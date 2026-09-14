import json
import urllib.request
import urllib.parse

MARGEN_GANANCIA = 1.15
URL_API = "https://www.venex.com.ar/api/catalog_system/pub/products/search"

def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    # Términos de búsqueda clave para cubrir todo el catálogo de hardware y tecnología
    terminos = [
        "procesador", "placa de video", "memoria ram", "disco ssd", 
        "disco rigido", "motherboard", "fuente", "gabinete", 
        "cooler", "monitor", "notebook", "teclado", "mouse", 
        "auricular", "silla gamer"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.venex.com.ar/"
    }

    for termino in terminos:
        from_val = 0
        print(f"Consultando API de Venex para: {termino.upper()}")
        
        while True:
            params = {
                "ft": termino,
                "_from": from_val,
                "_to": from_val + 49
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
                        
                    precio_venta = round(precio_lista * MARGEN_GANANCIA)
                    
                    catalogo_final[titulo.lower()] = {
                        "titulo": titulo,
                        "categoria": termino.title(),
                        "precio_venta": precio_venta,
                        "imagen": "", 
                        "stock": True
                    }
                    vistos.add(titulo.lower())
                    productos_nuevos += 1
                
                if len(data) < 50 or productos_nuevos == 0:
                    break
                    
                from_val += 50
                
            except Exception as e:
                print(f"Error consultando término '{termino}': {e}")
                break

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Sincronización completa vía API. Total de productos reales obtenidos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
