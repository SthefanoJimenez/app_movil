import os
import io
import json
import pymysql
import face_recognition

# Configuración base de datos (ajusta si usas otro host/usuario/pass/db)
db = pymysql.connect(
    host="localhost",
    user="root",
    password="12345678",
    database="reconocimiento_facial_1"
)

cursor = db.cursor()

# Seleccionar imágenes con embedding_fr NULL
cursor.execute("SELECT id, imagen_path FROM imagenes WHERE embedding_fr IS NULL")
registros = cursor.fetchall()
print(f"Encontradas {len(registros)} imágenes sin embedding_fr")

for fila in registros:
    id_img, imagen_path = fila
    ruta_img = os.path.join("uploads", imagen_path)  # ajusta la ruta base si tu carpeta uploads está en otro lado
    print(f"Procesando id={id_img}, archivo={ruta_img}")

    if not os.path.exists(ruta_img):
        print(f"    [ERROR] Archivo no encontrado: {ruta_img}")
        continue

    with open(ruta_img, 'rb') as f:
        imagen_bytes = f.read()

    try:
        img_fr = face_recognition.load_image_file(io.BytesIO(imagen_bytes))
        encodings = face_recognition.face_encodings(img_fr)
        if len(encodings) > 0:
            embedding_fr = json.dumps(encodings[0].tolist())
            # Actualizar en la base de datos
            cursor.execute(
                "UPDATE imagenes SET embedding_fr=%s WHERE id=%s",
                (embedding_fr, id_img)
            )
            db.commit()
            print("    [OK] embedding_fr actualizado")
        else:
            print("    [WARN] No se detectó rostro en la imagen")
    except Exception as e:
        print("    [ERROR] No se pudo calcular embedding_fr:", e)

cursor.close()
db.close()
print("¡Proceso finalizado!")
