import json
import asyncio
from playwright.async_api import async_playwright

MARGEN_GANANCIA = 1.15

async def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    async with async_playwright() as p:
        # Lanzar un navegador real en modo headless para burlar protecciones anti-bot
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        # URLs estratégicas del catálogo de Venex para asegurar una extracción masiva y real
        urls_a_visitar = [
            "https://www.venex.com.ar/resultado-busqueda.htm?keywords=&limit=48&page=1",
            "https://www.venex.com.ar/resultado-busqueda.htm?keywords=&limit=48&page=2",
            "https://www.venex.com.ar/procesadores",
            "https://www.venex.com.ar/placas-de-video",
            "https://www.venex.com.ar/memorias-ram",
            "https://www.venex.com.ar/discos-rigidos-y-ssds"
        ]

        for url in urls_a_visitar:
            try:
                print(f"Navegando a: {url}")
                # Cargar la página esperando el contenido y el DOM
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000) # Pausa breve para estabilizar renderizado de elementos

                # Extracción mediante JavaScript ejecutado en el contexto del navegador real
                productos_encontrados = await page.evaluate('''() => {
                    const items = document.querySelectorAll('div.product, div.item, div.card, div[data-id]');
                    const results = [];
                    
                    items.forEach(item => {
                        const titleEl = item.querySelector('h2, h3, a.title, a.name, [title]');
                        const priceEl = item.querySelector('.price, .precio, [class*="price"]');
                        const imgEl = item.querySelector('img');
                        
                        const title = titleEl ? (titleEl.getAttribute('title') || titleEl.innerText) : '';
                        const priceText = priceEl ? priceEl.innerText : '';
                        const imgSrc = imgEl ? (imgEl.getAttribute('data-src') || imgEl.getAttribute('src') || '') : '';
                        
                        if (title && priceText) {
                            results.push({
                                title: title.trim(),
                                price: priceText.trim(),
                                img: imgSrc.trim()
                            });
                        }
                    });
                    return results;
                }''')

                for prod in productos_encontrados:
                    titulo = prod['title']
                    if not titulo or len(titulo) < 4 or titulo in vistos:
                        continue

                    # Limpieza y conversión del precio real de Venex
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

                    # Procesamiento seguro de la URL de la imagen
                    img_url = prod['img']
                    if img_url.startswith('/'):
                        img_url = f"https://www.venex.com.ar{img_url}"
                    elif not img_url.startswith('http'):
                        continue

                    catalogo_final[titulo] = {
                        "titulo": titulo,
                        "precio_venta": precio_venta,
                        "imagen": img_url,
                        "stock": True
                    }
                    vistos.add(titulo)

            except Exception as e:
                print(f"Error procesando la URL {url}: {e}")
                continue

        await browser.close()

    lista_final = list(catalogo_final.values())
    print(f"Sincronización en vivo finalizada. Total de productos reales extraídos: {len(lista_final)}")

    # Guardado exclusivo de los datos reales sincronizados
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
