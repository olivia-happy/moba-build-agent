import sys, io, json, re, hashlib
sys.stdout.reconfigure(encoding="utf-8")
import urllib.request, datetime
url = "https://pvp.qq.com/web201605/js/item.json"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    data = r.read().decode("utf-8")
arr = json.loads(data)
payload = json.dumps(arr, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
root = r"C:\Users\202008-11\Desktop\ai pm\project5\data"
with io.open(root + r"\item_catalog_raw.json", "w", encoding="utf-8") as f:
    json.dump({"source_url": url, "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "content_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(), "items": arr}, f, ensure_ascii=False, indent=2)
print("saved", len(arr))
