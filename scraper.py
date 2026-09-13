import urllib.request
import re
import json

# Margen de ganancia (Ejemplo: 1.15 significa un 15% de ganancia sobre el precio de Venex)
MARGEN_GANANCIA = 1.15 

URLS_CATEGORIAS = [
    "https://www.venex.com.ar/componentes-de-pc/procesadores",
    "https://www.venex.com.ar/componentes-de-pc/placas-de-video",
    "https://www.venex.com.ar/componentes-de-pc/memorias-ram"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

productos_catalogo = []

for url in URLS_CATEGORIAS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        # Extraer productos de la categoría
        # Buscamos patrones de código de Venex para productos y precios
        items = re.findall(r'class="product-box".*?href="([^"]+)".*?alt="([^"]+)".*?\$([\d\.\,]+)', html, re.DOTALL)
        
        for link, titulo, precio_raw in items:
            precio_venex = float(precio_raw.replace('.', '').replace(',', '.'))
            precio_tu_tienda = round(precio_venex * MARGEN_GANANCIA)
            
            productos_catalogo.append({
                "titulo": titulo.strip(),
                "precio_venex": precio_venex,
                "precio_venta": precio_tu_tienda,
                "url_origen": link,
                "stock": True
            })
    except Exception as e:
        print(f"Error procesando {url}: {e}")

# Guardar el catálogo resultante en un archivo JSON para la web
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Sincronización completada. Total de productos: {len(productos_catalogo)}")
