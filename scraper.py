import json
import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

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

        print("Navegando a la página principal para descubrir categorías...")
        try:
            await page.goto(URL_BASE, timeout=40000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Error al cargar la página principal: {e}")
            await browser.close()
            return

        # Descubrimiento dinámico de enlaces del menú de navegación
        enlaces = await page.query_selector_all('nav a, header a, .menu a')
        categorias_urls = {}
        
        for enlace in enlaces:
            texto = (await enlace.inner_text()).strip()
            href = await enlace.get_attribute('href')
            
            if href and texto and len(texto) > 2:
                # Filtrar enlaces irrelevantes
                href_lower = href.lower()
                if not any(x in href_lower for x in ['contacto', 'login', 'carrito', '#', 'javascript']):
                    full_url = urljoin(URL_BASE, href)
                    if full_url.startswith(URL_BASE):
                        categorias_urls[texto] = full_url

        print(f"Se descubrieron {len(categorias_urls)} categorías para explorar.")

        for categoria, url in categorias_urls.items():
            pagina_actual = 1
            while True:
                url_paginada = f"{url}?page={pagina_actual}" if "?" not in url else f"{url}&page={pagina_actual}"
                print(f"Explorando: {categoria} - Página {pagina_actual} ({url_paginada})")
                
                try:
                    await page.goto(url_paginada, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                    
                    tarjetas = await page.query_selector_all('.item, .product-item, .box-product, [class*="product"]')
                    
                    if not tarjetas:
                        print(f"No hay más productos en {categoria}.")
                        break
                    
                    productos_nuevos = 0
                    
                    for tarjeta in tarjetas:
                        try:
                            # Título
                            title_el = await tarjeta.query_selector('h2, h3, h4, .name, .title, a')
                            if not title_el: continue
                            titulo = (await title_el.inner_text()).replace('\n', ' ').strip()
                            
                            if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                                continue

                            # Precio
                            price_el = await tarjeta.query_selector('.price, .precio, [class*="price"]')
                            if not price_el: continue
                            raw_price = await price_el.inner_text()
                            
                            if "$" not in raw_price:
                                continue
                                
                            clean_price = ''.join(c for c in raw_price if c.isdigit() or c in [',', '.'])
                            clean_price = clean_price.replace('.', '').replace(',', '.').split('.')[0]
                            
                            if not clean_price: continue
                            costo = float(clean_price)
                            if costo <= 100: continue
                            
                            precio_venta = round(costo * MARGEN_GANANCIA)

                            # Imagen
                            img_el = await tarjeta.query_selector('img')
                            img_url = ""
                            if img_el:
                                img_url = await img_el.get_attribute('src') or await img_el.get_attribute('data-src') or ""
                                if img_url.startswith('/'):
                                    img_url = urljoin(URL_BASE, img_url)
                                elif not img_url.startswith('http') or 'placeholder' in img_url:
                                    img_url = ""

                            catalogo_final[titulo.lower()] = {
                                "titulo": titulo,
                                "categoria": categoria,
                                "precio_venta": precio_venta,
                                "imagen": img_url,
                                "stock": True
                            }
                            vistos.add(titulo.lower())
                            productos_nuevos += 1
                            
                        except Exception:
                            continue
                            
                    if productos_nuevos == 0:
                        break # Fin de la paginación para esta categoría
                        
                    pagina_actual += 1
                    
                except Exception as e:
                    print(f"Error procesando {url_paginada}: {e}")
                    break 

        await browser.close()

    lista_final = list(catalogo_final.values())
    print(f"Proceso finalizado. Total de productos extraídos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
