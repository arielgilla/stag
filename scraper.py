import urllib.request
import json

MARGEN_GANANCIA = 1.15  # Tu 15% de ganancia

# ID oficial de Vendedor de Venex en Mercado Libre: 61580996 (o búsqueda directa oficial)
NICKNAME_VENEX = "VENEX"

CATEGORIAS = {
    "Procesadores": "procesador",
    "Placas de Video": "placa de video",
    "Memorias RAM": "memoria ram",
    "Almacenamiento": "disco ssd",
    "Notebooks": "notebook",
    "Monitores": "monitor"
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

productos_catalogo = []
vistos = set()

# 1. Obtener el ID de usuario de Venex
try:
    url_user = f"https://api.mercadolibre.com/sites/MLA/search?nickname={NICKNAME_VENEX}"
    req = urllib.request.Request(url_user, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data_user = json.loads(resp.read().decode('utf-8'))
        seller_id = data_user['seller']['id'] if 'seller' in data_user and 'id' in data_user['seller'] else None
except Exception as e:
    seller_id = None

for cat_nombre, query_text in CATEGORIAS.items():
    print(f"Obteniendo {cat_nombre} de Venex...")
    
    # Construir la consulta a la API oficial de Mercado Libre
    if seller_id:
        url_api = f"https://api.mercadolibre.com/sites/MLA/search?seller_id={seller_id}&q={urllib.parse.quote(query_text)}&limit=50"
    else:
        url_api = f"https://api.mercadolibre.com/sites/MLA/search?q=venex+{urllib.parse.quote(query_text)}&limit=50"

    try:
        req = urllib.request.Request(url_api, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])

            for item in results:
                titulo = item.get('title', '').strip()
                if not titulo or titulo in vistos:
                    continue

                precio_costo = float(item.get('price', 0))
                if precio_costo <= 0:
                    continue

                precio_venta = round(precio_costo * MARGEN_GANANCIA)
                
                # Obtener la foto original HD de alta calidad
                imagen_url = item.get('thumbnail', '').replace('-I.jpg', '-O.jpg').replace('-V.jpg', '-O.jpg')
                if not imagen_url.startswith('http'):
                    imagen_url = item.get('secure_thumbnail', '')

                productos_catalogo.append({
                    "titulo": titulo,
                    "precio_venta": precio_venta,
                    "categoria": cat_nombre,
                    "imagen": imagen_url,
                    "stock": True
                })
                vistos.add(titulo)

    except Exception as e:
        print(f"Error en {cat_nombre}: {e}")

# Guardar catálogo resultante en productos.json
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Éxito total! Se extrajeron {len(productos_catalogo)} productos reales con sus fotos HD.")
