import json
import re
from playwright.sync_api import sync_playwright

MARGEN_GANANCIA = 1.15  # Tu 15% de ganancia

CATEGORIAS = {
    "Procesadores": "https://www.venex.com.ar/componentes-de-pc/procesadores",
    "Placas de Video": "https://www.venex.com.ar/componentes-de-pc/placas-de-video",
    "Memorias RAM": "https://www.venex.com.ar/componentes-de-pc/memorias-ram",
    "Almacenamiento": "https://www.venex.com.ar/componentes-de-pc/discos-rigidos-y-solidos",
    "Notebooks": "https://www.venex.com.ar/notebooks",
    "Monitores": "https://www.venex.com.ar/perifericos/monitores"
}

productos_catalogo = []
vistos = set()

with sync_playwright() as p:
    # Simular navegador real con pantalla completa
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )
    page = context.new_page()

    for cat_nombre, url in CATEGORIAS.items():
        try:
            print(f"Scrapeando categoría: {cat_nombre}...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Scroll progresivo para forzar la carga de imágenes y productos
            for _ in range(4):
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(800)

            # Buscar las tarjetas de productos en Venex
            items = page.query_selector_all(".product-box, .product-item, .item-producto, .product")
            
            for item in items:
                try:
                    # Extraer Título y Link
                    link_el = item.query_selector("a[href*='/p/'], a[href*='venex.com.ar'], .title a, h3 a")
                    if not link_el:
                        continue
                    
                    titulo = link_el.inner_text().strip()
                    url_prod = link_el.get_attribute("href") or ""
                    
                    if not titulo or len(titulo) < 6 or titulo in vistos:
                        continue

                    # Extraer Precio
                    precio_el = item.query_selector(".price, .precio, .product-price")
                    texto_precio = precio_el.inner_text() if precio_el else item.inner_text()
                    
                    precio_match = re.search(r'\$\s*([\d\.\,]+)', texto_precio)
                    if not precio_match:
                        continue

                    precio_raw = precio_match.group(1).replace('.', '').replace(',', '.')
                    precio_venex = float(precio_raw)
                    precio_venta = round(precio_venex * MARGEN_GANANCIA)

                    # Extraer Imagen (Atributos reales de Lazy Loading)
                    img_el = item.query_selector("img")
                    img_src = ""
                    if img_el:
                        img_src = (
                            img_el.get_attribute("src") or 
                            img_el.get_attribute("data-src") or 
                            img_el.get_attribute("data-original") or ""
                        )
                        if img_src and not img_src.startswith("http"):
                            img_src = "https://www.venex.com.ar/" + img_src.lstrip("/")

                    productos_catalogo.append({
                        "titulo": titulo,
                        "precio_venta": precio_venta,
                        "categoria": cat_nombre,
                        "imagen": img_src,
                        "url_origen": url_prod,
                        "stock": True
                    })
                    vistos.add(titulo)

                except Exception:
                    continue

        except Exception as e:
            print(f"Error cargando {cat_nombre}: {e}")

    browser.close()

# Guardar en archivo JSON
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Extracción finalizada exitosamente. Total de productos con imágenes: {len(productos_catalogo)}")
