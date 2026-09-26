import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL_HOME = "https://www.venex.com.ar/"
CATEGORIA_TEST = "perifericos/mouse"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

def scrape_categoria(cat_url):
    driver.get(cat_url)
    # Esperar hasta que aparezcan productos
    try:
        productos = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.product-box"))
        )
    except:
        print("❌ No se encontraron productos en la página")
        return

    print(f"✅ Se encontraron {len(productos)} productos en {cat_url}")
    for p in productos:
        try:
            enlace = p.find_element(By.CSS_SELECTOR, ".product-box-name a, .product-box-body a")
            titulo = enlace.text.strip()
            print(" -", titulo)
        except:
            pass

scrape_categoria(f"{URL_HOME}{CATEGORIA_TEST}")
driver.quit()
