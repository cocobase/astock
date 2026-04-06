import requests

def debug_snapshot(symbol):
    url = f"https://qt.gtimg.cn/q={symbol}"
    response = requests.get(url)
    response.encoding = 'gbk'
    print(f"\nSymbol: {symbol}")
    if '=' in response.text:
        val = response.text.split('=', 1)[1].strip().strip('"').strip(';')
        fields = val.split('~')
        for i, f in enumerate(fields):
            print(f"{i}: {f}")

if __name__ == "__main__":
    debug_snapshot("sh600519")
    debug_snapshot("hk00700")
    debug_snapshot("usAAPL")
