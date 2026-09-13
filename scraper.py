import json
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

MARGEN_GANANCIA = 1.15
MAX_PRODUCTOS = 300  # Límite amplio para abarcar todo el catálogo masivo

print("Iniciando extracción masiva total desde el sitemap de Venex...")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

urls_productos = []

try:
    # 1. Intentar obtener las URLs directamente del sitemap principal de productos
    sitemap_url = "https://www.venex.com.ar/sitemap.xml"
    req = urllib.request.Request(sitemap_url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=15) as response:
        xml_data = response.read()
        
    root = ET.fromstring(xml_data)
    # Manejar namespaces de XML si los tiene
    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    # Buscar todas las URLs de productos (filtrando por la estructura de enlaces de la tienda)
    for elem in root.iter():
        if elem.tag.endswith('loc'):
            url = elem.text
            if url and any(cat in url for cat in ['/procesadores/', '/placas-', '/memorias-', '/discos-', '/notebooks/', '/monitores/', '/perifericos/', '/refrigeracion/', '/gabinetes/', '/fuentes/']):
                if url not in urls_productos:
                    urls_productos.append(url)

except Exception as e:
    print(f"Aviso leyendo sitemap principal: {e}")

# Si el sitemap directo devolvió pocos resultados, complementamos con las páginas de categorías principales de forma masiva
if len(urls_productos) < 10:
    print("Expandiendo búsqueda a través de listados de categorías...")
    categorias_base = [
        "https://www.venex.com.ar/procesadores",
        "https://www.venex.com.ar/placas-de-video",
        "https://www.venex.com.ar/memorias-ram",
        "https://www.venex.com.ar/discos-rigidos-y-ssds",
        "https://www.venex.com.ar/notebooks",
        "https://www.venex.com.ar/monitores",
        "https://www.venex.com.ar/perifericos",
        "https://www.venex.com.ar/refrigeracion",
        "https://www.venex.com.ar/gabinetes",
        "https://www.venex.com.ar/fuentes"
    ]
    
    for cat_url in categorias_base:
        try:
            req_cat = urllib.request.Request(cat_url, headers=headers)
            with urllib.request.urlopen(req_cat, timeout=10) as resp_cat:
                soup_cat = BeautifulSoup(resp_cat.read().decode('utf-8'), 'html.parser')
                
            for a_tag in soup_cat.find_all('a', href=True):
                href = a_tag['href']
                if href.startswith('http') and 'venex.com.ar' in href and href not in urls_productos:
                    if any(c in href for c in ['-p-', '-i-', '/producto/']): # Patrones típicos de URLs de productos individuales
                        urls_productos.append(href)
        except Exception:
            continue

print(f"URLs totales detectadas para procesar: {len(urls_productos)}")

catalogo_final = []
vistos = set()

# Procesar cada producto encontrado para extraer datos reales, precios e imágenes
for url in urls_productos[:MAX_PRODUCTOS]:
    try:
        req_p = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req_p, timeout=8) as resp_p:
            soup = BeautifulSoup(resp_p.read().decode('utf-8'), 'html.parser')
            
        # Extraer Título
        titulo_elem = soup.find('h1') or soup.find('title')
        if not titulo_elem:
            continue
        titulo = titulo_elem.get_text(strip=True).replace(" - Venex", "")
        
        if not titulo or len(titulo) < 3 or titulo in vistos:
            continue

        # Extraer Precio
        precio_elem = soup.find(class_=lambda x: x and 'price' in x.lower())
        if not precio_elem:
            # Buscar en metadatos si no está en la vista visual
            precio_elem = soup.find('meta', property='product:price:amount')
            precio_txt = precio_elem['content'] if precio_elem else ""
        else:
            precio_txt = precio_elem.get_text(strip=True)

        precio_limpio = ''.join(c for c in precio_txt if c.isdigit() or c == ',' or c == '.')
        precio_limpio = precio_limpio.replace('.', '').replace(',', '.').split('.')[0]
        
        try:
            precio_costo = float(precio_limpio)
        except ValueError:
            continue

        if precio_costo <= 100:
            continue

        precio_venta = round(precio_costo * MARGEN_GANANCIA)

        # Extraer Imagen Oficial
        img_url = ""
        img_elem = soup.find('meta', property='og:image') or soup.find('img', class_=lambda x: x and ('zoom' in x.lower() or 'main' in x.lower() or 'image' in x.lower()))
        
        if img_elem:
            img_url = img_elem.get('content') or img_elem.get('src') or img_elem.get('data-src') or ""

        if img_url.startswith('/'):
            img_url = f"https://www.venex.com.ar{img_url}"
        elif not img_url.startswith('http'):
            img_url = "https://images.weserv.nl/?url=https://http2.mlstatic.com/D_NQ_NP_2X_894121-MLA74070267431_012024-O.jpg&output=webp"
        else:
            img_url = f"https://images.weserv.nl/?url={urllib.parse.quote(img_url, safe='')}&output=webp"

        # Categorización automática basada en el título o URL
        categoria = "Hardware y Accesorios"
        u_lower = url.lower()
        t_lower = titulo.lower()
        
        if 'procesador' in u_lower or 'procesador' in t_lower: categoria = "Procesadores"
        elif 'placa' in u_lower or 'video' in t_lower or 'geforce' in t_lower or 'radeon' in t_lower: categoria = "Placas de Video"
        elif 'memoria' in u_lower or 'ram' in t_lower: categoria = "Memorias RAM"
        elif 'disco' in u_lower or 'ssd' in u_lower or 'almacenamiento' in t_lower: categoria = "Almacenamiento"
        elif 'notebook' in u_lower or 'laptop' in t_lower: categoria = "Notebooks"
        elif 'monitor' in u_lower: categoria = "Monitores"
        elif any(k in u_lower or k in t_lower for k in ['teclado', 'mouse', 'auricular', 'micrófono']): categoria = "Periféricos"
        elif any(k in u_lower or k in t_lower for k in ['gabinete', 'fuente', 'cooler', 'refrigeracion']): categoria = "Refrigeración"

        catalogo_final.append({
            "titulo": titulo,
            "precio_venta": precio_venta,
            "categoria": categoria,
            "imagen": img_url,
            "stock": True
        })
        vistos.add(titulo)

    except Exception:
        continue

print(f"Extracción masiva total completada. Total de productos extraídos: {len(catalogo_final)}")

# Guardar el archivo JSON definitivo para la tienda web
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(catalogo_final, f, ensure_ascii=False, indent=4)

print("Archivo productos.json actualizado con éxito.")
