import urllib.request
import json
import urllib.parse
import sys

# Parámetros de configuración
MARGEN_GANANCIA = 1.15  # 15% de incremento
SELLER_ID = "61580996"   # ID oficial verificado de Venex en Mercado Libre

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

productos_catalogo = []
vistos = set()
offset = 0
limit = 50
max_productos = 1000  # Límite de seguridad para abarcar todo el catálogo

print("Iniciando sincronización masiva del catálogo de Venex...")

while offset < max_productos:
    # URL oficial de la API de Mercado Libre filtrando por el vendedor de Venex
    url = f"https://api.mercadolibre.com/sites/MLA/search?seller_id={SELLER_ID}&offset={offset}&limit={limit}"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])
            
            if not results:
                break  # Si ya no hay más productos, terminamos la paginación

            for item in results:
                titulo = item.get('title', '').strip()
                if not titulo or titulo in vistos:
                    continue

                precio_costo = float(item.get('price', 0))
                if precio_costo <= 0:
                    continue

                # Aplicar automáticamente el 15% de margen de ganancia
                precio_venta = round(precio_costo * MARGEN_GANANCIA)

                # Procesamiento de imagen en alta resolución
                thumbnail = item.get('thumbnail', '')
                if not thumbnail:
                    continue

                imagen_hd = thumbnail.replace('http://', 'https://')
                for sufijo in ['-I.jpg', '-V.jpg', '-I.webp', '-V.webp']:
                    imagen_hd = imagen_hd.replace(sufijo, '-O.jpg')

                # Usar proxy de imágenes optimizado para evitar bloqueos CORS en GitHub Pages
                imagen_final = f"https://images.weserv.nl/?url={urllib.parse.quote(imagen_hd)}&output=webp"

                # Clasificación inteligente de categorías basada en el título del producto
                titulo_lower = titulo.lower()
                if any(k in titulo_lower for k in ['procesador', 'ryzen', 'core i5', 'core i7', 'core i3', 'cpu']):
                    categoria = "Procesadores"
                elif any(k in titulo_lower for k in ['placa de video', 'rtx', 'gtx', 'radeon', 'video']):
                    categoria = "Placas de Video"
                elif any(k in titulo_lower for k in ['memoria ram', 'ddr4', 'ddr5', 'sodimm']):
                    categoria = "Memorias RAM"
                elif any(k in titulo_lower for k in ['disco', 'ssd', 'nvme', 'hdd', 'almacenamiento', 'tb', 'gb']):
                    categoria = "Almacenamiento"
                elif any(k in titulo_lower for k in ['notebook', 'laptop', 'portatil']):
                    categoria = "Notebooks"
                elif any(k in titulo_lower for k in ['monitor', 'pantalla', 'hz']):
                    categoria = "Monitores"
                elif any(k in titulo_lower for k in ['teclado', 'mouse', 'auriculares', 'headset', 'micrófono', 'camara']):
                    categoria = "Periféricos"
                elif any(k in titulo_lower for k in ['cooler', 'water cooling', 'refrigeracion', 'gabinete', 'fuente']):
                    categoria = "Refrigeración y Gabinetes"
                else:
                    categoria = "Otros Componentes"

                productos_catalogo.append({
                    "titulo": titulo,
                    "precio_venta": precio_venta,
                    "categoria": categoria,
                    "imagen": imagen_final,
                    "stock": True
                })
                vistos.add(titulo)

            # Avanzar a la siguiente página
            offset += limit
            
            # Si trajimos menos de los solicitados, es el final del catálogo
            if len(results) < limit:
                break

    except Exception as e:
        print(f"Aviso durante la paginación en el offset {offset}: {e}")
        break

print(f"\nSincronización finalizada con éxito. Total de productos de Venex procesados: {len(productos_catalogo)}")

# Guardar únicamente si se obtuvieron productos para evitar vaciar el sitio
if len(productos_catalogo) > 0:
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(productos_catalogo, f, ensure_ascii=False, indent=4)
    print("Archivo productos.json actualizado correctamente.")
else:
    print("Error: No se pudieron extraer productos en esta ejecución.")
    sys.exit(1)
