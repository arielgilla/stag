import os
import re
import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL_HOME = "https://www.venex.com.ar/"
MARGEN = 1.15
ARCHIVO_CSV = os.path.join("dist", "productos.csv")

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
    "estabilizadores-ups-y-zapatillas/zapatillas",
]

def format_category(cat_name):
    return " > ".join(
        parte.replace("-", " ").title()
        for parte in cat_name.split("/")
    )

def crear_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def obtener_paginas(driver, cat_url):
    driver.get(cat_url)
    time.sleep(5)

    paginas = [cat_url]
    enlaces = driver.find_elements("css selector", ".pagination a")

    for enlace in enlaces:
        href = enlace.get_attribute("href")
        if href and href not in paginas:
            paginas.append(href)

    return paginas

def extraer_producto(producto, categoria):
    titulo = None
    precio_final = None
    imagen = None

    try:
        enlace = producto.find_element(
            "css selector",
            ".product-box-name a, .product-box-body a",
        )
        titulo = enlace.text.strip()
    except Exception:
        pass

    try:
        elementos_precio = producto.find_elements(
            "css selector",
            ".product-box-price span, .price",
        )
        for elemento in elementos_precio:
            texto = elemento.text.strip()
            numeros = re.sub(r"[^\d]", "", texto)
            if numeros:
                precio_final = round(int(numeros) * MARGEN)
                break
    except Exception:
        pass

    try:
        imagen = producto.find_element(
            "css selector",
            "img",
        ).get_attribute("src")
    except Exception:
        pass

    if not titulo or not precio_final or not imagen:
        return None

    return {
        # Se conserva el comportamiento anterior: el título se usa como SKU.
        "SKU": titulo,
        "Name": titulo,
        "Regular price": precio_final,
        "Categories": format_category(categoria),
        "Images": imagen,
    }

def main():
    driver = crear_driver()
    filas = []

    try:
        for categoria in CATEGORIAS:
            url_categoria = f"{URL_HOME}{categoria}"

            try:
                paginas = obtener_paginas(driver, url_categoria)
            except Exception as exc:
                print(f"Error al abrir la categoría {categoria}: {exc}")
                continue

            for url in paginas:
                try:
                    driver.get(url)
                    time.sleep(5)
                    productos = driver.find_elements(
                        "css selector",
                        "div.product-box",
                    )
                    print(
                        f"Procesando {categoria}: "
                        f"{len(productos)} productos en {url}"
                    )

                    for producto in productos:
                        fila = extraer_producto(producto, categoria)
                        if fila:
                            filas.append(fila)

                except Exception as exc:
                    print(f"Error procesando {url}: {exc}")

    finally:
        driver.quit()

    if not filas:
        raise RuntimeError(
            "No se encontraron productos. No se generó el CSV; "
            "revisa la respuesta de Venex y los selectores CSS."
        )

    os.makedirs(os.path.dirname(ARCHIVO_CSV), exist_ok=True)

    columnas = ["SKU", "Name", "Regular price", "Categories", "Images"]
    df = pd.DataFrame(filas, columns=columnas)
    df.to_csv(ARCHIVO_CSV, index=False, encoding="utf-8-sig")

    print(f"CSV generado: {ARCHIVO_CSV} ({len(filas)} productos)")

if __name__ == "__main__":
    main()
