import time
import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

URL_HOME = "https://www.venex.com.ar/"
MARGEN = 1.15

# Configuración de Selenium para usar Chromium en GitHub Actions
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service("/usr/bin/chromedriver")  # ruta de chromedriver en el runner
driver = webdriver.Chrome(service=service, options=options)

# Paso 1: obtener todas las categorías y subcategorías desde el home
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

    for p in productos:
        # Título
        try:
            titulo = p.find_element("css selector", "a").text.strip()
        except:
            titulo = None

        # Precio
        precio_final = None
        try:
            precio_texto = p.find_element("css selector", ".product-box-price, .price").text
            # Limpiar texto: dejar solo dígitos
            numeros = re.sub(r"[^\d]", "", precio_texto)
            if numeros.isdigit():
                precio_num = int(numeros)
                precio_final = round(precio_num * MARGEN)
        except:
            pass

        # Imagen
        try:
            imagen = p.find_element("css selector", "img").get_attribute("src")
        except:
            imagen = None

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

print("✅ Archivo 'productos.json' generado con todos los productos (precio especial Venex + 15%).")
