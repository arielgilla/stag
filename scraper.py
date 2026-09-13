import json
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import random
import time

MARGEN_GANANCIA = 1.15
catalogo_final = {}
vistos = set()

# Lista de navegadores reales para rotar y evitar el bloqueo de Cloudflare
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

print("Conectando en tiempo real con el catálogo oficial de Venex...")

base_search_url = "https://www.venex.com.ar/resultado-busqueda.htm?keywords=&limit=48&page="
max_paginas = 50 
consecutivos_vacios = 0

for page in range(1, max_paginas + 1):
    url = f"{base_search_url}{page}"
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.venex.com.ar/",
        "DNT": "1",
        "Connection": "keep-alive"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        # Pausa aleatoria breve para simular navegación humana y evitar bloqueos por velocidad
        time.sleep(random.uniform(1.0, 2.5))
        
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read()
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Localizar tarjetas de productos
        items = soup.find_all(['div', 'li'], class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower() or 'card' in x.lower()))
        if not items:
            items = soup.find_all('div', {'data-id': True})

        if not items:
            print(f"Fin del catálogo en vivo alcanzado en la página {page}.")
            break

        nuevos_en_pagina = 0

        for item in items:
            try:
                # Título oficial
                title_elem = item.find(['h2', 'h3', 'a'], class_=lambda x: x and ('title' in x.lower() or 'name' in x.lower()))
                if not title_elem:
                    title_elem = item.find('a', title=True)
                
                titulo = title_elem.get('title') or title_elem.get_text(strip=True) if title_elem else ""
                
                if not titulo or len(titulo) < 4 or titulo in vistos:
                    continue

                # Precio real
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

                # Imagen oficial
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
                continue

        if nuevos_en_pagina == 0:
            consecutivos_vacios += 1
            if consecutivos_vacios >= 3:
                break
        else:
            consecutivos_vacios = 0

    except Exception as e:
        print(f"Aviso de red en página {page}: {e}")
        continue

lista_final = list(catalogo_final.values())
print(f"Total exacto de productos sincronizados en vivo desde Venex: {len(lista_final)}")

# Guardar estrictamente lo obtenido de la tienda (sin respaldos inventados)
with open('productos.json', 'w', encoding='utf-8') as f:
    json.dump(lista_final, f, ensure_ascii=False, indent=4)

print("Archivo productos.json actualizado exclusivamente con datos reales de Venex.")
