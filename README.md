# HTTPDNS调度精确性检测


## 实现机制

调度精确性检测包含如下模块：

`config.py`

待对比测试的域名及其权威DNS信息
待对比测试的终端IP样本及其对应的运营商，地域信息

`evaluator.py`

检测脚本，针对所有的待检测域名，分别采用EDNS权威，HTTPDNS，DNSPOD D+，Google DoH四种方式，携带终端IP样本进行解析，对比HTTPDNS、DNSPOD D+、Google DoH与权威EDNS解析的差异，并给出有差异的解析数据及最终的差异统计信息。

`samples.py`

待检测的IP采样点集合，覆盖不同地域与运营商，目前只包括中国与东南亚地区，如果需要更多地区的探测点，请到[阿里云HTTPDNS](https://help.aliyun.com/product/30100.html) 提交工单。

## 运行方式

### 1. 安装依赖
```sudo pip2.7 install -r requirements.txt```

### 2. 启动测试脚本，注意运行一次大约需要20~30分钟
```python2.7 evaluator.py```

### 3. 查看输出
1. Terminal会输出大多数概述性的信息
1. httpdns_accuracy_detail.csv： 详细的数据表报告
1. httpdns_accuracy.run_log：运行日志，包含错误输出及最终结果

## 测试自己的域名
按照以下步骤，比较阿里云HTTPDNS与友商的解析精度。
### 1. 开通阿里云HTTPDNS
登录阿里云官网开通 [阿里云HTTPDNS](https://help.aliyun.com/product/30100.html) ，HTTPDNS为每个账户提供150万次解析/月的免费测试额度。

### 2. 配置HTTPDNS账户ID
1. 在HTTPDNS控制台的[概览](https://help.aliyun.com/document_detail/30115.html) 的左上角获取自己的HTTPDNS的账户ID 
2. 把evaluator.py文件中HTTPDNS_URL的'139450'修改为自己的HTTPDNS账户ID
```
HTTPDNS_URL = "http://47.74.222.190/{HTTPDNS账号ID}/d?host=%s&ip=%s"
```

### 3. 探测CNAME和权威域名服务器
1. 把domains.txt中的域名列表替换为自己待测试的域名列表
2. 执行命令得到配置文件config.py中的HOSTS变量
```bash
bash  config_helper.sh
```
3. 用上面命令得到的HOSTS数据替换config.py中的HOSTS数据

### 4. 添加HTTPDNS域名白名单
登录HTTPDNS控制台，把HOSTS第一列中的域名[添加到HTTPDNS域名白名单](https://help.aliyun.com/document_detail/30116.html)

### 5. 执行测试
确保HTTPDNS解析配置生效后，执行以下命令比较解析精度
```python
python2.7 evaluator.py
```

## FAQ

### 1. \## RETRY 1/5, \[The DNS operation timed out.]

如果出现本提示，是指某次DNS查询超时了，**正在重试**，由于评估过程中会发送大量UDP包，所以较为常见


### 2. 机器负载较高

请调节THREAD_POOL = ThreadPoolExecutor(max_workers=30) 中的并发数量

### 3. 确保访问Google DNS网络正常


`curl  "https://dns.google/resolve?name=www.aliyun.com&type=a&edns_client_subnet=202.97.96.0"`

