import time
import json
import re
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

# Lista completa de categorías y subcategorías
CATEGORIAS = [
    # Componentes de PC
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

    # Notebooks
    "notebooks",

    # Monitores
    "monitores/19-a-28-pulgadas",
    "monitores/27-a-32-pulgadas",
    "monitores/33-pulgadas-y-superior",
    "monitores/proyectores-y-pantallas",

    # Periféricos
    "perifericos/teclados",
    "perifericos/mousepads",
    "perifericos/auriculares/gamer",
    "perifericos/auriculares/oficina-y-urbano",
    "perifericos/microfonos",
    "perifericos/webcams",
    "perifericos/joysticks-volantes-y-simuladores",
    "perifericos/audio/portatiles",
    "perifericos/placas-de-sonido",

    # Almacenamiento portátil
    "almacenamiento-portatil/pendrives",
    "almacenamiento-portatil/microsd",
    "almacenamiento-portatil/discos-externos",

    # Impresión
    "impresion/impresoras-laser",
    "impresion/inyeccion-de-tinta",
    "impresion/termicas",
    "impresion/impresion-3d",
    "impresion/consumibles",

    # Redes
    "redes/routers",
    "redes/switchs",
    "redes/access-point",
    "redes/modem-router",

    # Otros
    "sillas-gamers",
    "software",
    "televisores",
    "tablets",
    "smartwatch",
    "camaras-ip",
    "accesorios"
]

productos_por_categoria = {}

for cat in CATEGORIAS:
    url = f"{URL_HOME}{cat}"
    driver.get(url)
    time.sleep(15)

    productos = driver.find_elements("css selector", "div.product-box")
    print(f"Procesando categoría: {cat} - encontrados {len(productos)} productos")

    productos_lista = []

    for p in productos:
        titulo = None
        precio_final = None
        imagen = None

        # Título
        try:
            titulo = p.find_element("css selector", ".product-box-name a, .product-box-body a").text.strip()
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

        # Imagen
        try:
            imagen = p.find_element("css selector", "img").get_attribute("src")
        except:
            pass

        productos_lista.append({
            "titulo": titulo,
            "precio_final": precio_final,
            "imagen": imagen
        })

    productos_por_categoria[cat] = productos_lista

driver.quit()

with open("productos.json", "w", encoding="utf-8") as f:
    json.dump(productos_por_categoria, f, ensure_ascii=False, indent=4)

print(f"✅ Archivo 'productos.json' generado con {sum(len(v) for v in productos_por_categoria.values())} productos.")
