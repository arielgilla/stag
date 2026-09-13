import urllib.request
import re
import json
from bs4 import BeautifulSoup

MARGEN_GANANCIA = 1.15  # 15% de ganancia

# Mapeo de categorías principales de Venex
CATEGORIAS = {
    "Procesadores": "https://www.venex.com.ar/componentes-de-pc/procesadores",
    "Placas de Video": "https://www.venex.com.ar/componentes-de-pc/placas-de-video",
    "Memorias RAM": "https://www.venex.com.ar/componentes-de-pc/memorias-ram",
    "Almacenamiento": "https://www.venex.com.ar/componentes-de-pc/discos-rigidos-y-solidos",
    "Motherboards": "https://www.venex.com.ar/componentes-de-pc/motherboards",
    "Fuentes": "https://www.venex.com.ar/componentes-de-pc/fuentes-de-alimentacion",
    "Gabinetes": "https://www.venex.com.ar/componentes-de-pc/gabinetes",
    "Monitores": "https://www.venex.com.ar/perifericos/monitores",
    "Notebooks": "https://www.venex.com.ar/notebooks",
    "Periféricos": "https://www.venex.com.ar/perifericos/mouses"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

productos_catalogo = []
vistos = set()

for cat_nombre, url in CATEGORIAS.items():
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar contenedores de productos
        items = soup.find_all('div', class_=re.compile(r'product-box|product-item|item-producto', re.I))
        
        # Si la estructura no coincide con clases conocidas, buscar por enlaces de productos
        if not items:
            cards = soup.find_all(['div', 'article'])
            for card in cards:
                a_tag = card.find('a', href=re.compile(r'venex\.com\.ar'))
                img_tag = card.find('img')
                text = card.get_text()
                
                if a_tag and img_tag and '$' in text:
                    titulo = a_tag.get_text(strip=True) or img_tag.get('alt', '')
                    if len(titulo) > 10 and titulo not in vistos:
                        # Extraer precio
                        precio_match = re.search(r'\$\s*([\d\.\,]+)', text)
                        if precio_match:
                            try:
                                p_raw = precio_match.group(1).replace('.', '').replace(',', '.')
                                precio_venex = float(p_raw)
                                precio_venta = round(precio_venex * MARGEN_GANANCIA)
                                
                                img_src = img_tag.get('src') or img_tag.get('data-src') or ''
                                if not img_src.startswith('http'):
                                    img_src = 'https://www.venex.com.ar/' + img_src.lstrip('/')
                                
                                productos_catalogo.append({
                                    "titulo": titulo,
                                    "precio_venta": precio_venta,
                                    "categoria": cat_nombre,
                                    "imagen": img_src,
                                    "url_origen": a_tag.get('href', ''),
                                    "stock": True
                                })
                                vistos.add(titulo)
                            except ValueError:
                                continue
        else:
            for item in items:
                try:
                    a_tag = item.find('a')
                    img_tag = item.find('img')
                    if not a_tag: continue
                    
                    titulo = item.find(class_=re.compile(r'title|nombre', re.I))
                    titulo_str = titulo.get_text(strip=True) if titulo else a_tag.get_text(strip=True)
                    
                    precio_tag = item.find(class_=re.compile(r'price|precio', re.I))
                    precio_str = precio_tag.get_text(strip=True) if precio_tag else item.get_text()
                    precio_match = re.search(r'([\d\.\,]+)', precio_str)
                    
                    if titulo_str and precio_match and titulo_str not in vistos:
                        p_raw = precio_match.group(1).replace('.', '').replace(',', '.')
                        precio_venex = float(p_raw)
                        precio_venta = round(precio_venex * MARGEN_GANANCIA)
                        
                        img_src = img_tag.get('src') or img_tag.get('data-src') if img_tag else ''
                        if img_src and not img_src.startswith('http'):
                            img_src = 'https://www.venex.com.ar/' + img_src.lstrip('/')
                        
                        productos_catalogo.append({
                            "titulo": titulo_str,
                            "precio_venta": precio_venta,
                            "categoria": cat_nombre,
                            "imagen": img_src,
                            "url_origen": a_tag.get('href', ''),
                            "stock": True
                        })
                        vistos.add(titulo_str)
                except Exception:
                    continue

    except Exception as e:
        print(f"Error cargando categoría {cat_nombre}: {e}")

# Guardar resultados
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Sincronización finalizada. Total productos procesados: {len(productos_catalogo)}")
# Guardar catálogo completo en productos.json
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Total productos extraídos con imágenes: {len(productos_catalogo)}")
