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

        categorias_urls = {
            "Procesadores": "https://www.venex.com.ar/procesadores",
            "Placas de Video": "https://www.venex.com.ar/placas-de-video",
            "Memorias RAM": "https://www.venex.com.ar/memorias-ram",
            "Discos y SSDs": "https://www.venex.com.ar/discos-rigidos-y-ssds"
        }

        for categoria, url in categorias_urls.items():
            try:
                print(f"Navegando a categoría '{categoria}': {url}")
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000)

                # Buscamos tarjetas de productos usando selectores genéricos pero seguros en Python
                tarjetas = await page.query_selector_all('.item, .product-item, .box-product, [class*="product"], [class*="item"]')
                print(f"Elementos encontrados en {categoria}: {len(tarjetas)}")

                for tarjeta in tarjetas:
                    try:
                        text = await tarjeta.inner_text()
                        if not text or "$" not in text:
                            continue

                        # Buscar título dentro de la tarjeta
                        title_el = await tarjeta.query_selector('h2, h3, h4, .name, .title, a')
                        if not title_el:
                            continue
                        titulo = (await title_el.inner_text()).replace('\n', ' ').strip()

                        if not titulo or len(titulo) < 5 or titulo in vistos:
                            continue

                        # Buscar precio dentro de la tarjeta
                        price_el = await tarjeta.query_selector('.price, .precio, [class*="price"], [class*="precio"]')
                        if not price_el:
                            continue
                        raw_price = await price_el.inner_text()

                        if "$" not in raw_price:
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

                        # Buscar imagen oficial del producto
                        img_el = await tarjeta.query_selector('img')
                        img_url = ""
                        if img_el:
                            img_url = await img_el.get_attribute('src') or await img_el.get_attribute('data-src') or await img_el.get_attribute('data-original') or ""
                            if img_url.startswith('/'):
                                img_url = f"https://www.venex.com.ar{img_url}"
                            elif not img_url.startswith('http') or 'placeholder' in img_url or 'logo' in img_url:
                                img_url = ""

                        catalogo_final[titulo] = {
                            "titulo": titulo,
                            "categoria": categoria,
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
    print(f"Total final de productos procesados con categoría e imágenes: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
