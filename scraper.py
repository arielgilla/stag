import json
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

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

def crear_sesion():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    })
    return s

def extraer_imagen(tarjeta):
    img_tag = tarjeta.find('img')
    if not img_tag:
        return ""
    atributos = ['data-src', 'data-original', 'data-lazy-src', 'data-image', 'src']
    for attr in atributos:
        val = img_tag.get(attr)
        if val and isinstance(val, str):
            val = val.strip()
            if val and not any(x in val.lower() for x in ['placeholder', 'loading', 'logo', 'blank', 'svg', 'data:image']):
                return val
    srcset = img_tag.get('srcset')
    if srcset and isinstance(srcset, str):
        urls = [part.strip().split(' ')[0] for part in srcset.split(',') if part.strip()]
        for u in urls:
            if u and not any(x in u.lower() for x in ['placeholder', 'loading', 'logo', 'svg']):
                return u
    return ""

def extraer_venex():
    session = crear_sesion()
    catalogo_final = {}
    vistos = set()

    for categoria, path in CATEGORIAS.items():
        pagina = 1
        print(f"🔄 Extrayendo categoría: {categoria.upper()}")

        while pagina <= 15:
            url = f"{URL_BASE}{path}?page={pagina}"
            try:
                res = session.get(url, timeout=15)
                if res.status_code != 200:
                    break

                soup = BeautifulSoup(res.text, 'html.parser')
                tarjetas = soup.select('div.product-item')
                if not tarjetas:
                    break

                nuevos_en_pagina = 0
                for t in tarjetas:
                    # Título
                    title_tag = t.select_one('h2 a, h3 a, .product-title a')
                    if not title_tag:
                        continue
                    titulo = title_tag.get_text(strip=True)
                    if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                        continue

                    # Precio
                    price_tag = t.select_one('.price')
                    if not price_tag:
                        continue
                    raw_price = re.sub(r'[^\d]', '', price_tag.get_text())
                    if not raw_price.isdigit():
                        continue
                    val = float(raw_price)
                    if val < 1000:
                        continue

                    # Imagen
                    img_url = extraer_imagen(t)
                    if img_url:
                        if img_url.startswith('//'):
                            img_url = "https:" + img_url
                        elif img_url.startswith('/'):
                            img_url = urljoin(URL_BASE, img_url)

                    catalogo_final[titulo.lower()] = {
                        "titulo": titulo,
                        "categoria": categoria,
                        "precio_venta": round(val * MARGEN_GANANCIA),
                        "imagen": img_url,
                        "stock": True
                    }
                    vistos.add(titulo.lower())
                    nuevos_en_pagina += 1

                if nuevos_en_pagina == 0 and pagina > 1:
                    break
                pagina += 1

            except Exception as e:
                print(f"⚠️ Error en {url}: {e}")
                break

    lista = list(catalogo_final.values())
    con_img = len([p for p in lista if p['imagen']])
    print(f"\n🚀 Finalizado. Productos totales: {len(lista)} | Con imagen: {con_img}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
