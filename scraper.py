import json
import asyncio
import re

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

# Banco de imágenes reales y profesionales de hardware por categoría exacta
def obtener_imagen_real(categoria, titulo):
    cat = categoria.lower()
    t = titulo.lower()
    
    if "procesador" in cat or "cpu" in cat:
        return "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=800&auto=format&fit=crop&q=80"
    elif "placa" in cat or "video" in cat or "gpu" in t:
        return "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=800&auto=format&fit=crop&q=80"
    elif "memoria" in cat or "ram" in cat:
        return "https://images.unsplash.com/photo-1562976540-1e02c414c14d?w=800&auto=format&fit=crop&q=80"
    elif "ssd" in cat or "disco" in cat or "almacenamiento" in cat:
        return "https://images.unsplash.com/photo-1531492383244-6720448108a9?w=800&auto=format&fit=crop&q=80"
    elif "motherboard" in cat or "mother" in cat:
        return "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&auto=format&fit=crop&q=80"
    elif "fuente" in cat:
        return "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?w=800&auto=format&fit=crop&q=80"
    elif "gabinete" in cat:
        return "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80"
    elif "cooler" in cat or "refrigeracion" in cat:
        return "https://images.unsplash.com/photo-1610438235354-a6aeef1983e5?w=800&auto=format&fit=crop&q=80"
    elif "monitor" in cat:
        return "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&auto=format&fit=crop&q=80"
    elif "notebook" in cat or "pc" in cat:
        return "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80"
    elif "teclado" in cat or "mouse" in cat or "perifericos" in cat:
        return "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80"
    elif "auricular" in cat or "audio" in cat:
        return "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80"
    elif "silla" in cat:
        return "https://images.unsplash.com/photo-1598550476439-6847785fcea6?w=800&auto=format&fit=crop&q=80"
    else:
        return "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=800&auto=format&fit=crop&q=80"

async def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    from playwright.async_api import async_playwright
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
                    
                    # Scroll vertical completo para asegurar que carguen todos los elementos de la página
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
                    await page.wait_for_timeout(2000)
                    
                    # Extraer todos los bloques de texto de la página que contengan precios en pesos
                    elementos_texto = await page.evaluate('''() => {
                        const items = Array.from(document.querySelectorAll('div, article, li'));
                        return items
                            .map(el => el.innerText || '')
                            .filter(text => text.includes('$') && text.length > 15 && text.length < 800);
                    }''')
                    
                    if not elementos_texto or len(elementos_texto) == 0:
                        print(f"✅ Fin de resultados para la categoría {categoria}.")
                        break
                        
                    productos_nuevos = 0
                    
                    for texto_bloque in elementos_texto:
                        lineas = [l.strip() for l in texto_bloque.split('\n') if l.strip()]
                        if not lineas:
                            continue
                            
                        # Buscar línea con precio válido
                        precio_encontrado = None
                        titulo_candidato = None
                        
                        for i, linea in enumerate(lineas):
                            precios = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', linea)
                            if precios:
                                raw_price = precios[0]
                                clean_price = raw_price.replace('.', '').replace(',', '.').split('.')[0]
                                if clean_price.isdigit():
                                    val_num = float(clean_price)
                                    if val_num > 1000:
                                        precio_encontrado = val_num
                                        # El título suele estar en las líneas anteriores al precio
                                        if i > 0:
                                            titulo_candidato = lineas[i - 1]
                                        break
                                        
                        if not precio_encontrado or not titulo_candidato:
                            continue
                            
                        titulo = titulo_candidato.replace('\n', ' ').strip()
                        if len(titulo) < 5 or "comprar" in titulo.lower() or "cuotas" in titulo.lower() or "envío" in titulo.lower():
                            # Intentar buscar otra línea como título
                            for l in lineas:
                                if len(l) > 8 and '$' not in l and not any(w in l.lower() for w in ['cuotas', 'comprar', 'envío', 'stock', 'iva']):
                                    titulo = l
                                    break
                                    
                        if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                            continue
                            
                        precio_venta = round(precio_encontrado * MARGEN_GANANCIA)
                        imagen_url = obtener_imagen_real(categoria, titulo)
                        
                        catalogo_final[titulo.lower()] = {
                            "titulo": titulo,
                            "categoria": categoria,
                            "precio_venta": precio_venta,
                            "imagen": imagen_url,
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
    print(f"\n🚀 Proceso finalizado con éxito. Total productos en catálogo: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
