#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
the HTTPDNS accuracy evaluator
httpdns_accuracy Copyright (C) 2017  Aliyun inc.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
if os.name == 'nt':
    import win_inet_pton as _

import csv
import time
import socket
import traceback
from collections import defaultdict
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor

import dns
import dns.query
import dns.resolver
import dns.exception
import clientsubnetoption
import requests
from progressbar import ProgressBar
from requests import ConnectionError
from requests.adapters import HTTPAdapter

from config import (
    HOSTS, CARRIERS, PROVINCES, IPS, SAMPLE_COUNT
)


RUN_LOG_FILE = 'httpdns_accuracy.run_log'
DETAIL_CSV_FILE = 'httpdns_accuracy_detail.csv'
HTTPDNS_URL = "http://203.107.1.65/139450/d?host=%s&ip=%s"
DNSPOD_URL = "http://119.29.29.29/d?dn=%s&ip=%s"

THREAD_POOL = ThreadPoolExecutor(max_workers=30)

FINAL_RESULTS = {}


def retry(n=5, exc_list=()):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            tried = 1
            while tried <= n:
                try:
                    result = fn(*args, **kwargs)
                except exc_list as err:
                    # print >> sys.stderr, fn, args, kwargs
                    run_log('## RETRY %s/%s, [%s]\n##  -> %s%s'
                            % (tried, n, err, fn.__name__, args), print_stderr=False)
                    tried += 1
                else:
                    if tried > 1:
                        run_log('##  -> %s%s [RESOLVED]'
                                % (fn.__name__, args), print_stderr=False)
                    return result
            else:
                raise err
        return wrapper
    return decorator


@retry(exc_list=(ConnectionError, ))
def fetch_url(url, **kw):
    session = requests.session()
    session.mount('http://', HTTPAdapter(max_retries=3))
    kw.setdefault('timeout', 3)
    return session.get(url, **kw)


@retry(exc_list=(dns.exception.Timeout, dns.resolver.NoAnswer, ))
def query_dns0(domain, authority, client_ip=None, **kwargs):
    ns_ip = socket.gethostbyname(authority)

    kwargs.setdefault('rdtype', dns.rdatatype.A)
    message = dns.message.make_query(domain, **kwargs)
    if client_ip:
        message.use_edns(options=[clientsubnetoption.ClientSubnetOption(client_ip, bits=32)])

    return dns.query.udp(message, ns_ip, timeout=3)


def collect_ips(resp, target):
    result = []
    for answer in resp.answer:
        if answer.name.to_text()[:-1] != target:
            continue

        for item in answer.items:
            item_text = item.to_text()
            if item.rdtype == dns.rdatatype.A:
                result.append(item_text)

    return result


def do_resolve(target, authority, client_ip, result):
    # Authority
    authority_ips = result['Authority'] = set()
    min_times, max_times = 10, 25
    for times in range(1, max_times + 1):
        try:
            resp = query_dns0(target, authority, client_ip)
        except:
            traceback.print_exc()
            raise

        resp_ips = collect_ips(resp, target)
        if not authority_ips.issuperset(resp_ips):
            authority_ips.update(resp_ips)
        elif times > min_times:
            break

    # HTTPDNS
    try:
        resp = fetch_url(HTTPDNS_URL % (target, client_ip)).json()
        result['HTTPDNS'] = sorted(resp['ips'])
    except:
        traceback.print_exc()

    # DNSPOD
    try:
        ip_list = fetch_url(DNSPOD_URL % (target, client_ip)).content.split(';')
        result['DNSPOD'] = sorted(ip_list)
    except:
        traceback.print_exc()


def start_resolve():
    for province in PROVINCES:
        for carrier in CARRIERS:
            for client_ip in IPS[province, carrier]:
                for target, authority in HOSTS:
                    target_result = FINAL_RESULTS\
                        .setdefault(province, {})\
                        .setdefault(carrier, {})\
                        .setdefault(client_ip, {})[target] = defaultdict(list)

                    yield THREAD_POOL.submit(
                        do_resolve, target, authority, client_ip, target_result)


log_fp = open(RUN_LOG_FILE, 'ab')
def run_log(s, print_stderr=True):
    log_fp.write(s + "\n")
    if print_stderr:
        print >> sys.stderr, s


def main():
    run_log("""\n\n
=====httpdns_accuracy=====
%s
==========================\n\n""" % time.ctime(), print_stderr=False)

    print >> sys.stderr, '待测试域名：%s' % len(HOSTS)
    print >> sys.stderr, '待测试省份：%s' % len(PROVINCES)
    print >> sys.stderr, '待测试运营商：%s' % len(CARRIERS)
    print >> sys.stderr, '根据您的网络和机器配置，可能要运行20~30分钟，请耐心等待...'

    # start resolve
    print >> sys.stderr, '\n正在构造请求...'
    features = list(ProgressBar()(start_resolve(), SAMPLE_COUNT))

    print >> sys.stderr, '\n正在查询服务器...'
    list(ProgressBar()(as_completed(features), SAMPLE_COUNT))

    percentile = lambda f: '%.2f%%' % (f * 100)

    # calc diffs
    diffs = {'HTTPDNS': 0, 'DNSPOD': 0}
    effective_sample_count = 0
    with open(DETAIL_CSV_FILE, 'wb') as csv_fp:
        writer = csv.writer(csv_fp)
        for province in PROVINCES:
            for carrier in CARRIERS:
                for client_ip in IPS[province, carrier]:
                    for target, authority in HOSTS:
                        result = FINAL_RESULTS[province][carrier][client_ip][target]
                        authority_ips = result['Authority']
                        if not authority_ips:
                            continue
                        effective_sample_count = effective_sample_count + 1
                        matches = {}
                        for provider in diffs:
                            provider_ips = result[provider]
                            intersection = set(authority_ips).intersection(provider_ips)
                            matches[provider] = len(intersection) / float(len(provider_ips)) if provider_ips else 0
                            diffs[provider] += 1 - matches[provider]

                        writer.writerow([
                            target, province, carrier, authority, client_ip,
                            percentile(matches['HTTPDNS']), percentile(matches['DNSPOD']),
                            authority_ips, result['HTTPDNS'], result['DNSPOD']
                        ])

    run_log('测试域名：%s' % len(HOSTS))
    run_log('测试省份：%s' % len(PROVINCES))
    run_log('测试运营商：%s\n' % len(CARRIERS))

    if not effective_sample_count:
        run_log('无有效监测样本')
    else:
        run_log('Total sample number: %s' % SAMPLE_COUNT)
        for provider in diffs:
            run_log('Provider: %s Accuracy: %s' % (provider, percentile(1 - diffs[provider] / effective_sample_count)))

    run_log("""\n\n
=====httpdns_accuracy end=====
%s
==============================\n\n""" % time.ctime(), print_stderr=False)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        os.system('kill -9 $PPID')
        exit(-1)
