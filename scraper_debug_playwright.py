import asyncio
from playwright.async_api import async_playwright

URL_BASE = "https://www.venex.com.ar/computadoras/notebooks"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        requests_log = []

        # Interceptar todas las peticiones
        page.on("response", lambda response: requests_log.append(f"{response.url} -> {response.status}"))

        await page.goto(URL_BASE)
        await page.wait_for_timeout(15000)  # esperar 15 segundos

        # Guardar todas las URLs en un archivo
        with open("debug_requests.txt", "w", encoding="utf-8") as f:
            for line in requests_log:
                f.write(line + "\n")

        await browser.close()
        print("✅ Archivo 'debug_requests.txt' generado con todas las URLs cargadas.")

if __name__ == "__main__":
    asyncio.run(main())
