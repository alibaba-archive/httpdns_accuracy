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
import socket
import traceback
from cStringIO import StringIO
from collections import defaultdict
from concurrent.futures import wait
from concurrent.futures.thread import ThreadPoolExecutor

import dns
import dns.query
import dns.resolver
import dns.exception
import clientsubnetoption
import requests
from requests.adapters import HTTPAdapter

from config import (
    HOSTS, CARRIERS, PROVINCES, IPS, SAMPLE_COUNT
)

HTTPDNS_URL = "http://203.107.1.33/139450/d?host=%s&ip=%s"
DNSPOD_URL = "http://119.29.29.29/d?dn=%s&ip=%s"

THREAD_POOL = ThreadPoolExecutor(max_workers=20)

FINAL_RESULTS = {}


def fetch_url(url, **kw):
    session = requests.session()
    session.mount('http://', HTTPAdapter(max_retries=3))
    return session.get(url, **kw)


def retry(n=5, exc_list=()):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            tried = 1
            while tried <= n:
                try:
                    return fn(*args, **kwargs)
                except exc_list as err:
                    # print >> sys.stderr, fn, args, kwargs
                    print >> sys.stderr, '## RETRY %s/%s, [%s]' % (tried, n, err)
                    tried += 1
            else:
                raise err
        return wrapper
    return decorator


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
    min_times, max_times = 5, 25
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


def main():
    print >> sys.stderr, '待测试域名：%s' % len(HOSTS)
    print >> sys.stderr, '待测试省份：%s' % len(PROVINCES)
    print >> sys.stderr, '待测试运营商：%s' % len(CARRIERS)

    # start resolve
    wait(list(start_resolve()))

    percentile = lambda f: '%.2f%%' % (f * 100)

    csv_fp = StringIO()
    writer = csv.writer(csv_fp)

    # calc diffs
    diffs = {'HTTPDNS': 0, 'DNSPOD': 0}
    for province in PROVINCES:
        for carrier in CARRIERS:
            for client_ip in IPS[province, carrier]:
                for target, authority in HOSTS:
                    result = FINAL_RESULTS[province][carrier][client_ip][target]
                    authority_ips = result['Authority']
                    matches = {}
                    for provider in diffs:
                        provider_ips = result[provider]
                        intersection = authority_ips.intersection(provider_ips)
                        matches[provider] = len(intersection) / float(len(provider_ips)) if provider_ips else 0
                        diffs[provider] += 1 - matches[provider]

                    writer.writerow([
                        target, province, carrier, authority, client_ip,
                        percentile(matches['HTTPDNS']), percentile(matches['DNSPOD']),
                        authority_ips, result['HTTPDNS'], result['DNSPOD']
                    ])

    if not SAMPLE_COUNT:
        print >> sys.stderr, '无有效监测样本'
    else:
        print >> sys.stderr, 'Total sample number: %s' % SAMPLE_COUNT
        for provider in diffs:
            print >> sys.stderr, 'Provider: %s Difference: %.2f%%' % (provider, diffs[provider] * 100.0 / SAMPLE_COUNT)

    print csv_fp.getvalue()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        os.system('kill -9 $PPID')
        exit(-1)
