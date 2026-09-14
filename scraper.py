import json
import asyncio
from playwright.async_api import async_playwright

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

async def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="es-AR"
        )
        
        page = await context.new_page()
        
        # Ocultar huellas de automatización
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

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
            "Teclados": "/perifericos/teclados",
            "Mouses": "/perifericos/mouses",
            "Auriculares": "/perifericos/auriculares",
            "Sillas Gamer": "/gaming/sillas-gamer"
        }

        for categoria, path in categorias.items():
            url_categoria = f"{URL_BASE}{path}"
            pagina_actual = 1
            
            while pagina_actual <= 5: # Límite por categoría para asegurar velocidad
                url_paginada = f"{url_categoria}?page={pagina_actual}"
                print(f"Explorando: {categoria.upper()} - Página {pagina_actual}")
                
                try:
                    productos_en_pagina = []
                    
                    # Interceptar las respuestas de red para capturar el JSON del catálogo directamente
                    async def handle_response(response):
                        if "api" in response.url or "search" in response.url or "product" in response.url:
                            try:
                                json_data = await response.json()
                                if isinstance(json_data, list):
                                    productos_en_pagina.extend(json_data)
                                elif isinstance(json_data, dict) and "products" in json_data:
                                    productos_en_pagina.extend(json_data["products"])
                            except:
                                pass

                    page.on("response", handle_response)
                    
                    await page.goto(url_paginada, timeout=45000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                    
                    # Desvincular el evento para la siguiente iteración
                    page.remove_listener("response", handle_response)
                    
                    # Extraer también directamente del DOM visual por si el JSON no se capturó completo
                    elementos_tarjetas = await page.query_selector_all('div[class*="item"], div[class*="product"], article')
                    
                    productos_nuevos = 0
                    
                    # Procesar datos visuales del DOM como respaldo infalible
                    for tarjeta in elementos_tarjetas:
                        try:
                            texto = await tarjeta.inner_text()
                            if not texto or '$' not in texto:
                                continue
                            
                            lineas = [l.strip() for l in texto.split('\n') if l.strip()]
                            titulo = ""
                            precio_val = None
                            
                            for i, l in enumerate(lineas):
                                if '$' in l:
                                    import re
                                    precios = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*)', l)
                                    if precios:
                                        clean = precios[0].replace('.', '').replace(',', '')
                                        if clean.isdigit():
                                            val = float(clean)
                                            if val > 1000:
                                                precio_val = val
                                                if i > 0:
                                                    titulo = lineas[i - 1]
                                                break
                            
                            if not titulo and len(lineas) > 0:
                                titulo = lineas[0]
                                
                            if not titulo or not precio_val or len(titulo) < 5:
                                continue
                                
                            if titulo.lower() in vistos:
                                continue
                                
                            # Buscar imagen real dentro de la tarjeta
                            img_el = await tarjeta.query_selector('img')
                            img_url = ""
                            if img_el:
                                for attr in ['src', 'data-src', 'data-lazy-src']:
                                    val = await img_el.get_attribute(attr)
                                    if val and val.startswith('http'):
                                        img_url = val
                                        break
                                        
                            precio_venta = round(precio_val * MARGEN_GANANCIA)
                            
                            catalogo_final[titulo.lower()] = {
                                "titulo": titulo,
                                "categoria": categoria,
                                "precio_venta": precio_venta,
                                "imagen": img_url,
                                "stock": True
                            }
                            vistos.add(titulo.lower())
                            productos_nuevos += 1
                        except:
                            continue
                            
                    if productos_nuevos == 0 and pagina_actual > 1:
                        break
                        
                    pagina_actual += 1
                    
                except Exception as e:
                    print(f"Error en {url_paginada}: {e}")
                    break

        await browser.close()

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Sincronización finalizada. Total de productos reales obtenidos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
