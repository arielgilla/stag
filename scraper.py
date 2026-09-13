import urllib.request
import json
import urllib.parse

MARGEN_GANANCIA = 1.15

CATEGORIAS = {
    "Procesadores": "procesador",
    "Placas de Video": "placa de video",
    "Memorias RAM": "memoria ram",
    "Almacenamiento": "disco ssd",
    "Notebooks": "notebook",
    "Monitores": "monitor"
}

headers = {'User-Agent': 'Mozilla/5.0'}
productos_catalogo = []
vistos = set()

for cat_nombre, query_text in CATEGORIAS.items():
    url = f"https://api.mercadolibre.com/sites/MLA/search?q={urllib.parse.quote(query_text)}&limit=30"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for item in data.get('results', []):
                titulo = item.get('title', '').strip()
                if not titulo or titulo in vistos:
                    continue
                precio = float(item.get('price', 0))
                if precio <= 0:
                    continue
                
                thumb = item.get('thumbnail', '').replace('http://', 'https://')
                for s in ['-I.jpg', '-V.jpg']:
                    thumb = thumb.replace(s, '-O.jpg')
                
                img_url = f"https://images.weserv.nl/?url={urllib.parse.quote(thumb)}&output=webp"
                
                productos_catalogo.append({
                    "titulo": titulo,
                    "precio_venta": round(precio * MARGEN_GANANCIA),
                    "categoria": cat_nombre,
                    "imagen": img_url,
                    "stock": True
                })
                vistos.add(titulo)
    except Exception as e:
        print(f"Error en {cat_nombre}: {e}")

# Solo sobrescribir si trajo productos (evita que se guarde un JSON vacío)
if len(productos_catalogo) > 0:
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)
    print(f"Éxito: {len(productos_catalogo)} productos guardados.")
else:
    print("No se sobrescribió productos.json para preservar los datos actuales.")
