import sys, io
sys.stdout.reconfigure(encoding="utf-8")
import urllib.request
url = "https://pvp.qq.com/web201605/js/item.json"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read()
    print("status ok, bytes", len(data))
    print(data[:300])
except Exception as e:
    print("ERR", type(e).__name__, e)
