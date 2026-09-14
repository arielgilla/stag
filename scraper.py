import json
import asyncio
import re
import subprocess
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# Instalación automática de BeautifulSoup por si no está en el entorno
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
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        # Rutas específicas donde Venex REALMENTE tiene sus grillas de productos
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
                # Armamos la URL de paginación
                url_paginada = f"{url_categoria}?page={pagina_actual}"
                print(f"Explorando: {categoria.upper()} - Página {pagina_actual}")
                
                try:
                    await page.goto(url_paginada, timeout=40000, wait_until="domcontentloaded")
                    # Espera ESTRICTA de 4 segundos para que carguen los precios por JavaScript
                    await page.wait_for_timeout(4000) 
                    
                    # Extraemos todo el HTML de la página y lo pasamos a BeautifulSoup (súper rápido y no da errores de sintaxis)
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    productos_nuevos = 0
                    
                    # Buscamos cualquier bloque (div, article) que tenga estructura de producto
                    for tarjeta in soup.find_all(['div', 'article']):
                        texto = tarjeta.get_text(separator=' ', strip=True)
                        
                        # Filtro inteligente: Si el bloque tiene mucho texto (es la página entera) o muy poco, lo descartamos
                        if len(texto) > 400 or len(texto) < 15:
                            continue
                        
                        # Si no hay signo $ en el bloque de texto, no es un producto
                        if '$' not in texto:
                            continue
                            
                        # Buscar título (priorizamos etiquetas H o enlaces)
                        title_tag = tarjeta.find(['h2', 'h3', 'h4', 'h5', 'a'])
                        if not title_tag: continue
                        titulo = title_tag.get_text(strip=True).replace('\n', ' ')
                        
                        if not titulo or len(titulo) < 5 or titulo.lower() in vistos:
                            continue
                            
                        # Buscar precio con una expresión regular sobre el texto
                        # Extrae formatos como $ 150.000 o $150.000
                        precios_encontrados = re.findall(r'\$\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', texto)
                        if not precios_encontrados:
                            continue
                            
                        raw_price = precios_encontrados[0]
                        # Limpieza matemática del precio (quitar puntos, comas decimales)
                        clean_price = raw_price.replace('.', '').replace(',', '.').split('.')[0]
                        
                        if not clean_price.isdigit(): continue
                        
                        costo = float(clean_price)
                        if costo <= 100: continue # Falso positivo (ej: precio de envío)
                        
                        precio_venta = round(costo * MARGEN_GANANCIA)
                        
                        # Buscar imagen oficial
                        img_tag = tarjeta.find('img')
                        img_url = ""
                        if img_tag:
                            img_url = img_tag.get('src') or img_tag.get('data-src') or ""
                            if img_url.startswith('/'):
                                img_url = urljoin(URL_BASE, img_url)
                            elif not img_url.startswith('http') or 'placeholder' in img_url.lower() or 'logo' in img_url.lower():
                                img_url = ""
                                
                        if not img_url: 
                            continue # Si no tiene foto real, descartamos
                        
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
                        break # Cortamos la paginación de esta categoría y pasamos a la siguiente
                        
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
