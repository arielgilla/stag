import json
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import sys

try:
    MARGEN_GANANCIA = 1.15
    catalogo_final = {}
    vistos = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    print("Iniciando escaneo masivo seguro del catálogo de Venex...")

    base_search_url = "https://www.venex.com.ar/resultado-busqueda.htm?keywords=&limit=48&page="
    max_paginas = 100 
    productos_consecutivos_repetidos = 0

    for page in range(1, max_paginas + 1):
        url = f"{base_search_url}{page}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                html_content = response.read()
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Selectores universales seguros
            items = soup.find_all(['div', 'li'], class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower() or 'card' in x.lower()))
            if not items:
                items = soup.find_all('div', {'data-id': True})

            if not items:
                print(f"Fin del catálogo detectado en la página {page}.")
                break

            nuevos_en_pagina = 0

            for item in items:
                try:
                    # Extracción segura del título
                    title_elem = item.find(['h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() or 'name' in x.lower()))
                    if not title_elem:
                        title_elem = item.find('a', title=True)
                    
                    titulo = title_elem.get('title') or title_elem.get_text(strip=True) if title_elem else ""
                    
                    if not titulo or len(titulo) < 4 or titulo in vistos:
                        continue

                    # Extracción segura del precio
                    price_elem = item.find(class_=lambda x: x and ('price' in x.lower() or 'precio' in x.lower()))
                    if not price_elem:
                        continue
                    
                    raw_price = price_elem.get_text(strip=True)
                    clean_price = ''.join(c for c in raw_price if c.isdigit() or c == ',' or c == '.')
                    clean_price = clean_price.replace('.', '').replace(',', '.').split('.')[0]
                    
                    if not clean_price:
                        continue
                        
                    costo = float(clean_price)
                    if costo <= 100:
                        continue

                    precio_final = round(costo * MARGEN_GANANCIA)

                    # Extracción segura de la imagen
                    img_elem = item.find('img')
                    img_url = ""
                    if img_elem:
                        img_url = img_elem.get('data-src') or img_elem.get('src') or img_elem.get('data-lazy') or ""

                    if img_url.startswith('/'):
                        img_url = f"https://www.venex.com.ar{img_url}"
                    elif not img_url.startswith('http'):
                        continue

                    catalogo_final[titulo] = {
                        "titulo": titulo,
                        "precio_venta": precio_final,
                        "imagen": img_url,
                        "stock": True
                    }
                    vistos.add(titulo)
                    nuevos_en_pagina += 1
                except Exception:
                    # Si falla un producto individual, continúa con el siguiente sin romper el script
                    continue

            if nuevos_en_pagina == 0:
                productos_consecutivos_repetidos += 1
                if productos_consecutivos_repetidos >= 3:
                    print("No se encontraron nuevos productos en páginas sucesivas. Deteniendo escaneo.")
                    break
            else:
                productos_consecutivos_repetidos = 0

        except Exception as e:
            # Si hay un error de red o bloqueo en una página entera, avisa pero no crashea
            print(f"Advertencia en página {page}: {e}")
            continue

    lista_final = list(catalogo_final.values())
    print(f"Sincronización completada con éxito. Total de productos únicos enlazados: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

except Exception as fatal_error:
    print(f"Error crítico en la ejecución: {fatal_error}")
    sys.exit(1)
