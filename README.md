# HTTPDNS调度精确性检测


## 实现机制

调度精确性检测包含如下模块：

`config.py`

待对比测试的域名及其权威DNS信息
待对比测试的终端IP样本及其对应的运营商，地域信息

`evaluator.py`

检测脚本，针对所有的待检测域名，分别采用EDNS权威，HTTPDNS，DNSPOD D+三种方式，携带终端IP样本进行解析，对比HTTPDNS、DNSPOD D+与权威EDNS解析的差异，并给出有差异的解析数据及最终的差异统计信息。


## 运行方式

### 1. 安装依赖
```sudo pip2.7 install -r requirements.txt```

### 2. 启动测试脚本，注意运行一次大约需要20~30分钟
```python2.7 evaluator.py```

### 3. 查看输出
1. Terminal会输出大多数概述性的信息
1. httpdns_accuracy_detail.csv： 详细的数据表报告
1. httpdns_accuracy.run_log：运行日志，包含错误输出及最终结果


## FAQ

### 1. \## RETRY 1/5, \[The DNS operation timed out.]

如果出现本提示，是指某次DNS查询超时了，**正在重试**，由于评估过程中会发送大量UDP包，所以较为常见


### 2. 机器负载较高

请调节THREAD_POOL = ThreadPoolExecutor(max_workers=20) 中的并发数量
