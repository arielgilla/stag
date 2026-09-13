import urllib.request
import json
import re

MARGEN_GANANCIA = 1.15  # 15% de ganancia extra

# Categorías a extraer de Venex vía HardGamers
CATEGORIAS = {
    "Procesadores": "https://www.hardgamers.com.ar/search?text=procesador+venex",
    "Placas de Video": "https://www.hardgamers.com.ar/search?text=placa+de+video+venex",
    "Memorias RAM": "https://www.hardgamers.com.ar/search?text=memoria+ram+venex",
    "Almacenamiento": "https://www.hardgamers.com.ar/search?text=disco+ssd+venex",
    "Notebooks": "https://www.hardgamers.com.ar/search?text=notebook+venex",
    "Monitores": "https://www.hardgamers.com.ar/search?text=monitor+venex"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

productos_catalogo = []
vistos = set()

for cat_nombre, url in CATEGORIAS.items():
    try:
        print(f"Buscando productos de {cat_nombre}...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')

        # Regex para capturar imagen real, título y precio
        # Buscar estructuras de productos en la plataforma
        items = re.findall(r'<div[^>]*class="[^"]*product-card[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)".*?<h3[^>]*>([^<]+)</h3>.*?\$([\d\.\,]+)', html, re.DOTALL)

        if not items:
            # Filtro secundario para imágenes y precios de Venex
            items = re.findall(r'src="([^"]+\.(?:jpg|png|webp))"[^>]*alt="([^"]+)".*?\$([\d\.\,]+)', html, re.DOTALL)

        for img, titulo, precio_raw in items:
            titulo_limpio = titulo.strip()
            
            # Filtrar productos repetidos o que no coincidan
            if titulo_limpio in vistos or len(titulo_limpio) < 8:
                continue

            try:
                precio_num = float(precio_raw.replace('.', '').replace(',', '.'))
                precio_venta = round(precio_num * MARGEN_GANANCIA)

                # Asegurar URL completa de imagen real
                img_url = img if img.startswith('http') else 'https:' + img

                productos_catalogo.append({
                    "titulo": titulo_limpio,
                    "precio_venta": precio_venta,
                    "categoria": cat_nombre,
                    "imagen": img_url,
                    "stock": True
                })
                vistos.add(titulo_limpio)
            except ValueError:
                continue
    except Exception as e:
        print(f"Error procesando {cat_nombre}: {e}")

# Guardar en productos.json
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Catálogo actualizado correctamente. Total de productos con fotos reales: {len(productos_catalogo)}")
