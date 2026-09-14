import json
import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

async def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Usamos un User-Agent de Mac para reducir la probabilidad de bloqueo por Cloudflare
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        # Puntos de entrada principales (cubre la totalidad del catálogo)
        categorias_base = [
            "componentes-de-pc",
            "perifericos",
            "monitores",
            "computadoras",
            "notebooks",
            "almacenamiento",
            "accesorios",
            "conectividad",
            "energia",
            "gaming"
        ]

        for categoria in categorias_base:
            url_categoria = f"{URL_BASE}/{categoria}"
            pagina_actual = 1
            
            while True:
                # Venex suele usar ?page=X o &page=X
                url_paginada = f"{url_categoria}?page={pagina_actual}"
                print(f"Explorando: {categoria.upper()} - Página {pagina_actual}")
                
                try:
                    await page.goto(url_paginada, timeout=30000, wait_until="domcontentloaded")
                    
                    # Esperamos explícitamente a que aparezca al menos un precio o pase el timeout
                    try:
                        await page.wait_for_selector('.price, .precio, [class*="price"]', timeout=5000)
                    except Exception:
                        print(f"Fin de resultados detectado en {categoria} (página {pagina_actual}).")
                        break # Si no carga ningún precio en 5 segundos, ya no hay más productos
                    
                    # Selectores súper amplios para capturar cualquier tarjeta
                    tarjetas = await page.query_selector_all('div.product-box, div.item, article, [class*="product-item"]')
                    
                    productos_nuevos = 0
                    
                    for tarjeta in tarjetas:
                        try:
                            # Extraer Título
                            title_el = await tarjeta.query_selector('h2, h3, h4, .name, .title, a')
                            if not title_el: continue
                            titulo = (await title_el.inner_text()).replace('\n', ' ').strip()
                            
                            if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                                continue

                            # Extraer Precio
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

                            # Extraer Imagen
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
                                "categoria": categoria.replace('-', ' ').title(),
                                "precio_venta": precio_venta,
                                "imagen": img_url,
                                "stock": True
                            }
                            vistos.add(titulo.lower())
                            productos_nuevos += 1
                            
                        except Exception:
                            continue
                            
                    if productos_nuevos == 0:
                        break # Si no se extrajo nada nuevo, la página está vacía
                        
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
