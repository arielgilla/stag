import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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

    # Guardar el HTML completo que ve Selenium
    with open("debug_pagina.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    driver.quit()
    print("✅ Archivo 'debug_pagina.html' generado. Abrilo en tu navegador para inspeccionar.")

if __name__ == "__main__":
    guardar_html()
