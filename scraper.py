import json
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

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

def extraer_venex():
    catalogo_final = {}
    vistos = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for categoria, path in CATEGORIAS.items():
            pagina = 1
            print(f"🔄 Extrayendo categoría: {categoria.upper()}")

            while pagina <= 15:
                url = f"{URL_BASE}{path}?page={pagina}"
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_selector("div.item-product", timeout=15000)

                    tarjetas = page.query_selector_all("div.item-product")
                    if not tarjetas:
                        break

                    nuevos_en_pagina = 0
                    for t in tarjetas:
                        # Título
                        title_tag = t.query_selector("h2 a, h3 a, .product-title a")
                        if not title_tag:
                            continue
                        titulo = title_tag.inner_text().strip()
                        if not titulo or titulo.lower() in vistos:
                            continue

                        # Precio
                        price_tag = t.query_selector(".price")
                        if not price_tag:
                            continue
                        raw_price = re.sub(r"[^\d]", "", price_tag.inner_text())
                        if not raw_price.isdigit():
                            continue
                        val = float(raw_price)

                        # Imagen
                        img_tag = t.query_selector("img")
                        img_url = ""
                        if img_tag:
                            src = img_tag.get_attribute("src") or img_tag.get_attribute("data-src")
                            if src:
                                if src.startswith("//"):
                                    src = "https:" + src
                                elif src.startswith("/"):
                                    src = urljoin(URL_BASE, src)
                                img_url = src

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

        browser.close()

    lista = list(catalogo_final.values())
    print(f"\n🚀 Finalizado. Productos totales: {len(lista)}")
    with open("productos.json", "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
