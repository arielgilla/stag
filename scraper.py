import json
import urllib.request
import urllib.parse
import re

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
    # Categorías y sus rutas en Venex
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

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }

    for categoria, path in categorias.items():
        pagina_actual = 1
        while pagina_actual <= 10:  # Límite de seguridad por categoría
            url_paginada = f"{URL_BASE}{path}?page={pagina_actual}"
            print(f"Consultando: {categoria.upper()} - Página {pagina_actual}")
            
            try:
                req = urllib.request.Request(url_paginada, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                
                # Si la página no devuelve contenido útil o nos redirige/bloquea
                if not html or "cloudflare" in html.lower() or len(html) < 5000:
                    print(f"⚠️ Posible bloqueo o fin de páginas en {categoria}.")
                    break

                # Extraer bloques de productos mediante expresiones regulares seguras sobre el HTML
                # Buscamos patrones típicos de títulos y precios en el código fuente
                productos_nuevos = 0
                
                # Extraer todos los fragmentos que contengan precios en pesos argentinos
                # Buscamos precios en formato $ X.XXX o similar
                fragmentos = re.findall(r'<[a-zA-Z0-9]+[^>]*>(?:(?!<\/[a-zA-Z0-9]+>).)*?\$[0-9]{1,3}(?:\.[0-9]{3})*(?:,\d{2})?</[a-zA-Z0-9]+>', html)
                
                # Método alternativo general si el HTML está minificado: extraer texto plano de etiquetas h2, h3, a, span con precios cercanos
                # Buscamos precios numéricos acompañados de textos largos (títulos)
                titulos_precios = re.findall(r'title="([^"]+)"[^>]*>.*?\$([0-9]{1,3}(?:\.[0-9]{3})*)', html, re.DOTALL)
                
                if not titulos_precios:
                    # Búsqueda alternativa por estructura genérica de enlaces y precios en texto
                    titulos_precios = re.findall(r'class="[^"]*(?:title|name|producto)[^"]*">([^<]+)</(?:h2|h3|a|span)>.*?\$([0-9]{1,3}(?:\.[0-9]{3})*)', html, re.DOTALL)

                for titulo_raw, precio_raw in titulos_precios:
                    titulo = titulo_raw.replace('\n', ' ').strip()
                    clean_precio = precio_raw.replace('.', '').replace(',', '.')
                    
                    if not clean_precio.isdigit():
                        continue
                        
                    costo = float(clean_precio)
                    if costo <= 1000 or len(titulo) < 5:
                        continue
                        
                    if titulo.lower() in vistos:
                        continue
                        
                    precio_venta = round(costo * MARGEN_GANANCIA)
                    
                    catalogo_final[titulo.lower()] = {
                        "titulo": titulo,
                        "categoria": categoria,
                        "precio_venta": precio_venta,
                        "imagen": "", 
                        "stock": True
                    }
                    vistos.add(titulo.lower())
                    productos_nuevos += 1

                print(f"-> Encontrados {productos_nuevos} productos nuevos en esta página.")
                
                if productos_nuevos == 0 and pagina_actual > 1:
                    break
                    
                pagina_actual += 1
                
            except Exception as e:
                print(f"Error al conectar con {url_paginada}: {e}")
                break

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Proceso finalizado. Total productos obtenidos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
