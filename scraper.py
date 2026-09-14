import json
import urllib.request
import urllib.parse

MARGEN_GANANCIA = 1.15
# Endpoint oficial de búsqueda y catálogo de VTEX para Venex
URL_API = "https://www.venex.com.ar/api/catalog_system/pub/products/search"

def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    # Categorías clave y sus términos de búsqueda en la API de VTEX
    terminos_busqueda = {
        "Procesadores": "microprocesadores",
        "Placas de Video": "placas de video",
        "Memorias RAM": "memorias ram",
        "Almacenamiento SSD": "disco ssd",
        "Discos Rigidos": "disco rigido",
        "Motherboards": "motherboard",
        "Fuentes": "fuente",
        "Gabinetes": "gabinete",
        "Coolers y Refrigeracion": "cooler",
        "Monitores": "monitor",
        "Notebooks": "notebook",
        "Teclados": "teclado",
        "Mouses": "mouse",
        "Auriculares": "auricular",
        "Sillas Gamer": "silla gamer"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    for categoria, termino in terminos_busqueda.glob_items() if hasattr(terminos_busqueda, 'glob_items') else terminos_busqueda.items():
        from_val = 0
        to_val = 49  # Lote por consulta de la API
        
        print(f"Consultando API de Venex para: {categoria.upper()}")
        
        while True:
            params = {
                "ft": termino,
                "_from": from_val,
                "_to": to_val
            }
            url_query = f"{URL_API}?{urllib.parse.urlencode(params)}"
            
            try:
                req = urllib.request.Request(url_query, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                if not data or not isinstance(data, list) or len(data) == 0:
                    break
                    
                productos_nuevos = 0
                
                for item in data:
                    titulo = item.get("productName", "").strip()
                    if not titulo or titulo.lower() in vistos:
                        continue
                        
                    # Extraer el precio real del primer SKU disponible
                    items_sku = item.get("items", [])
                    if not items_sku:
                        continue
                        
                    sellers = items_sku[0].get("sellers", [])
                    if not sellers:
                        continue
                        
                    offer = sellers[0].get("commertialOffer", {})
                    precio_lista = offer.get("Price", 0)
                    disponible = offer.get("IsAvailable", False)
                    
                    if precio_lista <= 1000 or not disponible:
                        continue
                        
                    # Extraer imagen real del producto directamente desde la API de VTEX
                    imagenes = items_sku[0].get("images", [])
                    imagen_url = imagenes[0].get("imageUrl", "") if imagenes else ""
                    
                    precio_venta = round(precio_lista * MARGEN_GANANCIA)
                    
                    catalogo_final[titulo.lower()] = {
                        "titulo": titulo,
                        "categoria": categoria,
                        "precio_venta": precio_venta,
                        "imagen": imagen_url,
                        "stock": True
                    }
                    vistos.add(titulo.lower())
                    productos_nuevos += 1
                
                # Si la API devuelve menos de los solicitados o ya no hay más lotes
                if len(data) < 50 or productos_nuevos == 0:
                    break
                    
                from_val += 50
                to_val += 50
                
            except Exception as e:
                print(f"Error consultando la API para {categoria}: {e}")
                break

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Sincronización completa vía API. Total de productos reales obtenidos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
