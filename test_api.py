import requests

URLS_PRUEBA = [
    "https://www.venex.com.ar/rest/V1/products?searchCriteria[currentPage]=1",
    "https://www.venex.com.ar/rest/default/V1/products?searchCriteria[currentPage]=1",
    "https://www.venex.com.ar/catalogsearch/result/?q=notebook"
]

for url in URLS_PRUEBA:
    print(f"Probando {url}")
    try:
        r = requests.get(url, timeout=10)
        print("Status:", r.status_code)
        print("Contenido:", r.text[:500])  # mostrar solo los primeros 500 caracteres
    except Exception as e:
        print("Error:", e)
