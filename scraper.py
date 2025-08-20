import concurrent.futures as cf
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept-Encoding": "gzip, deflate, br",
})
# Reuse TCP (keep-alive) and raise pool limits
adapter = HTTPAdapter(
    pool_connections=100, pool_maxsize=100,
    max_retries=Retry(total=2, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
)
session.mount("http://", adapter)
session.mount("https://", adapter)

def fetch(url, timeout=8):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text

urls = [f"https://biblehub.com/1_peter/{i}-1.htm" for i in range(1, 6)]

with cf.ThreadPoolExecutor(max_workers=20) as ex:
    html_pages = list(ex.map(fetch, urls))

print(html_pages)