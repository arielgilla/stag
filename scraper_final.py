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

# Paso 1: obtener todas las categorías y subcategorías
driver.get(URL_HOME)
time.sleep(10)

categorias = []
links = driver.find_elements("css selector", "a")
for link in links:
    href = link.get_attribute("href")
    if href and "venex.com.ar" in href:
        if any(x in href for x in ["componentes-de-pc", "computadoras", "perifericos", "almacenamiento", "monitores"]):
            categorias.append(href)

categorias = list(set(categorias))
print(f"Se encontraron {len(categorias)} categorías/subcategorías")

productos_totales = []

# Paso 2: recorrer cada categoría
for url in categorias:
    driver.get(url)
    time.sleep(15)

    productos = driver.find_elements("css selector", "div.product-box")

    print(f"Procesando categoría: {url} - encontrados {len(productos)} productos")

    for p in productos:
        titulo = None
        precio_final = None
        imagen = None

        # Título
        try:
            titulo = p.find_element("css selector", "a").text.strip()
        except:
            pass

        # Precio
        try:
            precio_texto = p.find_element("css selector", ".product-box-price, .price").text
            print(f"Precio bruto capturado: {precio_texto}")
            numeros = re.sub(r"[^\d]", "", precio_texto)
            if numeros:
                precio_num = int(numeros)
                precio_final = round(precio_num * MARGEN)
        except:
            pass

        # Imagen
        try:
            imagen = p.find_element("css selector", "img").get_attribute("src")
        except:
            pass

        productos_totales.append({
            "categoria": url,
            "titulo": titulo,
            "precio_final": precio_final,
            "imagen": imagen
        })

driver.quit()

# Paso 3: guardar resultados en productos.json
with open("productos.json", "w", encoding="utf-8") as f:
    json.dump(productos_totales, f, ensure_ascii=False, indent=4)

print(f"✅ Archivo 'productos.json' generado con {len(productos_totales)} productos.")
