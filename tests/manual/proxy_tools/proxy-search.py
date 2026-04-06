import requests
from bs4 import BeautifulSoup
import time
import sys

def scrape_proxies():
    """Scrapes proxies from hide.mn/en/proxy-list/"""
    url = "https://hide.mn/en/proxy-list/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Look for the table
        table = soup.find('table')
        if not table:
            # Try finding by class if generic 'table' fails
            table = soup.find('table', class_='proxy-list')
            
        if not table:
            print("Error: Could not find the proxy table on the page.")
            return []
        
        proxies = []
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                ip = cols[0].get_text(strip=True)
                port = cols[1].get_text(strip=True)
                # Simple validation for IP-like string and numeric port
                if ip and port and '.' in ip and port.isdigit():
                    proxies.append(f"{ip}:{port}")
        
        return proxies
    except Exception as e:
        print(f"Error during scraping: {e}")
        return []

def test_proxy(proxy):
    """Tests a proxy's availability and latency for both HTTP and HTTPS"""
    # Many free proxies only support HTTP, not HTTPS
    test_urls = ["http://httpbin.org/ip", "https://httpbin.org/ip"]
    proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }
    
    results = {}
    for url in test_urls:
        protocol = "HTTPS" if url.startswith("https") else "HTTP"
        try:
            start_time = time.time()
            response = requests.get(url, proxies=proxies, timeout=5)
            latency = time.time() - start_time
            if response.status_code == 200:
                origin = response.json().get('origin', 'Unknown')
                results[protocol] = (True, latency, origin)
            else:
                results[protocol] = (False, 0, None)
        except Exception:
            results[protocol] = (False, 0, None)
            
    # Prefer HTTPS result if both work, otherwise return HTTP if it works
    if results.get("HTTPS", (False, 0, None))[0]:
        return results["HTTPS"]
    return results.get("HTTP", (False, 0, None))

def scrape_geonode():
    """Scrapes proxies from geonode API"""
    url = "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        proxies = []
        for item in data.get('data', []):
            ip = item.get('ip')
            port = item.get('port')
            if ip and port:
                proxies.append(f"{ip}:{port}")
        return proxies
    except Exception as e:
        print(f"Error during Geonode scraping: {e}")
        return []

def main():
    print("=== Proxy Scraper & Tester ===")
    print("Source 1: https://hide.mn/en/proxy-list/")
    print("Source 2: Geonode API")
    print("-" * 30)
    
    proxies_source1 = scrape_proxies()
    proxies_source2 = scrape_geonode()
    
    # Use a set to remove duplicates
    all_proxies = list(set(proxies_source1 + proxies_source2))
    
    # Limit testing to 50 for efficiency, you can increase this later
    proxies_to_test = all_proxies[:50]
    
    print(f"Found {len(all_proxies)} unique potential proxies. Testing first {len(proxies_to_test)}...\n")
    print(f"{'Proxy Address':<22} | {'Status':<7} | {'Latency':<8} | {'Origin IP'}")
    print("-" * 65)
    
    working_proxies = []
    for proxy in proxies_to_test:
        success, latency, origin = test_proxy(proxy)
        status = "✅ OK" if success else "❌ FAIL"
        lat_str = f"{latency:.2f}s" if success else "-"
        origin_str = (origin.split(',')[0]) if origin else "-"
        
        print(f"{proxy:<22} | {status:<7} | {lat_str:<8} | {origin_str}")
        
        if success:
            working_proxies.append(proxy)
            
    print("-" * 65)
    print(f"Summary: {len(working_proxies)}/{len(proxies_to_test)} proxies are working.")
    
    if working_proxies:
        with open("working_proxies.txt", "w") as f:
            for p in working_proxies:
                f.write(f"{p}\n")
        print(f"Working proxies saved to 'working_proxies.txt'.")

if __name__ == "__main__":
    main()
