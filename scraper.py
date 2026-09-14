import json
import asyncio
import re
from playwright.async_api import async_playwright

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

async def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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
            "Teclados": "/perifericos/teclados",
            "Mouses": "/perifericos/mouses",
            "Auriculares": "/perifericos/auriculares",
            "Sillas Gamer": "/gaming/sillas-gamer"
        }

        for categoria, path in categorias.items():
            url_categoria = f"{URL_BASE}{path}"
            pagina_actual = 1
            
            while pagina_actual <= 4:  # Límite por categoría optimizado para velocidad
                url_paginada = f"{url_categoria}?page={pagina_actual}"
                print(f"Extrayendo: {categoria.upper()} - Página {pagina_actual}")
                
                try:
                    await page.goto(url_paginada, timeout=60000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3500)
                    
                    # Scroll para forzar la carga de imágenes lazy-load y elementos dinámicos
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    await page.wait_for_timeout(2000)
                    
                    # Selectores amplios adaptados al diseño actual de e-commerce VTEX/Venex
                    tarjetas = await page.query_selector_all('div[class*="product"], div[class*="item"], article, div[class*="box-item"]')
                    
                    if not tarjetas:
                        break
                        
                    productos_nuevos = 0
                    
                    for tarjeta in tarjetas:
                        try:
                            texto = await tarjeta.inner_text()
                            if not texto or '$' not in texto:
                                continue
                                
                            lineas = [l.strip() for l in texto.split('\n') if l.strip()]
                            if len(lineas) < 2:
                                continue
                                
                            precio_val = None
                            titulo_candidato = None
                            
                            for i, linea in enumerate(lineas):
                                precios = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*)', linea)
                                if precios:
                                    raw = precios[0].replace('.', '').replace(',', '')
                                    if raw.isdigit():
                                        val = float(raw)
                                        if val > 1000:
                                            precio_val = val
                                            if i > 0:
                                                titulo_candidato = lineas[i - 1]
                                            break
                                            
                            if not precio_val or not titulo_candidato:
                                continue
                                
                            titulo = titulo_candidato.replace('\n', ' ').strip()
                            # Filtrar textos basura que no sean el nombre del producto
                            if len(titulo) < 5 or any(w in titulo.lower() for w in ['cuotas', 'comprar', 'envío', 'stock', 'iva', '$', 'ahorro', 'off']):
                                for l in lineas:
                                    if len(l) > 6 and '$' not in l and not any(w in l.lower() for w in ['cuotas', 'comprar', 'envío', 'stock', 'iva', 'off']):
                                        titulo = l
                                        break
                                        
                            if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                                continue
                                
                            # Extraer imagen real de la tarjeta
                            img_el = await tarjeta.query_selector('img')
                            img_url = ""
                            if img_el:
                                for attr in ['src', 'data-src', 'data-lazy', 'srcset']:
                                    val = await img_el.get_attribute(attr)
                                    if val and val.startswith('http'):
                                        # Si es un srcset, tomar la primera URL limpia
                                        img_url = val.split(',')[0].strip().split(' ')[0]
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
                            
                        except Exception:
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
