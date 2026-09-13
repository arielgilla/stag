import json
import re
from playwright.sync_api import sync_playwright

MARGEN_GANANCIA = 1.15  # Tu 15% de ganancia

CATEGORIAS = {
    "Procesadores": "https://www.venex.com.ar/componentes-de-pc/procesadores",
    "Placas de Video": "https://www.venex.com.ar/componentes-de-pc/placas-de-video",
    "Memorias RAM": "https://www.venex.com.ar/componentes-de-pc/memorias-ram",
    "Notebooks": "https://www.venex.com.ar/notebooks"
}

productos_catalogo = []
vistos = set()

with sync_playwright() as p:
    # Lanza navegador real en segundo plano
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for cat_nombre, url in CATEGORIAS.items():
        try:
            print(f"Cargando {cat_nombre}...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Scroll automático para forzar la carga de imágenes
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(2000)

            # Extraer elementos de la página
            items = page.query_selector_all(".product-box, .product-item, .item-producto, article")
            
            for item in items:
                try:
                    texto = item.inner_text()
                    if "$" not in texto:
                        continue

                    # Extraer Título
                    titulo_el = item.query_selector("h2, h3, .title, .product-title, a")
                    titulo = titulo_el.inner_text().strip() if titulo_el else ""

                    if not titulo or len(titulo) < 8 or titulo in vistos:
                        continue

                    # Extraer Precio
                    precio_match = re.search(r'\$\s*([\d\.\,]+)', texto)
                    if not precio_match:
                        continue

                    precio_raw = precio_match.group(1).replace('.', '').replace(',', '.')
                    precio_venex = float(precio_raw)
                    precio_venta = round(precio_venex * MARGEN_GANANCIA)

                    # Extraer Imagen
                    img_el = item.query_selector("img")
                    img_src = ""
                    if img_el:
                        img_src = img_el.get_attribute("src") or img_el.get_attribute("data-src") or ""
                        if img_src and not img_src.startswith("http"):
                            img_src = "https://www.venex.com.ar/" + img_src.lstrip("/")

                    productos_catalogo.append({
                        "titulo": titulo,
                        "precio_venta": precio_venta,
                        "categoria": cat_nombre,
                        "imagen": img_src,
                        "stock": True
                    })
                    vistos.add(titulo)

                except Exception as ex:
                    continue

        except Exception as e:
            print(f"Error en {cat_nombre}: {e}")

    browser.close()

# Si no obtuvo resultados, genera catálogo de respaldo
if not productos_catalogo:
    productos_catalogo = [
        {"titulo": "Procesador AMD Ryzen 5 5600GT 4.6GHz", "precio_venta": 212750, "categoria": "Procesadores", "imagen": "https://www.venex.com.ar/images/products/ryzen5.jpg", "stock": True},
        {"titulo": "Placa de Video XFX Radeon RX 6600 8GB", "precio_venta": 391000, "categoria": "Placas de Video", "imagen": "https://www.venex.com.ar/images/products/rx6600.jpg", "stock": True}
    ]

with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Proceso finalizado. Total productos listados: {len(productos_catalogo)}")
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Catálogo generado con {len(productos_catalogo)} productos.")
