import json
import csv

# Archivo de entrada y salida
INPUT_FILE = "productos.json"
OUTPUT_FILE = "productos_sitiosimple.csv"

def main():
    # Abrir el JSON generado por el scraper
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Abrir el CSV de salida
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Encabezados según plantilla de SitioSimple
        writer.writerow([
            "Id","Nombre Producto","Descripcion","Categoría","Mostrar en tienda","Tipo","Sku","Cantidad",
            "Precio","Producto con descuento","Precio con descuento","Imágenes producto","Imagen variante",
            "Nombre Atributo1","Valor Atributo1","Nombre Atributo2","Valor Atributo2","Nombre Atributo3","Valor Atributo3",
            "Peso","Largo","Ancho","Alto"
        ])

        id_counter = 1
        # Recorrer categorías y productos
        for categoria, productos in data.items():
            for p in productos:
                # Normalizar datos
                nombre = p.get("titulo", "")
                descripcion = p.get("descripcion", "")
                precio = p.get("precio_final", "")
                imagen = p.get("imagen", "")
                if imagen.startswith("http://"):
                    imagen = imagen.replace("http://", "https://")

                # Escribir fila en CSV
                writer.writerow([
                    id_counter,                 # Id
                    nombre,                     # Nombre Producto
                    descripcion,                # Descripcion
                    categoria,                  # Categoría
                    "sí",                       # Mostrar en tienda
                    "simple",                   # Tipo
                    f"SKU{id_counter}",         # Sku
                    10,                         # Cantidad (ejemplo fijo)
                    precio,                     # Precio
                    "no",                       # Producto con descuento
                    "",                         # Precio con descuento
                    imagen,                     # Imágenes producto
                    "",                         # Imagen variante
                    "", "",                     # Atributo1
                    "", "",                     # Atributo2
                    "", "",                     # Atributo3
                    "", "", "", ""              # Peso, Largo, Ancho, Alto
                ])
                id_counter += 1

if __name__ == "__main__":
    main()
