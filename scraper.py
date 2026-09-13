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

        url = "https://www.venex.com.ar/procesadores"
        
        try:
            print(f"Conectando a {url}...")
            await page.goto(url, timeout=40000, wait_until="networkidle")
            
            # Diagnóstico: Imprimir el título de la página y guardar un pantallazo o texto si es necesario
            page_title = await page.title()
            print(f"Título de la página obtenida: {page_title}")

            # Extraer todos los bloques contenedores posibles para analizar qué estructura tienen
            productos_encontrados = await page.evaluate('''() => {
                // Buscamos cualquier elemento que parezca una tarjeta de producto o contenedor de grilla
                const items = document.querySelectorAll('div');
                const results = [];
                
                items.forEach(item => {
                    // Buscar elementos internos que suelan ser títulos de productos o precios
                    const titleEl = item.querySelector('h2, h3, h4, a');
                    const priceEl = item.querySelector('.price, .precio, span');
                    
                    if (titleEl && priceEl && titleEl.innerText.length > 5 && priceEl.innerText.includes('$')) {
                        results.push({
                            title: titleEl.innerText.trim(),
                            price: priceEl.innerText.trim(),
                            html_snippet: item.className
                        });
                    }
                });
                return results.slice(0, 15); // Devolver una muestra para depuración
            ''')

            print(f"Muestra detectada por el depurador: {json.dumps(productos_encontrados, indent=2)}")

            # Recorrer de forma amplia buscando cualquier estructura con precio y título
            elementos_genericos = await page.evaluate('''() => {
                const elements = Array.from(document.querySelectorAll('*'));
                const list = [];
                elements.forEach(el => {
                    if (el.children.length === 0 && el.innerText && (el.innerText.includes('$') || el.innerText.includes('Precio'))) {
                        list.push({tag: el.tagName, class: el.className, text: el.innerText.trim()});
                    }
                });
                return list.slice(0, 30);
            ''')
            print(f"Elementos de texto analizados: {len(elementos_genericos)}")

        except Exception as e:
            print(f"Error durante la ejecución del diagnóstico: {e}")

        await browser.close()

    # Guardar un archivo mínimo para que no rompa la web mientras depuramos
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
