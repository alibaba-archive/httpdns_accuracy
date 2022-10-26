# -*- coding: utf8 -*-

"""
Configuration of the HTTPDNS accuracy evaluator
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
from collections import defaultdict

from samples import CLIENT_SAMPLES

HOSTS = (
    ('gw.alicdn.com.danuoyi.tbcache.com', 'danuoyins7.tbcache.com'),
    ('ww1.sinaimg.cn.w.alikunlun.com', 'ns3.alikunlun.com'),
    ('bili.cold.c.cdnhwc2.com','ns1.huaweicloud-dns.cn'),
    ('v6-cname.dingtalk.com.gds.alibabadns.com','ns7.taobao.com'),
    ('suning.xdwscache.ourwebcdn.com', 'dns2.wswebcdn.info'),
    ('y.qq.com.sched.px-dk.tdnsv6.com','ns5.tdnsv6.com'),
    ('hiphotos.gshifen.com',  'ns1.gshifen.com'),
    ('x2ipv6.tcdn.qq.com', 'ns-cdn1.qq.com'),
    ('i.w.bilicdn1.com','ns4.dnsv5.com')
)

IPS = defaultdict(list)

# 测试终端IP总数
IP_COUNT = 0
PROVINCES = set()
CARRIERS = set()

for ip, province, carrier in CLIENT_SAMPLES:
    CARRIERS.add(carrier)
    PROVINCES.add(province)
    IPS[province, carrier].append(ip)
    IP_COUNT += 1

PROVINCES = sorted(PROVINCES)
CARRIERS = sorted(CARRIERS)
SAMPLE_COUNT = IP_COUNT * len(HOSTS)
