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
        # Lanzar con argumentos anti-detección para evitar bloqueos de Cloudflare en GitHub Actions
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="es-AR",
            timezone_id="America/Argentina/Cordoba",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"'
            }
        )
        
        page = await context.new_page()

        # Ocultar propiedades de automatización de JavaScript
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

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
                    response = await page.goto(url_paginada, timeout=60000, wait_until="domcontentloaded")
                    
                    if response and response.status == 403:
                        print(f"⚠️ Bloqueo detectado (403 Forbidden) en {url_paginada}. Esperando...")
                        await page.wait_for_timeout(10000)
                        continue
                        
                    await page.wait_for_timeout(4000) 
                    
                    # Scroll progresivo para simular comportamiento humano y activar elementos
                    await page.evaluate("""async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            let distance = 400;
                            let timer = setInterval(() => {
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= document.body.scrollHeight) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 150);
                        });
                    }""")
                    await page.wait_for_timeout(3000)
                    
                    # Extracción directa de todos los bloques de la página que contengan texto y precios
                    productos_encontrados_pagina = await page.evaluate('''() => {
                        const items = [];
                        // Buscamos cualquier elemento que pueda contener la tarjeta de producto
                        const elements = document.querySelectorAll('div, article, li');
                        elements.forEach(el => {
                            const text = el.innerText || '';
                            if (text.includes('$') && text.length > 15 && text.length < 1000) {
                                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                if (lines.length >= 2) {
                                    items.push(lines);
                                }
                            }
                        });
                        return items;
                    }''')
                    
                    if not productos_encontrados_pagina:
                        print(f"✅ Fin de resultados o página vacía para {categoria}.")
                        break
                        
                    productos_nuevos = 0
                    
                    for lineas in productos_encontrados_pagina:
                        precio_val = None
                        titulo_candidato = None
                        
                        for i, linea in enumerate(lineas):
                            precios = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', linea)
                            if precios:
                                raw = precios[0].replace('.', '').replace(',', '.').split('.')[0]
                                if raw.isdigit():
                                    val = float(raw)
                                    if val > 1000: # Filtrar precios inválidos o menores a $1000
                                        precio_val = val
                                        if i > 0:
                                            titulo_candidato = lineas[i - 1]
                                        break
                                        
                        if not precio_val or not titulo_candidato:
                            continue
                            
                        titulo = titulo_candidato.replace('\n', ' ').strip()
                        if len(titulo) < 5 or any(w in titulo.lower() for w in ['cuotas', 'comprar', 'envío', 'stock', 'iva', '$', 'tarjeta']):
                            for l in lineas:
                                if len(l) > 6 and '$' not in l and not any(w in l.lower() for w in ['cuotas', 'comprar', 'envío', 'stock', 'iva', 'tarjeta']):
                                    titulo = l
                                    break
                                    
                        if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                            continue
                            
                        precio_venta = round(precio_val * MARGEN_GANANCIA)
                        
                        catalogo_final[titulo.lower()] = {
                            "titulo": titulo,
                            "categoria": categoria,
                            "precio_venta": precio_venta,
                            "imagen": "", 
                            "stock": True
                        }
                        vistos.add(titulo.lower())
                        productos_nuevos += 1
                        
                    if productos_nuevos == 0:
                        print(f"✅ Fin de resultados para la categoría {categoria}.")
                        break
                        
                    pagina_actual += 1
                    
                except Exception as e:
                    print(f"Error procesando {url_paginada}: {e}")
                    break

        await browser.close()

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Extracción finalizada. Total de productos obtenidos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
