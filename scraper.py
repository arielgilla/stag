import json
import requests
from bs4 import BeautifulSoup
import re

MARGEN_GANANCIA = 1.15
URL_BASE = "https://www.venex.com.ar"

def extraer_venex():
    catalogo_final = {}
    vistos = set()
    
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
        while pagina_actual <= 10:
            url_paginada = f"{URL_BASE}{path}?page={pagina_actual}"
            print(f"Extrayendo: {categoria.upper()} - Página {pagina_actual}")
            
            try:
                response = requests.get(url_paginada, headers=headers, timeout=30)
                if response.status_code != 200:
                    break
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Búsqueda general de tarjetas de productos en el HTML
                tarjetas = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'(product|item|summary|card|box)', re.I))
                
                if not tarjetas:
                    break
                    
                productos_nuevos = 0
                
                for tarjeta in tarjetas:
                    texto = tarjeta.get_text(separator='\n', strip=True)
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
                    if len(titulo) < 5 or any(w in titulo.lower() for w in ['cuotas', 'comprar', 'envío', 'stock', 'iva', '$', 'off']):
                        for l in lineas:
                            if len(l) > 6 and '$' not in l and not any(w in l.lower() for w in ['cuotas', 'comprar', 'envío', 'stock', 'iva', 'off']):
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
                    
                print(f"-> Encontrados {productos_nuevos} productos nuevos.")
                
                if productos_nuevos == 0 and pagina_actual > 1:
                    break
                    
                pagina_actual += 1
                
            except Exception as e:
                print(f"Error en {url_paginada}: {e}")
                break

    lista_final = list(catalogo_final.values())
    print(f"\n🚀 Sincronización completa. Total de productos obtenidos: {len(lista_final)}")

    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(lista_final, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extraer_venex()
