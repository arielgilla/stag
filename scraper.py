import json
import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

CATEGORIAS = {
    "Notebooks": "/computadoras/notebooks",
    "PCs Armadas": "/computadoras/pc-armadas",
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8"
    })
    return s

def extraer_imagen(tarjeta):
    img_tag = tarjeta.find('img')
    if not img_tag:
        return ""
    val = img_tag.get('src') or img_tag.get('data-src')
    if val and val.startswith('//'):
        val = "https:" + val
    elif val and val.startswith('/'):
        val = urljoin(URL_BASE, val)
    return val or ""

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
                tarjetas = soup.select('div.item-product')
                if not tarjetas:
                    break

                nuevos_en_pagina = 0
                for t in tarjetas:
                    # Título
                    title_tag = t.select_one('h2 a, h3 a, .product-title a')
                    if not title_tag:
                        continue
                    titulo = title_tag.get_text(strip=True)
                    if not titulo or titulo.lower() in vistos:
                        continue

                    # Precio
                    price_tag = t.select_one('.price')
                    if not price_tag:
                        continue
                    raw_price = re.sub(r'[^\d]', '', price_tag.get_text())
                    if not raw_price.isdigit():
                        continue
                    val = float(raw_price)

                    # Imagen
                    img_url = extraer_imagen(t)

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
    print(f"\n🚀 Finalizado. Productos totales: {len(lista)}")
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
