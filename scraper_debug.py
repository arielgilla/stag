import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# Instala automáticamente el ChromeDriver correcto
chromedriver_autoinstaller.install()

URL_BASE = "https://www.venex.com.ar/computadoras/notebooks"  # ejemplo: categoría Notebooks

def guardar_html():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(URL_BASE)

    # Esperar más tiempo para que se ejecute el JavaScript y se carguen los productos
    print("⏳ Esperando 15 segundos para que cargue la página completa...")
    time.sleep(15)

    # Guardar el HTML completo que ve Selenium
    with open("debug_pagina.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    driver.quit()
    print("✅ Archivo 'debug_pagina.html' generado. Abrilo en tu navegador para inspeccionar.")

if __name__ == "__main__":
    guardar_html()
