import json
import asyncio
from playwright.async_api import async_playwright

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

CATEGORIAS = {
    "Procesadores": "procesador",
    "Placas de Video": "placa de video",
    "Memorias RAM": "memoria ram",
    "Almacenamiento SSD": "disco ssd",
    "Discos Rigidos": "disco rigido",
    "Motherboards": "motherboard",
    "Fuentes": "fuente",
    "Gabinetes": "gabinete",
    "Coolers y Refrigeracion": "cooler",
    "Monitores": "monitor",
    "Notebooks": "notebook",
    "Teclados": "teclado",
    "Mouses": "mouse",
    "Auriculares": "auricular",
    "Sillas Gamer": "silla gamer"
}

async def extraer_venex():
    catalogo_final = {}
    vistos = set()

    async with async_playwright() as p:
        print("🌐 Iniciando navegador para superar Cloudflare...")
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        # Establecer sesión real y validar Cloudflare
        await page.goto(URL_BASE, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        for categoria, termino in CATEGORIAS.items():
            from_val = 0
            print(f"\n📦 Obteniendo datos oficiales: {categoria.upper()}")

            while True:
                api_url = f"/api/catalog_system/pub/products/search?ft={termino}&_from={from_val}&_to={from_val + 49}"
                
                # Inyección de petición API dentro de la sesión activa del navegador
                data = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const res = await fetch('{api_url}');
                            if (!res.ok) return null;
                            return await res.json();
                        }} catch (e) {{
                            return null;
                        }}
                    }}
                """)

                if not data or not isinstance(data, list) or len(data) == 0:
                    break

                nuevos = 0
                for item in data:
                    titulo = item.get("productName", "").strip()
                    if not titulo or titulo.lower() in vistos:
                        continue

                    items_sku = item.get("items", [])
                    if not items_sku:
                        continue

                    # Extraer imagen original de alta resolución
                    images = items_sku[0].get("images", [])
                    img_url = images[0].get("imageUrl", "") if images else ""

                    # Extraer oferta comercial
                    sellers = items_sku[0].get("sellers", [])
                    if not sellers:
                        continue

                    offer = sellers[0].get("commertialOffer", {})
                    precio_lista = offer.get("Price", 0)
                    disponible = offer.get("IsAvailable", False)

                    if precio_lista <= 1000 or not disponible:
                        continue

                    precio_venta = round(precio_lista * MARGEN_GANANCIA)

                    catalogo_final[titulo.lower()] = {
                        "titulo": titulo,
                        "categoria": categoria,
                        "precio_venta": precio_venta,
                        "imagen": img_url,
                        "stock": True
                    }
                    vistos.add(titulo.lower())
                    nuevos += 1

                print(f"  └─ Procesados: {from_val + len(data)} items (+{nuevos} agregados)")

                if len(data) < 50:
                    break

                from_val += 50
                await page.wait_for_timeout(300)

        await browser.close()

    lista_final = list(catalogo_final.values())
    con_imagen = len([p for p in lista_final if p["imagen"]])
    print(f"\n🚀 Éxito total. Total productos obtenidos: {len(lista_final)} | Con imagen: {con_imagen}")

    with open("productos.json", "w", encoding="utf-8") as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    asyncio.run(extraer_venex())
