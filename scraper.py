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

        # Mapeo de URLs a sus respectivas categorías oficiales
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

                # Buscar contenedores típicos de productos en tiendas de e-commerce modernas
                # (Tarjetas de producto, items de grilla)
                productos_encontrados = await page.evaluate('''() => {
                    const items = document.querySelectorAll('.item, .product-item, .box-product, [class*="product"], [class*="item"]');
                    const results = [];
                    
                    items.forEach(el => {
                        const text = el.innerText || '';
                        if (text.includes('$')) {
                            // Buscar título (usualmente h2, h3, h4 o etiquetas a con texto descriptivo)
                            const titleEl = el.querySelector('h2, h3, h4, .name, .title, a');
                            // Buscar precio
                            const priceEl = el.querySelector('.price, .precio, [class*="price"], [class*="precio"]');
                            // Buscar imagen del producto
                            const imgEl = el.querySelector('img');
                            
                            const title = titleEl ? titleEl.innerText.trim() : '';
                            const price = priceEl ? priceEl.innerText.trim() : '';
                            let img = '';
                            
                            if (imgEl) {
                                img = imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || imgEl.getAttribute('data-original') || '';
                            }
                            
                            if (title && price && price.includes('$') && title.length > 5) {
                                results.push({ title, price, img });
                            }
                        }
                    });
                    return results;
                ''')

                print(f"Productos válidos detectados en {categoria}: {len(productos_encontrados)}")

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
