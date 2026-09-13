import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

MARGEN_GANANCIA = 1.15
PRODUCTOS_POR_CATEGORIA = 50  # Cantidad de productos a extraer por categoría

categorias = [
    {"url": "https://www.venex.com.ar/procesadores", "cat": "Procesadores"},
    {"url": "https://www.venex.com.ar/placas-de-video", "cat": "Placas de Video"},
    {"url": "https://www.venex.com.ar/memorias-ram", "cat": "Memorias RAM"},
    {"url": "https://www.venex.com.ar/discos-rigidos-y-ssds", "cat": "Almacenamiento"},
    {"url": "https://www.venex.com.ar/notebooks", "cat": "Notebooks"},
    {"url": "https://www.venex.com.ar/monitores", "cat": "Monitores"},
    {"url": "https://www.venex.com.ar/perifericos", "cat": "Periféricos"},
    {"url": "https://www.venex.com.ar/refrigeracion", "cat": "Refrigeración"},
    {"url": "https://www.venex.com.ar/gabinetes", "cat": "Refrigeración"},
    {"url": "https://www.venex.com.ar/fuentes", "cat": "Refrigeración"}
]

print("Iniciando motor de extracción con navegador real (Playwright)...")
catalogo_final = []
vistos = set()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()

    for item_cat in categorias:
        url = item_cat["url"]
        categoria_nombre = item_cat["cat"]
        print(f"Extrayendo categoría: {categoria_nombre} desde {url}...")
        
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(3)
            
            # Hacer scroll para forzar la carga de imágenes reales (lazy loading)
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(1)

            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            items = soup.find_all('div', class_=lambda x: x and 'product' in x.lower())
            if not items:
                items = soup.find_all('div', class_='item')

            contador_cat = 0
            for card in items:
                if contador_cat >= PRODUCTOS_POR_CATEGORIA:
                    break
                
                # Buscar título
                titulo_tag = card.find(['h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() or 'name' in x.lower()))
                if not titulo_tag:
                    titulo_tag = card.find('a', title=True)
                
                titulo = ""
                if titulo_tag:
                    titulo = titulo_tag.get('title') or titulo_tag.get_text(strip=True)
                
                if not titulo or len(titulo) < 3 or titulo in vistos:
                    continue

                # Buscar precio
                precio_tag = card.find(class_=lambda x: x and 'price' in x.lower())
                if not precio_tag:
                    continue
                
                precio_txt = precio_tag.get_text(strip=True)
                precio_limpio = ''.join(c for c in precio_txt if c.isdigit() or c == ',' or c == '.')
                precio_limpio = precio_limpio.replace('.', '').replace(',', '.').split('.')[0]
                
                try:
                    precio_costo = float(precio_limpio)
                except ValueError:
                    continue

                if precio_costo <= 100:
                    continue

                precio_venta = round(precio_costo * MARGEN_GANANCIA)

                # Buscar imagen oficial
                img_tag = card.find('img')
                img_url = ""
                if img_tag:
                    img_url = img_tag.get('data-src') or img_tag.get('src') or img_tag.get('data-lazy-src') or ""

                if not img_url or 'placeholder' in img_url:
                    style = img_tag.get('style', '') if img_tag else ''
                    if 'url(' in style:
                        parts = style.split('url(')[1].split(')')[0].strip('"\'')
                        img_url = parts

                if img_url.startswith('/'):
                    img_url = f"https://www.venex.com.ar{img_url}"
                elif not img_url.startswith('http'):
                    img_url = "https://images.weserv.nl/?url=https://http2.mlstatic.com/D_NQ_NP_2X_894121-MLA74070267431_012024-O.jpg&output=webp"
                else:
                    img_url = f"https://images.weserv.nl/?url={urllib_quote_safe(img_url)}&output=webp" if 'weserv' not in img_url else img_url

                catalogo_final.append({
                    "titulo": titulo,
                    "precio_venta": precio_venta,
                    "categoria": categoria_nombre,
                    "imagen": img_url,
                    "stock": True
                })
                vistos.add(titulo)
                contador_cat += 1

        except Exception as e:
            print(f"Error al procesar categoría {categoria_nombre}: {e}")
            continue

    browser.close()

def urllib_quote_safe(url):
    import urllib.parse
    return urllib.parse.quote(url, safe='')

print(f"\nExtracción masiva total finalizada. Productos obtenidos: {len(catalogo_final)}")

with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(catalogo_final, f, ensure_ascii=False, indent=4)

print("Archivo productos.json generado con éxito.")
