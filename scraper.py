import urllib.request
import json
import re

MARGEN_GANANCIA = 1.15  # 15% de ganancia sobre el precio base

# Enlaces directos a las categorías principales de Venex
CATEGORIAS = {
    "Procesadores": "https://www.venex.com.ar/componentes-de-pc/procesadores",
    "Placas de Video": "https://www.venex.com.ar/componentes-de-pc/placas-de-video",
    "Memorias RAM": "https://www.venex.com.ar/componentes-de-pc/memorias-ram",
    "Almacenamiento": "https://www.venex.com.ar/componentes-de-pc/discos-rigidos-y-solidos",
    "Notebooks": "https://www.venex.com.ar/notebooks",
    "Monitores": "https://www.venex.com.ar/perifericos/monitores"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7'
}

productos_catalogo = []
vistos = set()

for cat_nombre, url_cat in CATEGORIAS.items():
    print(f"Descargando categoría: {cat_nombre}...")
    
    # Intentar obtener hasta 3 páginas por categoría para traer decenas de productos
    for pagina in range(1, 4):
        url = f"{url_cat}?p={pagina}" if pagina > 1 else url_cat
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Expresión regular ajustada para capturar las tarjetas de productos de Venex
            # Captura: Imagen, Enlace al producto, Título y Precio
            patron = r'<div[^>]*class="[^"]*product-box[^"]*"[^>]*>.*?<img[^>]+(?:src|data-src)="([^"]+)".*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?\$([\d\.\,]+)'
            items = re.findall(patron, html, re.DOTALL)

            if not items:
                # Patrón secundario si varía la estructura
                patron_secundario = r'<img[^>]+(?:src|data-src)="([^"]+)"[^>]*alt="([^"]+)".*?\$([\d\.\,]+)'
                matches = re.findall(patron_secundario, html, re.DOTALL)
                items = [(img, "#", titulo, precio) for img, titulo, precio in matches]

            encontrados_en_pagina = 0

            for img, link, titulo, precio_raw in items:
                titulo_limpio = titulo.strip()

                if not titulo_limpio or len(titulo_limpio) < 8 or titulo_limpio in vistos:
                    continue

                try:
                    precio_num = float(precio_raw.replace('.', '').replace(',', '.'))
                    precio_venta = round(precio_num * MARGEN_GANANCIA)

                    # Formatear la URL de la imagen
                    img_url = img
                    if not img_url.startswith('http'):
                        img_url = 'https://www.venex.com.ar/' + img_url.lstrip('/')

                    # Asegurar la URL de imagen oficial de alta resolución si es miniatura
                    img_url = img_url.replace('/thumbs/', '/').replace('_thumb', '')

                    productos_catalogo.append({
                        "titulo": titulo_limpio,
                        "precio_venta": precio_venta,
                        "categoria": cat_nombre,
                        "imagen": img_url,
                        "stock": True
                    })
                    
                    vistos.add(titulo_limpio)
                    encontrados_en_pagina += 1

                except ValueError:
                    continue

            if encontrados_en_pagina == 0:
                break

        except Exception as e:
            print(f"Aviso en {cat_nombre} (pág {pagina}): {e}")
            break

# Guardar en productos.json
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Extracción finalizada. Total de productos extraídos: {len(productos_catalogo)}")
