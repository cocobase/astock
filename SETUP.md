# 配置指南

1. OpenD 是 Futu API 的网关程序，运行于您的本地电脑或云端服务器，负责中转协议请求到富途服务器，并将处理后的数据返回。
2. 下载地址https://openapi.futunn.com/futu-api-doc/opend/opend-cmd.html ，运行后设置用户名和密码
3. 使用 uv run src/main.py --init 初始化日K线数据
4. 使用 uv run src/main.py --calc-pct 计算最近一个交易日的股票涨幅数据，数据保存在 data/pct-change.csv
5. 配置文件位于 config/config.yaml
