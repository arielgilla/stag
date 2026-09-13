import urllib.request
import json
import urllib.parse
import sys

MARGEN_GANANCIA = 1.15  # 15% de ganancia

# ID de Vendedor de Venex en ML
SELLER_ID = "61580996"

# Términos simples para que Mercado Libre no filtre de más y devuelva resultados
CATEGORIAS = {
    "Procesadores": "procesador",
    "Placas de Video": "placa de video",
    "Memorias RAM": "memoria ram",
    "Almacenamiento": "disco solido",
    "Notebooks": "notebook",
    "Monitores": "monitor"
}

headers = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0'
}

productos_catalogo = []
vistos = set()

for cat_nombre, query_text in CATEGORIAS.items():
    print(f"Buscando: {cat_nombre}...")
    
    query_encoded = urllib.parse.quote(query_text)
    
    # 3 opciones de búsqueda: de más exacta (Venex) a más amplia
    urls = [
        f"https://api.mercadolibre.com/sites/MLA/search?seller_id={SELLER_ID}&q={query_encoded}&limit=50",
        f"https://api.mercadolibre.com/sites/MLA/search?q=venex+{query_encoded}&limit=50",
        f"https://api.mercadolibre.com/sites/MLA/search?q={query_encoded}&limit=50"
    ]

    items_encontrados = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'results' in data and len(data['results']) > 0:
                    items_encontrados = data['results']
                    break  # Si encontró resultados, deja de intentar otras URLs
        except Exception as e:
            continue
    
    for item in items_encontrados:
        titulo = item.get('title', '').strip()
        if not titulo or titulo in vistos:
            continue

        precio = float(item.get('price', 0))
        if precio <= 0:
            continue

        precio_final = round(precio * MARGEN_GANANCIA)
        
        # Extraer imagen y pasarla a HD
        thumbnail = item.get('thumbnail', '')
        if not thumbnail:
            continue

        imagen_hd = thumbnail.replace('http://', 'https://')
        for sufijo in ['-I.jpg', '-V.jpg']:
            imagen_hd = imagen_hd.replace(sufijo, '-O.jpg')

        # Proxy de imágenes para que GitHub Pages no las bloquee (CORS)
        imagen_final = f"https://images.weserv.nl/?url={urllib.parse.quote(imagen_hd)}&output=webp"

        productos_catalogo.append({
            "titulo": titulo,
            "precio_venta": precio_final,
            "categoria": cat_nombre,
            "imagen": imagen_final,
            "stock": True
        })
        vistos.add(titulo)

# Comprobar si se encontraron productos antes de guardar
if len(productos_catalogo) > 0:
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)
    print(f"¡Éxito! Se sincronizaron {len(productos_catalogo)} productos.")
else:
    print("Error: No se encontraron productos. Verifica los términos de búsqueda.")
    sys.exit(1)
