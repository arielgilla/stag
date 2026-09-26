import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

URL_HOME = "https://www.venex.com.ar/"
MARGEN = 1.15

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

# 🔹 Lista completa de categorías
CATEGORIAS = [
    "componentes-de-pc/motherboards/intel",
    "componentes-de-pc/motherboards/amd",
    "componentes-de-pc/microprocesadores/intel",
    "componentes-de-pc/microprocesadores/amd",
    "componentes-de-pc/memorias-ram/desktop",
    "componentes-de-pc/memorias-ram/notebook",
    "componentes-de-pc/placas-de-video",
    "componentes-de-pc/placas-de-sonido",
    "componentes-de-pc/placas-de-red",
    "componentes-de-pc/discos-solidos-ssd",
    "componentes-de-pc/discos-duros-mecanicos",
    "componentes-de-pc/fuentes",
    "componentes-de-pc/gabinetes",
    "componentes-de-pc/refrigeracion",
    "componentes-de-pc/pastas-termicas",
    "componentes-de-pc/combos-de-actualizacion",
    "notebooks",
    "monitores/19-a-28-pulgadas",
    "monitores/27-a-32-pulgadas",
    "monitores/33-pulgadas-y-superior",
    "monitores/proyectores-y-pantallas",
    "perifericos/teclados",
    "perifericos/mousepads",
    "perifericos/auriculares/gamer",
    "perifericos/auriculares/oficina-y-urbano",
    "perifericos/microfonos",
    "perifericos/webcams",
    "perifericos/joysticks-volantes-y-simuladores",
    "perifericos/audio/portatiles",
    "perifericos/placas-de-sonido",
    "almacenamiento-portatil/pendrives",
    "almacenamiento-portatil/microsd",
    "almacenamiento-portatil/discos-externos",
    "impresion/impresoras-laser",
    "impresion/inyeccion-de-tinta",
    "impresion/termicas",
    "impresion/impresion-3d",
    "impresion/consumibles",
    "redes/routers",
    "redes/switchs",
    "redes/access-point",
    "redes/modem-router",
    "sillas-gamers",
    "software",
    "televisores",
    "tablets",
    "smartwatch",
    "camaras-ip",
    "accesorios"
]

rows = []

def format_category(cat_name):
    # Reemplazar "/" por ">" para jerarquía
    # Reemplazar "-" por espacio para legibilidad
    parts = cat_name.split("/")
    formatted = " > ".join([p.replace("-", " ").title() for p in parts])
    return formatted

def scrape_categoria(cat_url, cat_name):
    driver.get(cat_url)
    time.sleep(5)

    # 🔹 Obtener todas las páginas de la categoría
    paginas = [cat_url]
    try:
        enlaces = driver.find_elements("css selector", ".pagination a")
        for e in enlaces:
            href = e.get_attribute("href")
            if href and href not in paginas:
                paginas.append(href)
    except:
        pass

    # 🔹 Recorrer todas las páginas
    for url in paginas:
        driver.get(url)
        time.sleep(5)
        productos = driver.find_elements("css selector", "div.product-box")
        print(f"Procesando {cat_name} - {len(productos)} productos en {url}")

        for p in productos:
            titulo = None
            precio_final = None
            imagenes_str = None

            try:
                enlace = p.find_element("css selector", ".product-box-name a, .product-box-body a")
                titulo = enlace.text.strip()
            except:
                pass

            try:
                precio_elementos = p.find_elements("css selector", ".product-box-price span, .price")
                for elem in precio_elementos:
                    texto = elem.text.strip()
                    if any(c.isdigit() for c in texto):
                        numeros = re.sub(r"[^\d]", "", texto)
                        if numeros:
                            precio_num = int(numeros)
                            precio_final = round(precio_num * MARGEN)
                            break
            except:
                pass

            try:
                imagenes = [img.get_attribute("src") for img in p.find_elements("css selector", "img")]
                if "notebooks" in cat_name:
                    imagenes = imagenes[1:]  # ignorar la primera
                imagenes_str = ",".join(imagenes)
            except:
                pass

            if titulo and precio_final and imagenes_str:
                rows.append({
                    "SKU": titulo,  # SKU = Nombre del producto
                    "Name": titulo,
                    "Regular price": precio_final,
                    "Categories": format_category(cat_name),
                    "Images": imagenes_str
                })

for cat in CATEGORIAS:
    scrape_categoria(f"{URL_HOME}{cat}", cat)

driver.quit()

df = pd.DataFrame(rows, columns=["SKU", "Name", "Regular price", "Categories", "Images"])
df.to_csv("productos.csv", index=False, encoding="utf-8-sig")

print(f"✅ Archivo 'productos.csv' generado con {len(rows)} productos.")
