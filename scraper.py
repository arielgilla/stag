import urllib.request
import xml.etree.ElementTree as ET
import json
import urllib.parse
import re
import gzip
import io

# Margen de ganancia exacto del 15%
MARGEN_GANANCIA = 1.15

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9'
}

print("Iniciando extracción masiva del catálogo completo de Venex...")

productos_catalogo = []
vistos = set()

# Intentar descargar el sitemap principal de productos de Venex
sitemap_urls = [
    "https://www.venex.com.ar/sitemap.xml",
    "https://www.venex.com.ar/sitemap_products.xml",
    "https://www.venex.com.ar/sitemap-products.xml"
]

xml_data = None
for s_url in sitemap_urls:
    try:
        req = urllib.request.Request(s_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            if content.startswith(b'\x1f\x8b'): # Gzip
                content = gzip.decompress(content)
            xml_data = content.decode('utf-8', errors='ignore')
            print(f"Sitemap encontrado exitosamente en: {s_url}")
            break
    except Exception as e:
        print(f"No se pudo acceder a {s_url}: {e}")

urls_productos = []
if xml_data:
    try:
        root = ET.fromstring(xml_data)
        # Manejar namespaces de XML si existen
        for elem in root.iter():
            if elem.tag.endswith('loc'):
                url_text = elem.text.strip() if elem.text else ""
                # Filtrar URLs que correspondan a productos de la tienda
                if url_text and ('/producto/' in url_text or '/p/' in url_text):
                    urls_productos.append(url_text)
    except Exception as e:
        print(f"Error procesando el XML del sitemap: {e}")

# Si el sitemap no está accesible de forma directa, realizamos una extracción amplia por categorías clave barriendo páginas enteras
if len(urls_productos) == 0:
    print("Empleando motor de barrido masivo por páginas de categorías de Venex...")
    categorias_busqueda = [
        "procesador", "placa-de-video", "memoria-ram", "disco-rigido", "ssd", 
        "notebook", "monitor", "teclado", "mouse", "auriculares", "gabinete", 
        "fuente", "motherboard", "cooler", "silla-gamer", "refrigeracion"
    ]
    
    for cat in categorias_busqueda:
        for pagina in range(1, 6): # Barrido de hasta 5 páginas por categoría
            url_cat = f"https://www.venex.com.ar/{cat}?page={pagina}"
            try:
                req = urllib.request.Request(url_cat, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html_cat = resp.read().decode('utf-8', errors='ignore')
                    # Extraer links de productos dentro de la categoría
                    links = re.findall(r'href="(https://www.venex\.com\.ar/productos/[^"]+)"', html_cat)
                    if not links:
                        links = re.findall(r'href="(/producto/[^"]+)"', html_cat)
                        links = [f"https://www.venex.com.ar{l}" if l.startswith('/') else l for l in links]
                    
                    for l in links:
                        if l not in vistos:
                            vistos.add(l)
                            urls_productos.append(l)
            except Exception:
                break

print(f"Se detectaron {len(urls_productos)} enlaces de productos únicos para procesar.")

# Procesar cada producto encontrado para extraer título, precio real e imagen oficial
contador = 0
for url_prod in urls_productos[:300]: # Límite optimizado para rendimiento en GitHub Actions
    try:
        req = urllib.request.Request(url_prod, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            # Extracción limpia de metadatos OpenGraph oficiales de la página del producto
            titulo_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if not titulo_match:
                titulo_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            
            precio_match = re.search(r'<meta property="product:price:amount" content="([0-9\.]+)"', html)
            if not precio_match:
                precio_match = re.search(r'class="current-price"[^>]*>\s*\$?\s*([0-9\.]+)', html)
            
            imagen_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            
            if titulo_match and precio_match:
                titulo = titulo_match.group(1).replace(' - Venex', '').strip()
                if titulo in vistos and contador > 0:
                    continue
                
                precio_str = precio_match.group(1).replace('.', '').replace(',', '.').strip()
                try:
                    precio_costo = float(precio_str)
                except ValueError:
                    continue
                
                if precio_costo <= 100: # Descartar valores erróneos
                    continue
                
                precio_venta = round(precio_costo * MARGEN_GANANCIA)
                
                img_url = imagen_match.group(1) if imagen_match else "https://http2.mlstatic.com/D_NQ_NP_2X_894121-MLA74070267431_012024-O.jpg"
                
                # Enrutar imagen mediante proxy CDN para evitar problemas de CORS y asegurar carga rápida
                imagen_final = f"https://images.weserv.nl/?url={urllib.parse.quote(img_url)}&output=webp"
                
                # Categorización inteligente basada en el título
                t_lower = titulo.lower()
                if 'procesador' in t_lower or 'ryzen' in t_lower or 'core i' in t_lower:
                    cat = "Procesadores"
                elif 'placa' in t_lower or 'video' in t_lower or 'rtx' in t_lower or 'gtx' in t_lower or 'radeon' in t_lower:
                    cat = "Placas de Video"
                elif 'memoria' in t_lower or 'ram' in t_lower or 'ddr' in t_lower:
                    cat = "Memorias RAM"
                elif 'disco' in t_lower or 'ssd' in t_lower or 'nvme' in t_lower or 'tb' in t_lower:
                    cat = "Almacenamiento"
                elif 'notebook' in t_lower or 'laptop' in t_lower:
                    cat = "Notebooks"
                elif 'monitor' in t_lower or 'pantalla' in t_lower:
                    cat = "Monitores"
                elif 'teclado' in t_lower or 'mouse' in t_lower or 'auriculares' in t_lower:
                    cat = "Periféricos"
                else:
                    cat = "Hardware y Accesorios"

                productos_catalogo.append({
                    "titulo": titulo,
                    "precio_venta": precio_venta,
                    "categoria": cat,
                    "imagen": imagen_final,
                    "stock": True
                })
                vistos.add(titulo)
                contador += 1
    except Exception:
        continue

print(f"Extracción masiva completada con éxito. Total de productos extraídos: {len(productos_catalogo)}")

# Guardar el archivo JSON final para la tienda web
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print("Archivo productos.json actualizado correctamente.")
