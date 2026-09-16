import json
import csv

INPUT_FILE = "productos.json"
OUTPUT_FILE = "productos_sitiosimple.csv"

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Id","Nombre Producto","Descripcion","Categoría","Mostrar en tienda","Tipo","Sku","Cantidad",
            "Precio","Producto con descuento","Precio con descuento","Imágenes producto","Imagen variante",
            "Nombre Atributo1","Valor Atributo1","Nombre Atributo2","Valor Atributo2","Nombre Atributo3","Valor Atributo3",
            "Peso","Largo","Ancho","Alto"
        ])

        id_counter = 1
        for categoria, productos in data.items():
            for p in productos:
                nombre = p.get("titulo", "")
                descripcion = p.get("descripcion", "")
                precio = p.get("precio_final", "")

                # Manejo seguro de imagen
                imagen = p.get("imagen")
                if not imagen:
                    imagen = ""  # si no hay imagen, dejar vacío
                elif isinstance(imagen, str) and imagen.startswith("http://"):
                    imagen = imagen.replace("http://", "https://")

                writer.writerow([
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
                ])
                id_counter += 1

if __name__ == "__main__":
    main()
