import chromedriver_autoinstaller
from seleniumwire import webdriver  # usar selenium-wire en vez de selenium
from selenium.webdriver.chrome.options import Options
import time

chromedriver_autoinstaller.install()

URL_BASE = "https://www.venex.com.ar/computadoras/notebooks"

def capturar_requests():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(URL_BASE)

    print("⏳ Esperando 15 segundos para que cargue la página completa...")
    time.sleep(15)

    # Guardar todas las peticiones que hizo la página
    with open("debug_requests.txt", "w", encoding="utf-8") as f:
        for request in driver.requests:
            if request.response:
                f.write(f"{request.url} -> {request.response.status_code}\n")

    driver.quit()
    print("✅ Archivo 'debug_requests.txt' generado con todas las URLs cargadas.")

if __name__ == "__main__":
    capturar_requests()
