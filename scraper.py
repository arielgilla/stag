import json
import re
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from curl_cffi import requests

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

CATEGORIAS = {
    "Procesadores": "/componentes-de-pc/microprocesadores",
    "Placas de Video": "/componentes-de-pc/placas-de-video",
    "Memorias RAM": "/componentes-de-pc/memorias-ram",
    "Almacenamiento SSD": "/componentes-de-pc/discos-solidos-ssd",
    "Discos Rigidos": "/componentes-de-pc/discos-rigidos",
    "Motherboards": "/componentes-de-pc/motherboards",
    "Fuentes": "/componentes-de-pc/fuentes",
    "Gabinetes": "/componentes-de-pc/gabinetes",
    "Coolers y Refrigeracion": "/componentes-de-pc/coolers-y-refrigeracion",
    "Monitores": "/monitores",
    "Notebooks": "/computadoras/notebooks",
    "PCs Armadas": "/computadoras/pc-armadas",
    "Teclados": "/perifericos/teclados",
    "Mouses": "/perifericos/mouses",
    "Auriculares": "/perifericos/auriculares",
    "Mousepads": "/perifericos/mousepads",
    "Sillas Gamer": "/gaming/sillas-gamer",
    "Consolas y Videojuegos": "/gaming/consolas-y-videojuegos",
    "Audio y Parlantes": "/audio-y-video/parlantes",
    "Almacenamiento Externo": "/almacenamiento/pendrives-y-tarjetas-de-memoria",
    "Conectividad y Redes": "/conectividad/routers-y-repetidores"
}

def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    # Simular la huella TLS de Chrome 120 para bypass de Cloudflare
    session = requests.Session(impersonate="chrome120")
    
    for categoria, path in CATEGORIAS.items():
        pagina_actual = 1
        print(f"\n🔍 Explorando: {categoria.upper()}")
        
        while True:
            url_paginada = f"{URL_BASE}{path}?page={pagina_actual}"
            
            try:
                res = session.get(url_paginada, timeout=15)
                if res.status_code != 200:
                    print(f"  ❌ Error {res.status_code} al acceder a página {pagina_actual}")
                    break

                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Detectar contenedores de productos en el HTML
                tarjetas = soup.find_all(lambda tag: tag.name in ['div', 'article'] and 
                                        tag.has_attr('class') and 
                                        any('product' in c.lower() or 'item' in c.lower() for c in tag['class']))
                
                if not tarjetas:
                    tarjetas = [t for t in soup.find_all(['div', 'article']) if '$' in t.get_text()]

                productos_nuevos = 0
                
                for tarjeta in tarjetas:
                    texto = tarjeta.get_text(separator=' ', strip=True)
                    if '$' not in texto:
                        continue

                    # Extraer Título
                    title_tag = tarjeta.find(['h2', 'h3', 'h4', 'h5', 'a'])
                    if not title_tag:
                        continue
                    
                    titulo = title_tag.get_text(strip=True).replace('\n', ' ')
                    if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                        continue

                    # Extraer Precio
                    precios = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', texto)
                    if not precios:
                        continue

                    raw_price = precios[0]
                    clean_price = raw_price.replace('.', '').replace(',', '.').split('.')[0]
                    if not clean_price.isdigit():
                        continue

                    costo = float(clean_price)
                    if costo <= 1000:
                        continue

                    precio_venta = round(costo * MARGEN_GANANCIA)

                    # Extraer Imagen
                    img_url = ""
                    img_tag = tarjeta.find('img')
                    if img_tag:
                        for attr in ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-image']:
                            val = img_tag.get(attr)
                            if val and 'placeholder' not in val.lower() and 'logo' not in val.lower() and 'svg' not in val.lower():
                                img_url = val.strip()
                                break

                    if img_url:
                        if img_url.startswith('//'):
                            img_url = "https:" + img_url
                        elif img_url.startswith('/'):
                            img_url = urljoin(URL_BASE, img_url)

                    catalogo_final[titulo.lower()] = {
                        "titulo": titulo,
                        "categoria": categoria,
                        "precio_venta": precio_venta,
                        "imagen": img_url,
                        "stock": True
                    }
                    vistos.add(titulo.lower())
                    productos_nuevos += 1

                print(f"  ├─ Página {pagina_actual}: {productos_nuevos} productos agregados")

                if productos_nuevos == 0:
                    break

                pagina_actual += 1
                time.sleep(0.5)

            except Exception as e:
                print(f"  ❌ Error procesando {url_paginada}: {e}")
                break

    lista_final = list(catalogo_final.values())
    con_imagen = len([p for p in lista_final if p['imagen']])
    print(f"\n🚀 Proceso finalizado. Total productos: {len(lista_final)} | Con imagen: {con_imagen}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
