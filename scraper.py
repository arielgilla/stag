import urllib.request
import json
import urllib.parse
import sys

MARGEN_GANANCIA = 1.15  # 15% de ganancia

# Lista de búsquedas clave para traer un catálogo completo de Hardware
BUSQUEDAS = [
    ("Procesadores", "procesador ryzen intel core"),
    ("Placas de Video", "placa de video rtx rx nvidia radeon"),
    ("Memorias RAM", "memoria ram ddr4 ddr5"),
    ("Almacenamiento", "disco ssd nvme"),
    ("Notebooks", "notebook laptop gamer"),
    ("Monitores", "monitor gamer 144hz")
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

productos_catalogo = []
vistos = set()

for cat_nombre, query_text in BUSQUEDAS:
    print(f"Buscando productos para: {cat_nombre}...")
    
    # 1. Intentar primero búsqueda directa en Venex
    urls_a_probar = [
        f"https://api.mercadolibre.com/sites/MLA/search?seller_id=61580996&q={urllib.parse.quote(query_text)}&limit=50",
        f"https://api.mercadolibre.com/sites/MLA/search?q=venex+{urllib.parse.quote(query_text)}&limit=50",
        f"https://api.mercadolibre.com/sites/MLA/search?q={urllib.parse.quote(query_text)}&limit=50"
    ]

    items_obtenidos = []
    for url in urls_a_probar:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get('results', [])
                if results and len(results) >= 5:
                    items_obtenidos = results
                    break
        except Exception as e:
            print(f"Aviso al consultar URL ({e}), intentando alternativa...")

    for item in items_obtenidos:
        titulo = item.get('title', '').strip()
        if not titulo or titulo in vistos:
            continue

        precio_costo = float(item.get('price', 0))
        if precio_costo <= 0:
            continue

        precio_venta = round(precio_costo * MARGEN_GANANCIA)
        
        # Obtener URL de imagen de alta calidad
        thumbnail = item.get('thumbnail', '')
        if not thumbnail:
            continue

        # Convertir a HTTPS y reemplazar sufijos de miniatura por alta resolución (-O)
        imagen_hd = thumbnail.replace('http://', 'https://')
        for sufijo in ['-I.jpg', '-V.jpg', '-I.webp', '-V.webp']:
            imagen_hd = imagen_hd.replace(sufijo, '-O.jpg')

        # Proxy para saltar bloqueos CORS/Hotlinking en GitHub Pages
        imagen_final = f"https://images.weserv.nl/?url={urllib.parse.quote(imagen_hd)}&output=webp"

        productos_catalogo.append({
            "titulo": titulo,
            "precio_venta": precio_venta,
            "categoria": cat_nombre,
            "imagen": imagen_final,
            "stock": True
        })
        vistos.add(titulo)

print(f"\nProceso finalizado. Total de productos extraídos: {len(productos_catalogo)}")

# Verificar que no esté vacío antes de guardar
if len(productos_catalogo) > 0:
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)
    print("productos.json guardado correctamente.")
else:
    print("Error: No se pudieron obtener productos.")
    sys.exit(1)
