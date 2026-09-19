import json
import pandas as pd

with open("productos.json", "r", encoding="utf-8") as f:
    data = json.load(f)

rows = []
for categoria, productos in data.items():
    for p in productos:
        if p.get("precio_final") and p.get("imagen"):
            rows.append({
                "Nombre": p.get("titulo"),
                "Precio": p.get("precio_final"),
                "Imagen": p.get("imagen"),
                "Categoría": categoria,
                "URL": p.get("url")
            })

df = pd.DataFrame(rows)
df.to_csv("productos.csv", index=False, encoding="utf-8-sig")

print(f"✅ Archivo 'productos.csv' generado con {len(rows)} productos.")
