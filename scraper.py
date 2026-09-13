import urllib.request
import json
import urllib.parse

MARGEN_GANANCIA = 1.15  # 15% de ganancia

# ID de Vendedor Oficial de Venex en Mercado Libre
SELLER_ID = "61580996"

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

for cat_nombre, query_text in CATEGORIAS.items():
    print(f"Obteniendo {cat_nombre}...")
    
    query_encoded = urllib.parse.quote(query_text)
    url_api = f"https://api.mercadolibre.com/sites/MLA/search?seller_id={SELLER_ID}&q={query_encoded}&limit=50"

    try:
        req = urllib.request.Request(url_api, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])

            if len(results) < 5:
                url_fallback = f"https://api.mercadolibre.com/sites/MLA/search?q=venex+{query_encoded}&limit=50"
                req_f = urllib.request.Request(url_fallback, headers=headers)
                with urllib.request.urlopen(req_f) as resp_f:
                    data = json.loads(resp_f.read().decode('utf-8'))
                    results = data.get('results', [])

            for item in results:
                titulo = item.get('title', '').strip()
                if not titulo or titulo in vistos:
                    continue

                precio_costo = float(item.get('price', 0))
                if precio_costo <= 0:
                    continue

                precio_venta = round(precio_costo * MARGEN_GANANCIA)
                
                # Obtener la foto real
                thumbnail = item.get('thumbnail', '')
                if '-I.jpg' in thumbnail or '-V.jpg' in thumbnail:
                    imagen_raw = thumbnail.replace('-I.jpg', '-O.jpg').replace('-V.jpg', '-O.jpg')
                else:
                    imagen_raw = thumbnail.replace('http://', 'https://')

                # Usar el proxy de imágenes gratuito para saltar el bloqueo CORS de GitHub Pages
                imagen_desbloqueada = f"https://images.weserv.nl/?url={urllib.parse.quote(imagen_raw)}"

                productos_catalogo.append({
                    "titulo": titulo,
                    "precio_venta": precio_venta,
                    "categoria": cat_nombre,
                    "imagen": imagen_desbloqueada,
                    "stock": True
                })
                vistos.add(titulo)

    except Exception as e:
        print(f"Error cargando {cat_nombre}: {e}")

# Guardar catálogo en productos.json
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)

print(f"Sincronización finalizada. Total de productos cargados: {len(productos_catalogo)}")
