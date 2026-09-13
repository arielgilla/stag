import urllib.request
import re
import json

MARGEN_GANANCIA = 1.15  # Tu 15% de ganancia

# Lista ampliada de categorías principales de Venex
URLS_CATEGORIAS = [
    "https://www.venex.com.ar/componentes-de-pc/procesadores",
    "https://www.venex.com.ar/componentes-de-pc/placas-de-video",
    "https://www.venex.com.ar/componentes-de-pc/memorias-ram",
    "https://www.venex.com.ar/componentes-de-pc/discos-rigidos-y-solidos",
    "https://www.venex.com.ar/componentes-de-pc/motherboards",
    "https://www.venex.com.ar/componentes-de-pc/fuentes-de-alimentacion",
    "https://www.venex.com.ar/componentes-de-pc/gabinetes",
    "https://www.venex.com.ar/perifericos/monitores",
    "https://www.venex.com.ar/notebooks",
    "https://www.venex.com.ar/perifericos/auriculares",
    "https://www.venex.com.ar/perifericos/teclados",
    "https://www.venex.com.ar/perifericos/mouses"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

productos_catalogo = []
vistos = set()

for url in URLS_CATEGORIAS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        # Extraer bloques de producto buscando la imagen, el título, link y el precio
        # Buscar artículos de productos
        items = re.findall(r'<div[^>]*class="[^"]*product-box[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)".*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>.*?\$([\d\.\,]+)', html, re.DOTALL)
        
        # Patrón alternativo más flexible si el HTML varía
        if not items:
            items = re.findall(r'src="([^"]+\.(?:jpg|png|webp)[^"]*)".*?href="(https://www\.venex\.com\.ar/[^"]+)".*?>([^<]{10,100})<.*?\$([\d\.\,]+)', html, re.DOTALL)

        for img, link, titulo, precio_raw in items:
            titulo_limpio = titulo.strip()
            if titulo_limpio in vistos:
                continue
                
            try:
                precio_venex = float(precio_raw.replace('.', '').replace(',', '.'))
                precio_tu_tienda = round(precio_venex * MARGEN_GANANCIA)
                
                # Ajustar URL de la imagen si es relativa
                img_url = img if img.startswith('http') else 'https://www.venex.com.ar/' + img.lstrip('/')
                
                productos_catalogo.append({
                    "titulo": titulo_limpio,
                    "precio_venta": precio_tu_tienda,
                    "imagen": img_url,
                    "url_origen": link,
                    "stock": True
                })
                vistos.add(titulo_limpio)
            except ValueError:
                continue
    except Exception as e:
        print(f"Error cargando {url}: {e}")

# Guardar catálogo completo en productos.json
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Total productos extraídos con imágenes: {len(productos_catalogo)}")
