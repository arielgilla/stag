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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        categorias = {
            "Procesadores": "/componentes-de-pc/microprocesadores",
            "Placas de Video": "/componentes-de-pc/placas-de-video",
            "Memorias RAM": "/componentes-de-pc/memorias-ram",
            "Almacenamiento SSD": "/componentes-de-pc/discos-solidos-ssd",
            "Discos Rigidos": "/componentes-de-pc/discos-rigidos",
            "Motherboards": "/componentes-de-pc/motherboards",
            "Fuentes": "/componentes-de-pc/fuentes",
            "Gabinetes": "/componentes-de-pc/gabinetes",
            "Coolers y Refrigeracion": "/componentes-de-pc/coolers-y-refrigeracion",
            "Monitores": "/monitores",
            "Notebooks": "/computadoras/notebooks",
            "PCs Armadas": "/computadoras/pc-armadas",
            "Teclados": "/perifericos/teclados",
            "Mouses": "/perifericos/mouses",
            "Auriculares": "/perifericos/auriculares",
            "Mousepads": "/perifericos/mousepads",
            "Sillas Gamer": "/gaming/sillas-gamer",
            "Consolas y Videojuegos": "/gaming/consolas-y-videojuegos",
            "Audio y Parlantes": "/audio-y-video/parlantes",
            "Almacenamiento Externo": "/almacenamiento/pendrives-y-tarjetas-de-memoria",
            "Conectividad y Redes": "/conectividad/routers-y-repetidores"
        }

        for categoria, path in categorias.items():
            url_categoria = f"{URL_BASE}{path}"
            pagina_actual = 1
            
            while True:
                url_paginada = f"{url_categoria}?page={pagina_actual}"
                print(f"Explorando: {categoria.upper()} - Página {pagina_actual}")
                
                try:
                    await page.goto(url_paginada, timeout=40000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000) 
                    
                    # Scroll vertical fluido para forzar la carga de imágenes en el DOM vivo
                    await page.evaluate("""async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            let distance = 300;
                            let timer = setInterval(() => {
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= document.body.scrollHeight) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        });
                    }""")
                    await page.wait_for_timeout(3000)
                    
                    # Extracción directa mediante selectores de Playwright
                    tarjetas = await page.query_selector_all('div[class*="product"], article[class*="product"], div[class*="item"]')
                    
                    if not tarjetas:
                        print(f"✅ Fin de resultados para la categoría {categoria}.")
                        break
                        
                    productos_nuevos = 0
                    
                    for tarjeta in tarjetas:
                        try:
                            texto_completo = await tarjeta.inner_text()
                            if '$' not in texto_completo:
                                continue
                                
                            # Título
                            title_el = await tarjeta.query_selector('h2, h3, h4, h5, a')
                            if not title_el:
                                continue
                            titulo = (await title_el.inner_text()).replace('\n', ' ').strip()
                            
                            if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                                continue
                                
                            # Precio
                            precios_encontrados = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', texto_completo)
                            if not precios_encontrados:
                                continue
                                
                            raw_price = precios_encontrados[0]
                            clean_price = raw_price.replace('.', '').replace(',', '.').split('.')[0]
                            
                            if not clean_price.isdigit():
                                continue
                                
                            costo = float(clean_price)
                            if costo <= 1000:
                                continue 
                            
                            precio_venta = round(costo * MARGEN_GANANCIA)
                            
                            # Imagen (Evaluación directa sobre el DOM en vivo)
                            img_url = ""
                            img_el = await tarjeta.query_selector('img')
                            if img_el:
                                for attr in ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-url']:
                                    val = await img_el.get_attribute(attr)
                                    if val and val.strip() and 'placeholder' not in val.lower() and 'logo' not in val.lower() and 'svg' not in val.lower():
                                        img_url = val.strip()
                                        break
                                
                                if not img_url:
                                    srcset = await img_el.get_attribute('srcset')
                                    if srcset:
                                        parts = srcset.split(',')
                                        if parts:
                                            img_url = parts[0].strip().split(' ')[0]

                            if img_url:
                                if img_url.startswith('//'):
                                    img_url = "https:" + img_url
                                elif img_url.startswith('/'):
                                    img_url = urljoin(URL_BASE, img_url)
                                elif not img_url.startswith('http'):
                                    img_url = ""
                            
                            if 'placeholder' in img_url.lower() or 'logo' in img_url.lower() or 'svg' in img_url.lower():
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
                        print(f"✅ Fin de resultados para la categoría {categoria}.")
                        break
                        
                    pagina_actual += 1
                    
                except Exception as e:
                    print(f"Error procesando {url_paginada}: {e}")
                    break

        await browser.close()

    lista_final = list(catalogo_final.values())
    con_imagen = len([p for p in lista_final if p['imagen']])
    print(f"\n🚀 Proceso finalizado. Total productos: {len(lista_final)} | Con imagen: {con_imagen}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
