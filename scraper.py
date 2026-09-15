import json
import requests

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

CATEGORIAS = {
    "Notebooks": "/computadoras/notebooks",
    "Placas de Video": "/componentes-de-pc/placas-de-video",
    # ...
}

def extraer_venex():
    catalogo_final = {}

    for categoria, path in CATEGORIAS.items():
        print(f"🔄 Extrayendo categoría: {categoria.upper()}")
        url = f"{URL_BASE}{path}"
        # ⚠️ Este URL no trae productos directamente, hay que descubrir el endpoint JSON
        # Ejemplo ficticio:
        api_url = f"{URL_BASE}/api/catalogo{path}?page=1"
        resp = requests.get(api_url)
        data = resp.json()

        for item in data["products"]:
            titulo = item["name"]
            precio = float(item["price"])
            img_url = item["image"]

            catalogo_final[titulo.lower()] = {
                "titulo": titulo,
                "categoria": categoria,
                "precio_venta": round(precio * MARGEN_GANANCIA),
                "imagen": img_url,
                "stock": item.get("stock", True)
            }

    lista = list(catalogo_final.values())
    print(f"\n🚀 Finalizado. Productos totales: {len(lista)}")
    with open("productos.json", "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
