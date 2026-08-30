import sys, io, json
sys.stdout.reconfigure(encoding="utf-8")
p = r"C:\Users\202008-11\Desktop\ai pm\project5\data\item_catalog_raw.json"
with io.open(p, encoding="utf-8") as f:
    doc = json.load(f)
items = doc["items"]
# Print all defensive / support items that could be emergency-swap or anti-heal / tenacity
for it in items:
    name = it.get("item_name","")
    des2 = it.get("des2") or ""
    if any(k in name for k in ["复活","血魔","名刀","辉月","金身","苍穹","冰霜","制裁","梦魇","魔女","永夜","破魔","不祥","极寒","反伤","暴烈","纯净"]) or "重伤" in des2 or "韧性" in des2:
        print(json.dumps({k: it.get(k) for k in ["item_id","item_name","item_type","price","total_price","des1","des2"]}, ensure_ascii=False))
