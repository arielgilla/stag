import json
from openpyxl import Workbook

INPUT_FILE = "productos.json"
OUTPUT_FILE = "productos_sitiosimple.xlsx"

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    # Encabezados según plantilla SitioSimple
    headers = [
        "Id","Nombre Producto","Descripcion","Categoría","Mostrar en tienda","Tipo","Sku","Cantidad",
        "Precio","Producto con descuento","Precio con descuento","Imágenes producto","Imagen variante",
        "Nombre Atributo1","Valor Atributo1","Nombre Atributo2","Valor Atributo2","Nombre Atributo3","Valor Atributo3",
        "Peso","Largo","Ancho","Alto"
    ]
    ws.append(headers)

    id_counter = 1
    for categoria, productos in data.items():
        for p in productos:
            nombre = p.get("titulo", "")
            descripcion = p.get("descripcion", "")
            precio = p.get("precio_final", "")
            imagen = p.get("imagen") or ""

            if isinstance(imagen, str) and imagen.startswith("http://"):
                imagen = imagen.replace("http://", "https://")

            row = [
                id_counter,
                nombre,
                descripcion,
                categoria,
                "sí",
                "simple",
                f"SKU{id_counter}",
                10,
                precio,
                "no",
                "",
                imagen,
                "",
                "","",
                "","",
                "","",
                "","","",""
            ]
            ws.append(row)
            id_counter += 1

    wb.save(OUTPUT_FILE)

if __name__ == "__main__":
    main()
