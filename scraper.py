import json
import asyncio
from playwright.async_api import async_playwright

MARGEN_GANANCIA = 1.15

async def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        urls_a_visitar = [
            "https://www.venex.com.ar/procesadores",
            "https://www.venex.com.ar/placas-de-video",
            "https://www.venex.com.ar/memorias-ram",
            "https://www.venex.com.ar/discos-rigidos-y-ssds"
        ]

        for url in urls_a_visitar:
            try:
                print(f"Navegando a: {url}")
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)

                # Extracción simplificada y segura directamente desde Python usando selectores genéricos de elementos
                elements = await page.query_selector_all("div, article")
                
                for el in elements:
                    try:
                        text = await el.inner_text()
                        if not text or "$" not in text or len(text) > 400:
                            continue
                            
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        if len(lines) < 2:
                            continue

                        # Intentar identificar título y precio de las líneas del bloque
                        titulo = ""
                        raw_price = ""
                        
                        for line in lines:
                            if "$" in line and len(line) < 20:
                                raw_price = line
                            elif len(line) > 10 and not titulo:
                                titulo = line

                        if not titulo or not raw_price:
                            continue

                        if titulo in vistos:
                            continue

                        # Limpieza del precio
                        clean_price = ''.join(c for c in raw_price if c.isdigit() or c == ',' or c == '.')
                        clean_price = clean_price.replace('.', '').replace(',', '.').split('.')[0]
                        
                        if not clean_price:
                            continue

                        costo = float(clean_price)
                        if costo <= 100:
                            continue

                        precio_venta = round(costo * MARGEN_GANANCIA)

                        # Buscar imagen dentro del bloque de forma segura
                        img_el = await el.query_selector("img")
                        img_url = ""
                        if img_el:
                            img_url = await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or ""
                            if img_url.startswith('/'):
                                img_url = f"https://www.venex.com.ar{img_url}"
                            elif not img_url.startswith('http'):
                                img_url = ""

                        catalogo_final[titulo] = {
                            "titulo": titulo,
                            "precio_venta": precio_venta,
                            "imagen": img_url,
                            "stock": True
                        }
                        vistos.add(titulo)
                    except Exception:
                        continue

            except Exception as e:
                print(f"Error procesando {url}: {e}")
                continue

        await browser.close()

    lista_final = list(catalogo_final.values())
    print(f"Total final de productos procesados: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
