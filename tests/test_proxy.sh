#!/bin/bash

# 确定 proxies.txt 的路径
PROXY_FILE="proxies.txt"
if [[ ! -f "$PROXY_FILE" ]]; then
  # 如果在 tests 目录下运行，尝试上级目录
  PROXY_FILE="../proxies.txt"
fi

if [[ ! -f "$PROXY_FILE" ]]; then
  echo "❌ 错误: 找不到 $PROXY_FILE"
  exit 1
fi

echo "正在从 $PROXY_FILE 加载代理列表..."

while IFS= read -r proxy || [[ -n "$proxy" ]]; do
  # 跳过空行和注释
  [[ -z "$proxy" ]] && continue
  [[ "$proxy" =~ ^# ]] && continue

  # 去除首尾空格
  proxy=$(echo "$proxy" | xargs)
  [[ -z "$proxy" ]] && continue

  # 确保有协议前缀，如果没有则默认为 http://
  if [[ ! "$proxy" =~ ^[a-z]+:// ]]; then
    proxy_url="http://$proxy"
  else
    proxy_url="$proxy"
  fi

  echo "Testing $proxy_url"

  result=$(curl -x "$proxy_url" \
    --connect-timeout 3 \
    --max-time 5 \
    -s https://httpbin.org/ip)

  if [[ $result == *"origin"* ]]; then
    latency=$(curl -x "$proxy_url" \
      -o /dev/null \
      -s \
      -w "%{time_total}" \
      https://httpbin.org/ip)

    echo "✅ OK: $proxy_url | latency=${latency}s | $result"
  else
    echo "❌ FAIL: $proxy_url"
  fi

  echo "----------------------"
done < "$PROXY_FILE"
