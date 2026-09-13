import urllib.request
import json
import urllib.parse
import sys

MARGEN_GANANCIA = 1.15  # 15% de ganancia

# Múltiples términos por categoría para garantizar decenas de productos reales
CATEGORIAS = {
    "Procesadores": ["procesador ryzen", "procesador intel core", "procesador am4 am5"],
    "Placas de Video": ["placa de video rtx", "placa de video rx", "placa de video gtx"],
    "Memorias RAM": ["memoria ram ddr4", "memoria ram ddr5", "memoria ram notebook"],
    "Almacenamiento": ["disco ssd nvme", "disco solido sata", "disco ssd 1tb"],
    "Notebooks": ["notebook i5 i7", "notebook ryzen", "notebook gamer"],
    "Monitores": ["monitor gamer 144hz", "monitor 24 pulgadas", "monitor samsung lg"]
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

productos_catalogo = []
vistos = set()

for cat_nombre, terminos in CATEGORIAS.items():
    print(f"Descargando categoría: {cat_nombre}...")
    for termino in terminos:
        query_encoded = urllib.parse.quote(termino)
        
        # Búsqueda amplia directa en Venex / Mercado Libre
        urls = [
            f"https://api.mercadolibre.com/sites/MLA/search?seller_id=61580996&q={query_encoded}&limit=50",
            f"https://api.mercadolibre.com/sites/MLA/search?q={query_encoded}&limit=50"
        ]

        for url in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
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

                        # Formateo de imagen HD oficial de Mercado Libre
                        thumbnail = item.get('thumbnail', '')
                        if not thumbnail:
                            continue

                        # Cambiar HTTP a HTTPS
                        imagen_url = thumbnail.replace('http://', 'https://')
                        
                        # Reemplazar la miniatura por la imagen HD original (-O)
                        for sufijo in ['-I.jpg', '-V.jpg', '-I.webp', '-V.webp']:
                            imagen_url = imagen_url.replace(sufijo, '-O.jpg')

                        # Usar el CDN/Proxy oficial de imágenes de weserv para evitar bloqueos CORS en GitHub Pages
                        imagen_final = f"https://images.weserv.nl/?url={urllib.parse.quote(imagen_url)}&output=webp"

                        productos_catalogo.append({
                            "titulo": titulo,
                            "precio_venta": precio_venta,
                            "categoria": cat_nombre,
                            "imagen": imagen_final,
                            "stock": True
                        })
                        vistos.add(titulo)

            except Exception as e:
                print(f"Aviso procesando {termino}: {e}")
                continue

print(f"\nSincronización completa. Total de productos extraídos: {len(productos_catalogo)}")

# Guardar si tenemos una lista amplia de productos
if len(productos_catalogo) > 0:
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)
    print("productos.json generado exitosamente.")
else:
    print("Error: No se lograron obtener productos.")
    sys.exit(1)
