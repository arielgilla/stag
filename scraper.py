import json
import time
from curl_cffi import requests

MARGEN_GANANCIA = 1.15
URL_API = "https://www.venex.com.ar/api/catalog_system/pub/products/search"

def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    session = requests.Session(impersonate="chrome120")
    headers = {
        "Accept": "application/json",
        "Referer": "https://www.venex.com.ar/"
    }

    from_val = 0
    step = 50
    max_items = 2500

    print("🚀 Extrayendo catálogo completo desde API de VTEX...")

    while from_val < max_items:
        to_val = from_val + step - 1
        params = {
            "_from": from_val,
            "_to": to_val
        }

        try:
            response = session.get(URL_API, headers=headers, params=params, timeout=20)
            
            if response.status_code != 200:
                print(f"  ❌ Error HTTP {response.status_code}. Finalizando.")
                break

            data = response.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                print("  ✅ No hay más productos devueltos.")
                break

            nuevos = 0
            for item in data:
                titulo = item.get("productName", "").strip()
                if not titulo or titulo.lower() in vistos:
                    continue

                items_sku = item.get("items", [])
                if not items_sku:
                    continue

                sellers = items_sku[0].get("sellers", [])
                if not sellers:
                    continue

                offer = sellers[0].get("commertialOffer", {})
                precio_lista = offer.get("Price", 0)
                disponible = offer.get("IsAvailable", False)

                if precio_lista <= 1000 or not disponible:
                    continue

                # Extraer categoría desde el árbol oficial de VTEX
                raw_cats = item.get("categories", ["/General/"])
                cat_path = raw_cats[0].strip("/").split("/") if raw_cats else ["General"]
                categoria = cat_path[-1] if cat_path else "General"

                # Extraer URL de la imagen principal
                images = items_sku[0].get("images", [])
                img_url = images[0].get("imageUrl", "") if images else ""

                precio_venta = round(precio_lista * MARGEN_GANANCIA)

                catalogo_final[titulo.lower()] = {
                    "titulo": titulo,
                    "categoria": categoria,
                    "precio_venta": precio_venta,
                    "imagen": img_url,
                    "stock": True
                }
                vistos.add(titulo.lower())
                nuevos += 1

            print(f"  ├─ Items {from_val} a {to_val}: {len(data)} recibidos (+{nuevos} válidos)")

            if len(data) < step:
                break

            from_val += step
            time.sleep(0.2)

        except Exception as e:
            print(f"  ❌ Error consultando la API: {e}")
            break

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Proceso finalizado. Total productos obtenidos: {len(lista_final)}")

    with open("productos.json", "w", encoding="utf-8") as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
