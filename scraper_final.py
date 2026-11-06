import time
import re
import os
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

# Lista completa de categorías y subcategorías (según categorias.txt)
CATEGORIAS = [
    "componentes-de-pc/combos-de-actualizacion",
    "componentes-de-pc/discos-duros-mecanicos",
    "componentes-de-pc/discos-solidos-ssd",
    "componentes-de-pc/memorias-ram/desktop",
    "componentes-de-pc/memorias-ram/notebook",
    "componentes-de-pc/microprocesadores",
    "componentes-de-pc/motherboards/amd",
    "componentes-de-pc/motherboards/intel",
    "componentes-de-pc/placas-de-video",
    "componentes-de-pc/gabinetes",
    "componentes-de-pc/placas-de-sonido",
    "componentes-de-pc/fuentes",
    "componentes-de-pc/pastas-termicas",
    "componentes-de-pc/placas-de-red",
    "componentes-de-pc/refrigeracion/coolers-y-watercoolers",
    "componentes-de-pc/refrigeracion/fan-coolers",
    "pc-de-escritorio/hogar-y-oficina",
    "pc-de-escritorio/gamer",
    "pc-de-escritorio/ia-local",
    "pc-de-escritorio/mini-pcs",
    "pc-de-escritorio/combos-de-actualizacion",
    "pc-de-escritorio/powered-by-msi",
    "notebooks",
    "monitores/19-a-26-pulgadas",
    "monitores/27-a-32-pulgadas",
    "monitores/33-pulgadas-y-superior",
    "monitores/proyectores-y-pantallas",
    "perifericos/teclados",
    "perifericos/gaming-kit",
    "perifericos/teclado-mouse",
    "perifericos/mousepads",
    "perifericos/mouse",
    "perifericos/auriculares/gamer",
    "perifericos/auriculares/oficina-y-urbano",
    "perifericos/audio/barras-de-sonido",
    "perifericos/audio/parlantes",
    "perifericos/audio/portatiles",
    "perifericos/joysticks",
    "perifericos/webcams",
    "perifericos/lectores-codigo-de-barras",
    "perifericos/microfonos",
    "perifericos/simuladores",
    "conectividad-y-redes/access-point",
    "conectividad-y-redes/modem-router",
    "conectividad-y-redes/routers",
    "conectividad-y-redes/switchs",
    "impresion-y-scanners/impresoras-laser",
    "impresion-y-scanners/impresoras-sistema-continuo",
    "impresion-y-scanners/impresoras-inyeccion-tinta",
    "impresion-y-scanners/impresoras-termicas",
    "impresion-y-scanners/impresion-3d/impresoras-3d",
    "impresion-y-scanners/impresion-3d/consumibles",
    "impresion-y-scanners/toners",
    "impresion-y-scanners/cartuchos-de-tinta",
    "relojes-smartwatch",
    "almacenamiento-portatil/microsd",
    "almacenamiento-portatil/pendrives",
    "almacenamiento-portatil/discos-externos",
    "tablets",
    "tabletas-digitalizadoras",
    "televisores-y-tv-box/smart-tvs",
    "televisores-y-tv-box/tv-box",
    "streaming",
    "software",
    "camaras-ip",
    "accesorios/fundas-y-mochilas",
    "accesorios/bases-refrigerantes",
    "accesorios/cargadores",
    "accesorios/cables",
    "accesorios/merchandising",
    "soportes",
    "sillas-gamers/sillas-gamers",
    "estabilizadores-ups-y-zapatillas/estabilizadores",
    "estabilizadores-ups-y-zapatillas/ups",
    "estabilizadores-ups-y-zapatillas/zapatillas"
]

rows = []

def format_category(cat_name):
    parts = cat_name.split("/")
    return " > ".join([p.replace("-", " ").title() for p in parts])

def scrape_categoria(cat_url, cat_name):
    driver.get(cat_url)
    time.sleep(5)

    paginas = [cat_url]
    try:
        enlaces = driver.find_elements("css selector", ".pagination a")
        for e in enlaces:
            href = e.get_attribute("href")
            if href and href not in paginas:
                paginas.append(href)
    except Exception as exc:
        print(f"No se pudieron leer las páginas de {cat_name}: {exc}")

    for url in paginas:
        driver.get(url)
        time.sleep(5)
        productos = driver.find_elements("css selector", "div.product-box")
        print(f"Procesando {cat_name} - {len(productos)} productos en {url}")

        for p in productos:
            titulo = None
            precio_final = None
            imagen = None

            try:
                enlace = p.find_element("css selector", ".product-box-name a, .product-box-body a")
                titulo = enlace.text.strip()
            except Exception:
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
            except Exception:
                pass

            try:
                imagen = p.find_element("css selector", "img").get_attribute("src")
            except Exception:
                pass

            if titulo and precio_final and imagen:
                rows.append({
                    "SKU": titulo,
                    "Name": titulo,
                    "Regular price": precio_final,
                    "Categories": format_category(cat_name),
                    "Images": imagen
                })

try:
    for cat in CATEGORIAS:
        scrape_categoria(f"{URL_HOME}{cat}", cat)
finally:
    driver.quit()

if not rows:
    raise RuntimeError(
        "El scraper no encontró productos. No se generará ni publicará un CSV vacío; "
        "revisá los selectores y la respuesta del sitio."
    )

output_dir = "dist"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "productos.csv")
df = pd.DataFrame(rows, columns=["SKU", "Name", "Regular price", "Categories", "Images"])
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"✅ Archivo '{output_path}' generado con {len(rows)} productos.")
