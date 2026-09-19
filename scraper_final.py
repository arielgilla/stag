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

for cat in CATEGORIAS:
    url = f"{URL_HOME}{cat}"
    while True:
        driver.get(url)
        time.sleep(5)

        productos = driver.find_elements("css selector", "div.product-box")
        print(f"Procesando categoría: {cat} - encontrados {len(productos)} productos en esta página")

        for p in productos:
            titulo = None
            precio_final = None
            imagen = None
            link = None

            # Título y URL
            try:
                enlace = p.find_element("css selector", ".product-box-name a, .product-box-body a")
                titulo = enlace.text.strip()
                link = enlace.get_attribute("href")
            except:
                pass

            # Precio
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

            # Imagen (se guarda tal cual viene, sin modificar)
            try:
                imagen = p.find_element("css selector", "img").get_attribute("src")
            except:
                pass

            # 🔹 Filtrar: solo guardar si hay precio e imagen
            if precio_final and imagen:
                rows.append({
                    "Nombre": titulo,
                    "Precio": precio_final,
                    "Imagen": imagen,
                    "Categoría": cat,
                    "URL": link
                })

        # Paginación: buscar botón "siguiente"
        try:
            next_btn = driver.find_element("css selector", ".pagination a.next")
            next_url = next_btn.get_attribute("href")
            if next_url and next_url != url:
                url = next_url
                continue
        except:
            pass
        break

driver.quit()

# 🔹 Guardar directamente en CSV
df = pd.DataFrame(rows)
df.to_csv("productos.csv", index=False, encoding="utf-8-sig")

print(f"✅ Archivo 'productos.csv' generado con {len(rows)} productos.")
