import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL_HOME = "https://www.venex.com.ar/"
MARGEN = 1.15

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

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
    time.sleep(15)  # esperar que cargue productos

    productos = driver.find_elements("css selector", "div.contenedorDetalleProd")

    for p in productos:
        # Título
        titulo = p.find_element("css selector", "h1.tituloProducto").text

        # Precio especial Venex
        precios = p.find_elements("css selector", ".precioProducto, .price, .special-price")
        precio_especial = None
        for pr in precios:
            texto = pr.text
            if "Venex" in texto or "Precio especial" in texto:
                precio_especial = texto
                break

        if not precio_especial:
            continue

        # Convertir precio a número y aplicar margen
        precio_num = int("".join([c for c in precio_especial if c.isdigit()]))
        precio_final = round(precio_num * MARGEN)

        # Imagen
        try:
            imagen = p.find_element("css selector", "img").get_attribute("src")
        except:
            try:
                imagen = p.find_element("css selector", "div.detalle-producto-gal-item").get_attribute("style")
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
