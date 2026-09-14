import json
import asyncio
import re
import subprocess
from urllib.parse import urljoin
from playwright.async_api import async_playwright

try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.run(["pip", "install", "beautifulsoup4"], check=True)
    from bs4 import BeautifulSoup

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

async def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Usamos un User-Agent realista para evitar bloqueos
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        categorias = {
            "Procesadores": "/componentes-de-pc/microprocesadores",
            "Placas de Video": "/componentes-de-pc/placas-de-video",
            "Memorias RAM": "/componentes-de-pc/memorias-ram",
            "Almacenamiento": "/componentes-de-pc/discos-solidos-ssd",
            "Motherboards": "/componentes-de-pc/motherboards",
            "Fuentes": "/componentes-de-pc/fuentes",
            "Monitores": "/monitores",
            "Perifericos": "/perifericos",
            "Notebooks": "/computadoras/notebooks"
        }

        for categoria, path in categorias.items():
            url_categoria = f"{URL_BASE}{path}"
            pagina_actual = 1
            
            while True:
                url_paginada = f"{url_categoria}?page={pagina_actual}"
                print(f"Explorando: {categoria.upper()} - Página {pagina_actual}")
                
                try:
                    await page.goto(url_paginada, timeout=40000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000) 
                    
                    titulo_pagina = await page.title()
                    if "Just a moment" in titulo_pagina or "Cloudflare" in titulo_pagina:
                        print("⚠️ Cloudflare está bloqueando el acceso. Intentando continuar...")
                    
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    productos_nuevos = 0
                    
                    # Buscamos elementos que tengan clases relacionadas a productos
                    # Esto evita escanear divs irrelevantes
                    tarjetas = soup.find_all(lambda tag: tag.name in ['div', 'article'] and tag.has_attr('class') and any('product' in c.lower() or 'item' in c.lower() for c in tag['class']))
                    
                    for tarjeta in tarjetas:
                        texto_completo = tarjeta.get_text(separator=' ', strip=True)
                        
                        if '$' not in texto_completo:
                            continue
                            
                        # Extraer Título (buscamos headers o enlaces dentro de la tarjeta)
                        title_tag = tarjeta.find(['h2', 'h3', 'h4', 'h5'])
                        if not title_tag:
                            # Si no hay H2/H3, buscamos el enlace con el texto más largo
                            enlaces = tarjeta.find_all('a')
                            if enlaces:
                                title_tag = max(enlaces, key=lambda a: len(a.get_text(strip=True)))
                                
                        if not title_tag: continue
                        titulo = title_tag.get_text(strip=True).replace('\n', ' ')
                        
                        if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                            continue
                            
                        # Extraer Precio
                        precios_encontrados = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', texto_completo)
                        if not precios_encontrados:
                            continue
                            
                        raw_price = precios_encontrados[0]
                        clean_price = raw_price.replace('.', '').replace(',', '.').split('.')[0]
                        
                        if not clean_price.isdigit(): continue
                        
                        costo = float(clean_price)
                        if costo <= 1000: continue # Descartamos accesorios muy baratos o errores
                        
                        precio_venta = round(costo * MARGEN_GANANCIA)
                        
                        # Extraer Imagen
                        img_tag = tarjeta.find('img')
                        img_url = ""
                        if img_tag:
                            img_url = img_tag.get('src') or img_tag.get('data-src') or ""
                            if img_url.startswith('/'):
                                img_url = urljoin(URL_BASE, img_url)
                            elif not img_url.startswith('http') or 'placeholder' in img_url.lower() or 'logo' in img_url.lower():
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
                        
                    if productos_nuevos == 0:
                        print(f"✅ Fin de resultados para la categoría {categoria}.")
                        break
                        
                    pagina_actual += 1
                    
                except Exception as e:
                    print(f"Error procesando {url_paginada}: {e}")
                    break

        await browser.close()

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Proceso finalizado. Total de productos extraídos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
