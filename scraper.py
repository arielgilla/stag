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

        # URLs clave para poblar el catálogo
        urls_a_visitar = [
            "https://www.venex.com.ar/procesadores",
            "https://www.venex.com.ar/placas-de-video",
            "https://www.venex.com.ar/memorias-ram",
            "https://www.venex.com.ar/discos-rigidos-y-ssds"
        ]

        for url in urls_a_visitar:
            try:
                print(f"Navegando a: {url}")
                # Usamos domcontentloaded para evitar bloqueos por keep-alives de red de Cloudflare
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(4000) # Tiempo prudencial para que cargue la grilla por JS

                # Extracción robusta basada en la estructura común de e-commerce y tiendas VTEX/Custom
                productos_encontrados = await page.evaluate('''() => {
                    // Seleccionamos cualquier bloque que parezca una tarjeta de producto
                    const items = document.querySelectorAll('div, article, li');
                    const results = [];
                    
                    items.forEach(item => {
                        // Buscamos elementos hijos que contengan textos típicos de producto y precio
                        const textContent = item.innerText || '';
                        if (textContent.includes('$') && (textContent.length > 20 && textContent.length < 300)) {
                            const titleEl = item.querySelector('h2, h3, h4, a, strong');
                            const priceEl = item.querySelector('.price, .precio, [id*="price"], [class*="price"]');
                            const imgEl = item.querySelector('img');
                            
                            const title = titleEl ? titleEl.innerText.trim() : '';
                            const price = priceEl ? priceEl.innerText.trim() : '';
                            const img = imgEl ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '') : '';
                            
                            if (title && price && price.includes('$')) {
                                results.push({ title, price, img });
                            }
                        }
                    });
                    return results;
                ''')

                print(f"Productos extraídos crudos en {url}: {len(productos_encontrados)}")

                for prod in productos_encontrados:
                    titulo = prod['title'].replace('\n', ' ').strip()
                    if not titulo or len(titulo) < 4 or titulo in vistos:
                        continue

                    raw_price = prod['price']
                    clean_price = ''.join(c for c in raw_price if c.isdigit() or c == ',' or c == '.')
                    clean_price = clean_price.replace('.', '').replace(',', '.').split('.')[0]
                    
                    if not clean_price:
                        continue

                    try:
                        costo = float(clean_price)
                    except ValueError:
                        continue

                    if costo <= 100:
                        continue

                    precio_venta = round(costo * MARGEN_GANANCIA)

                    img_url = prod['img']
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
