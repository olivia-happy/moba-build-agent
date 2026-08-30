import sys, io, json, hashlib, datetime, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
url = "https://pvp.qq.com/web201605/js/herolist.json"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    raw = r.read().decode("utf-8")
arr = json.loads(raw)
payload = json.dumps(arr, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
root = r"C:\Users\202008-11\Desktop\ai pm\project5\data"
with io.open(root + r"\hero_catalog_raw.json", "w", encoding="utf-8") as f:
    json.dump({"source_url": url, "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "content_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(), "heroes": arr}, f, ensure_ascii=False, indent=2)
print("heroes:", len(arr))
for h in arr[:8]:
    print(h.get("ename"), h.get("cname"), "type=", h.get("hero_type"), "roles=", h.get("roles"))
