import json
import re
import time
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

CATEGORIAS = {
    "Notebooks": "/computadoras/notebooks",
    "Placas de Video": "/componentes-de-pc/placas-de-video",
    "Monitores": "/monitores",
    "Procesadores": "/componentes-de-pc/microprocesadores",
    "Memorias RAM": "/componentes-de-pc/memorias-ram",
    "Almacenamiento SSD": "/componentes-de-pc/discos-solidos-ssd",
    "Discos Rigidos": "/componentes-de-pc/discos-rigidos",
    "Motherboards": "/componentes-de-pc/motherboards",
    "Fuentes": "/componentes-de-pc/fuentes",
    "Gabinetes": "/componentes-de-pc/gabinetes",
    "Coolers y Refrigeracion": "/componentes-de-pc/coolers-y-refrigeracion",
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

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    for categoria, path in CATEGORIAS.items():
        print(f"🔄 Extrayendo categoría: {categoria.upper()}")
        url = f"{URL_BASE}{path}"
        driver.get(url)
        time.sleep(8)

        tarjetas = driver.find_elements(By.CSS_SELECTOR, "div.item-product")
        print(f"➡️ {len(tarjetas)} productos detectados en {categoria}")

        for t in tarjetas:
            try:
                titulo_elem = t.find_element(By.CSS_SELECTOR, "h2 a, h3 a, .product-title a")
                titulo = titulo_elem.text.strip()
                if not titulo or titulo.lower() in vistos:
                    continue

                precio_elem = t.find_element(By.CSS_SELECTOR, ".price")
                raw_price = re.sub(r"[^\d]", "", precio_elem.text)
                if not raw_price.isdigit():
                    continue
                val = float(raw_price)

                img_elem = t.find_element(By.CSS_SELECTOR, "img")
                img_url = img_elem.get_attribute("src") or ""
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = urljoin(URL_BASE, img_url)

                catalogo_final[titulo.lower()] = {
                    "titulo": titulo,
                    "categoria": categoria,
                    "precio_venta": round(val * MARGEN_GANANCIA),
                    "imagen": img_url,
                    "stock": True
                }
                vistos.add(titulo.lower())
            except Exception as e:
                print(f"⚠️ Error procesando producto: {e}")

    driver.quit()

    lista = list(catalogo_final.values())
    print(f"\n🚀 Finalizado. Productos totales: {len(lista)}")
    with open("productos.json", "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
