import io, json, hashlib, sys
sys.stdout.reconfigure(encoding="utf-8")
root = r"C:\Users\202008-11\Desktop\ai pm\project5"
asset = io.open(root + r"\android-app\app\src\main\assets\portrait_index.json", encoding="utf-8").read()
doc = json.loads(asset)
print("asset heroes:", doc.get("hero_count"), "grid:", doc.get("grid_size"), "hash:", doc.get("content_hash"))
backend = io.open(root + r"\data\portrait_index.json", encoding="utf-8").read()
b_doc = json.loads(backend)
print("backend heroes:", b_doc.get("hero_count"), "grid:", b_doc.get("grid_size"), "hash:", b_doc.get("content_hash"))
print("asset == backend:", doc == b_doc)
