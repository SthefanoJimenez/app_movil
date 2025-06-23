import numpy as np

from utils.face_utils import (
    obtener_embeddings_lbp_lpq_hog as obtener_embeddings,
    normalizar_embedding
)

def similitud_coseno(v1, v2):
    v1 = normalizar_embedding(v1)
    v2 = normalizar_embedding(v2)
    return float(np.dot(v1, v2))

def distancia_euclidiana(v1, v2):
    v1 = normalizar_embedding(v1)
    v2 = normalizar_embedding(v2)
    return float(np.linalg.norm(np.array(v1) - np.array(v2)))

import os
import json
import json
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import db_config
import face_recognition
import io


# Crear la app Flask
app = Flask(__name__)
CORS(app)

# Configuración de la base de datos desde config.py
app.config['MYSQL_HOST'] = db_config['host']
app.config['MYSQL_USER'] = db_config['user']
app.config['MYSQL_PASSWORD'] = db_config['password']
app.config['MYSQL_DB'] = db_config['database']

# Inicializar conexión MySQL
mysql = MySQL(app)


# Ruta raíz de prueba
@app.route("/")
def index():
    return "Backend funcionando correctamente."


# Ruta: Registrar usuario (sin imagen aún)
@app.route("/registrar_usuario", methods=["POST"])
def registrar_usuario():
    try:
        # Obtener los datos del formulario
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        codigo_unico = request.form['codigo_unico']
        email = request.form['email']
        requisitoriado = request.form['requisitoriado'] == 'true'  # Convertir a booleano

        # Verificar que los valores se recibieron correctamente
        print(f"Datos recibidos: {nombre}, {apellido}, {codigo_unico}, {email}, {requisitoriado}")

        # Verificar si todos los campos están presentes
        if not nombre or not apellido or not codigo_unico or not email:
            return jsonify({"mensaje": "Todos los campos son obligatorios"}), 400
        
        cursor = mysql.connection.cursor()
        sql = """
            INSERT INTO usuarios (nombre, apellido, codigo_unico, email, requisitoriado)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (nombre, apellido, codigo_unico, email, requisitoriado))
        mysql.connection.commit()

        # Obtener ID generado
        inserted_id = cursor.lastrowid
        print(f"Usuario registrado con ID: {inserted_id}")

        cursor.close()

        # Devolver el ID generado al frontend
        return jsonify({
            "mensaje": f"Usuario registrado exitosamente con ID {inserted_id}",
            "id_usuario": inserted_id
        }), 200

    except Exception as e:
        print("Error al registrar usuario:", e)
        return jsonify({"mensaje": "Error al registrar usuario"}), 500



# Ruta: Agregar imagen + embeddings LBP + LPQ + face_recognition a un usuario
@app.route("/agregar_imagen/<int:usuario_id>", methods=["POST"])
def agregar_imagen(usuario_id):
    try:
        imagen = request.files['imagen']
        if not imagen:
            raise ValueError('No se recibió ninguna imagen.')

        filename = secure_filename(imagen.filename)
        print(f"Imagen recibida: {filename}")

        # Crear carpeta del usuario si no existe
        carpeta_usuario = os.path.join("uploads", f"user_{usuario_id}")
        os.makedirs(carpeta_usuario, exist_ok=True)

        # Guardar la imagen en la carpeta correspondiente
        ruta_guardado = os.path.join(carpeta_usuario, filename)
        imagen.save(ruta_guardado)

        with open(ruta_guardado, 'rb') as f:
            imagen_bytes = f.read()

        # Embedding tradicional (LBP+LPQ+HOG)
        embeddings = obtener_embeddings(imagen_bytes)
        if embeddings is None:
            return jsonify({"mensaje": "No se detectaron características LBP+LPQ+HOG"}), 400

        # Embedding de face_recognition
        try:
            image_fr = face_recognition.load_image_file(io.BytesIO(imagen_bytes))
            encodings_fr = face_recognition.face_encodings(image_fr)
            if len(encodings_fr) > 0:
                embedding_fr = encodings_fr[0].tolist()  # Lista serializable en JSON
            else:
                embedding_fr = None
        except Exception as e:
            print("Error obteniendo embedding face_recognition:", e)
            embedding_fr = None

        # Guardar ruta + embeddings en la base de datos
        cursor = mysql.connection.cursor()
        sql = """INSERT INTO imagenes (usuario_id, imagen_path, embeddings, embedding_fr)
                 VALUES (%s, %s, %s, %s)"""
        cursor.execute(sql, (
            usuario_id,
            ruta_guardado,
            json.dumps(embeddings),
            json.dumps(embedding_fr) if embedding_fr is not None else None
        ))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"mensaje": "Imagen agregada exitosamente"}), 200

    except Exception as e:
        print(f"Error al agregar imagen: {e}")
        return jsonify({"mensaje": "Error al agregar imagen"}), 500



# Ruta: Listar todos los usuarios registrados
@app.route("/listar_usuarios", methods=["GET"])
def listar_usuarios():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, nombre, apellido, codigo_unico, email, requisitoriado, fecha_registro FROM usuarios")
        resultados = cursor.fetchall()

        lista = []
        columnas = [col[0] for col in cursor.description]

        for fila in resultados:
            usuario = dict(zip(columnas, fila))
            usuario['requisitoriado'] = bool(usuario['requisitoriado'])
            lista.append(usuario)

        cursor.close()
        return jsonify(lista), 200

    except Exception as e:
        print("Error al listar usuarios:", e)
        return jsonify({"mensaje": "Error al obtener usuarios"}), 500
    
  #Reconocer Usuario 
@app.route("/reconocer_usuario", methods=["POST"])
def reconocer_usuario():
    try:
        # Recibir imagen
        imagen = request.files['imagen']
        filename = secure_filename(imagen.filename)
        ruta_temporal = os.path.join("uploads", filename)
        imagen.save(ruta_temporal)

        with open(ruta_temporal, 'rb') as f:
            imagen_bytes = f.read()

        # --- 1. Obtener embeddings tradicionales (tu método) ---
        emb_ext = obtener_embeddings(imagen_bytes)
        if emb_ext is None:
            # Limpieza de archivo temporal
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
            return jsonify({"mensaje": "No se detectaron características tradicionales en la imagen"}), 400

        # --- 2. Obtener embedding face_recognition ---
        try:
            image_fr = face_recognition.load_image_file(io.BytesIO(imagen_bytes))
            encodings_fr = face_recognition.face_encodings(image_fr)
            if len(encodings_fr) > 0:
                emb_ext_fr = encodings_fr[0]
            else:
                emb_ext_fr = None
        except Exception as e:
            print("Error obteniendo embedding face_recognition:", e)
            emb_ext_fr = None

        if emb_ext_fr is None:
            if os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
            return jsonify({"mensaje": "No se detectó embedding face_recognition en la imagen"}), 400

        # --- 3. Buscar en la base de datos ---
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT i.embeddings, i.embedding_fr, i.imagen_path, u.id, u.nombre, u.apellido, u.codigo_unico, u.requisitoriado
            FROM imagenes i
            JOIN usuarios u ON i.usuario_id = u.id
        """)
        resultados = cursor.fetchall()
        cursor.close()

        # Umbrales principales
        umbral_similitud_tradicional = 0.85    # similitud coseno tradicional
        umbral_similitud_fr = 0.60             # similitud coseno face_recognition
        cantidad_minima = 4  # mínimo de coincidencias dobles para aceptar

        # Umbrales estrictos para fallback
        umbral_strict_tradicional = 0.98
        umbral_strict_fr = 0.85

        candidatos = {
            'doble': {},
            'tradicional': {},
            'fr': {}
        }

        for fila in resultados:
            emb_guardado = json.loads(fila[0])
            emb_guardado_fr = json.loads(fila[1]) if fila[1] else None
            imagen_path = fila[2]
            usuario_id = fila[3]
            nombre = fila[4]
            apellido = fila[5]
            codigo = fila[6]
            requisitoriado = fila[7]

            # Validación de tamaños y existencia de embeddings
            if (
                emb_guardado is None or
                emb_guardado_fr is None or
                len(emb_guardado) != len(emb_ext) or
                len(emb_guardado_fr) != len(emb_ext_fr)
            ):
                continue

            # --- Similitud tradicional (coseno) ---
            sim_trad = float(np.dot(emb_ext, emb_guardado) / (np.linalg.norm(emb_ext) * np.linalg.norm(emb_guardado)))
            # --- Similitud face_recognition (coseno) ---
            emb_ext_fr_n = emb_ext_fr / np.linalg.norm(emb_ext_fr)
            emb_guardado_fr_n = np.array(emb_guardado_fr) / np.linalg.norm(emb_guardado_fr)
            sim_fr = float(np.dot(emb_ext_fr_n, emb_guardado_fr_n))

            # --- Lógica Fallback ---
            # Caso 1: Doble coincidencia
            if sim_trad >= umbral_similitud_tradicional and sim_fr >= umbral_similitud_fr:
                if usuario_id not in candidatos['doble']:
                    candidatos['doble'][usuario_id] = {
                        "nombre": nombre,
                        "apellido": apellido,
                        "codigo_unico": codigo,
                        "requisitoriado": bool(requisitoriado),
                        "similitudes_trad": [],
                        "similitudes_fr": [],
                        "imagenes": []
                    }
                candidatos['doble'][usuario_id]["similitudes_trad"].append(sim_trad)
                candidatos['doble'][usuario_id]["similitudes_fr"].append(sim_fr)
                candidatos['doble'][usuario_id]["imagenes"].append(imagen_path)
            # Caso 2: Solo tradicional (umbral estricto)
            elif sim_trad >= umbral_strict_tradicional:
                if usuario_id not in candidatos['tradicional']:
                    candidatos['tradicional'][usuario_id] = {
                        "nombre": nombre,
                        "apellido": apellido,
                        "codigo_unico": codigo,
                        "requisitoriado": bool(requisitoriado),
                        "similitudes_trad": [],
                        "imagenes": []
                    }
                candidatos['tradicional'][usuario_id]["similitudes_trad"].append(sim_trad)
                candidatos['tradicional'][usuario_id]["imagenes"].append(imagen_path)
            # Caso 3: Solo face_recognition (umbral estricto)
            elif sim_fr >= umbral_strict_fr:
                if usuario_id not in candidatos['fr']:
                    candidatos['fr'][usuario_id] = {
                        "nombre": nombre,
                        "apellido": apellido,
                        "codigo_unico": codigo,
                        "requisitoriado": bool(requisitoriado),
                        "similitudes_fr": [],
                        "imagenes": []
                    }
                candidatos['fr'][usuario_id]["similitudes_fr"].append(sim_fr)
                candidatos['fr'][usuario_id]["imagenes"].append(imagen_path)

        # Limpieza del archivo temporal
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)

        # --- Selección del mejor usuario según prioridad ---
        mejor_usuario = None
        max_coincidencias = 0

        # 1. Buscar coincidencia doble
        for uid, data in candidatos['doble'].items():
            if len(data["similitudes_trad"]) >= cantidad_minima:
                promedio_trad = sum(data["similitudes_trad"]) / len(data["similitudes_trad"])
                promedio_fr = sum(data["similitudes_fr"]) / len(data["similitudes_fr"])
                if len(data["similitudes_trad"]) > max_coincidencias:
                    max_coincidencias = len(data["similitudes_trad"])
                    mejor_usuario = {
                        "usuario_id": uid,
                        "nombre": data["nombre"],
                        "apellido": data["apellido"],
                        "codigo_unico": data["codigo_unico"],
                        "similitud_tradicional_promedio": round(promedio_trad, 4),
                        "similitud_face_recognition_promedio": round(promedio_fr, 4),
                        "requisitoriado": data["requisitoriado"],
                        "imagen_referencia": data["imagenes"][0],
                        "metodo": "doble"
                    }
        # 2. Fallback tradicional
        if not mejor_usuario:
            for uid, data in candidatos['tradicional'].items():
                promedio_trad = sum(data["similitudes_trad"]) / len(data["similitudes_trad"])
                if len(data["similitudes_trad"]) > max_coincidencias:
                    max_coincidencias = len(data["similitudes_trad"])
                    mejor_usuario = {
                        "usuario_id": uid,
                        "nombre": data["nombre"],
                        "apellido": data["apellido"],
                        "codigo_unico": data["codigo_unico"],
                        "similitud_tradicional_promedio": round(promedio_trad, 4),
                        "requisitoriado": data["requisitoriado"],
                        "imagen_referencia": data["imagenes"][0],
                        "metodo": "solo_tradicional"
                    }
        # 3. Fallback face_recognition
        if not mejor_usuario:
            for uid, data in candidatos['fr'].items():
                promedio_fr = sum(data["similitudes_fr"]) / len(data["similitudes_fr"])
                if len(data["similitudes_fr"]) > max_coincidencias:
                    max_coincidencias = len(data["similitudes_fr"])
                    mejor_usuario = {
                        "usuario_id": uid,
                        "nombre": data["nombre"],
                        "apellido": data["apellido"],
                        "codigo_unico": data["codigo_unico"],
                        "similitud_face_recognition_promedio": round(promedio_fr, 4),
                        "requisitoriado": data["requisitoriado"],
                        "imagen_referencia": data["imagenes"][0],
                        "metodo": "solo_face_recognition"
                    }

        if mejor_usuario:
            if mejor_usuario["requisitoriado"]:
                mejor_usuario["alerta"] = True
                mejor_usuario["mensaje_alerta"] = "¡ALERTA DE SEGURIDAD! Usuario requisitoriado detectado. Notificación enviada a la policía (simulada)."
            return jsonify(mejor_usuario), 200
        else:
            return jsonify({"mensaje": "No se encontraron coincidencias."}), 200

    except Exception as e:
        print("Error en reconocimiento:", e)
        import traceback; traceback.print_exc()
        # Limpieza del archivo temporal en caso de error
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)
        return jsonify({"mensaje": "Error al procesar imagen"}), 500

#Editar Usuario de datos
@app.route("/editar_usuario/<int:usuario_id>", methods=["PUT"])
def editar_usuario(usuario_id):
    try:
        datos = request.form
        nombre = datos.get('nombre')
        apellido = datos.get('apellido')
        codigo_unico = datos.get('codigo_unico')
        email = datos.get('email')
        requisitoriado = datos.get('requisitoriado', 'false').lower() == 'true'

        # Actualizar datos personales
        cursor = mysql.connection.cursor()
        sql = """UPDATE usuarios SET nombre=%s, apellido=%s, codigo_unico=%s, email=%s, requisitoriado=%s
                 WHERE id=%s"""
        cursor.execute(sql, (nombre, apellido, codigo_unico, email, requisitoriado, usuario_id))

        # Si se envía imagen, agrega una nueva (¡no borra las anteriores!)
        if 'imagen' in request.files and request.files['imagen'].filename != '':
            imagen = request.files['imagen']
            filename = secure_filename(imagen.filename)
            carpeta_usuario = os.path.join("uploads", f"user_{usuario_id}")
            os.makedirs(carpeta_usuario, exist_ok=True)
            ruta_guardado = os.path.join(carpeta_usuario, filename)
            imagen.save(ruta_guardado)
            with open(ruta_guardado, 'rb') as f:
                imagen_bytes = f.read()

            embeddings = obtener_embeddings(imagen_bytes)
            if embeddings is None:
                cursor.close()
                return jsonify({"mensaje": "No se detectaron características LBP"}), 400

            ruta_relativa = os.path.join(f"user_{usuario_id}", filename)

            # ¡Solo INSERTA la nueva imagen y sus embeddings!
            sql_img = """INSERT INTO imagenes (usuario_id, imagen_path, embeddings)
                         VALUES (%s, %s, %s)"""
            cursor.execute(sql_img, (usuario_id, ruta_relativa, json.dumps(embeddings)))

        mysql.connection.commit()
        cursor.close()
        return jsonify({"mensaje": "Usuario actualizado (datos y/o imagen agregada)"}), 200
    except Exception as e:
        print("Error editando usuario:", e)
        import traceback; traceback.print_exc()
        return jsonify({"mensaje": "Error actualizando usuario"}), 500


#Eliminar imagen específica de usuario
@app.route("/imagenes_usuario/<int:usuario_id>", methods=["GET", "DELETE"])
def imagenes_usuario(usuario_id):
    try:
        cursor = mysql.connection.cursor()
        
        # ----------- GET: Listar todas las imágenes del usuario -----------
        if request.method == "GET":
            cursor.execute("""
                SELECT id, imagen_path, fecha_registro
                FROM imagenes
                WHERE usuario_id = %s
                ORDER BY fecha_registro DESC
            """, (usuario_id,))
            resultados = cursor.fetchall()
            imagenes = []
            for fila in resultados:
                imagenes.append({
                    "id": fila[0],
                    "imagen_path": fila[1],
                    "fecha_registro": str(fila[2]) if fila[2] else None
                })
            cursor.close()
            return jsonify(imagenes), 200
        
        # ----------- DELETE: Eliminar por id o por comparación facial -----------
        if request.method == "DELETE":
            # form-data o x-www-form-urlencoded
            imagen_id = request.form.get('imagen_id')
            if imagen_id:
                # Eliminar por id
                cursor.execute("SELECT imagen_path FROM imagenes WHERE id=%s AND usuario_id=%s", (imagen_id, usuario_id))
                fila = cursor.fetchone()
                if fila is None:
                    cursor.close()
                    return jsonify({"mensaje": "Imagen no encontrada para este usuario"}), 404
                ruta_relativa = fila[0]
                ruta_absoluta = os.path.join("uploads", ruta_relativa)
                if os.path.exists(ruta_absoluta):
                    os.remove(ruta_absoluta)
                cursor.execute("DELETE FROM imagenes WHERE id=%s AND usuario_id=%s", (imagen_id, usuario_id))
                mysql.connection.commit()
                cursor.close()
                return jsonify({"mensaje": "Imagen eliminada correctamente (por imagen_id)"}), 200
            
            # Eliminar por comparación facial (si no se mandó imagen_id pero sí imagen)
            if 'imagen' in request.files and request.files['imagen'].filename != '':
                imagen = request.files['imagen']
                imagen_bytes = imagen.read()
                emb_subida = obtener_embeddings(imagen_bytes)
                if emb_subida is None:
                    cursor.close()
                    return jsonify({"mensaje": "No se detectaron características en la imagen subida"}), 400

                cursor.execute("SELECT id, imagen_path, embeddings FROM imagenes WHERE usuario_id=%s", (usuario_id,))
                resultados = cursor.fetchall()
                umbral = 0.98  # Ajusta según tu necesidad

                for fila in resultados:
                    _id, _imagen_path, _embeddings_json = fila
                    emb_guardado = np.array(json.loads(_embeddings_json))
                    sim = float(np.dot(emb_subida, emb_guardado) / (np.linalg.norm(emb_subida) * np.linalg.norm(emb_guardado)))
                    if sim >= umbral:
                        ruta_absoluta = os.path.join("uploads", _imagen_path)
                        if os.path.exists(ruta_absoluta):
                            os.remove(ruta_absoluta)
                        cursor.execute("DELETE FROM imagenes WHERE id=%s AND usuario_id=%s", (_id, usuario_id))
                        mysql.connection.commit()
                        cursor.close()
                        return jsonify({"mensaje": f"Imagen eliminada por coincidencia facial (similitud: {sim:.4f})"}), 200

                cursor.close()
                return jsonify({"mensaje": "No se encontró imagen similar para eliminar"}), 404

            cursor.close()
            return jsonify({"mensaje": "Debes enviar 'imagen_id' o 'imagen' para eliminar"}), 400

    except Exception as e:
        print("Error en imagenes_usuario:", e)
        import traceback; traceback.print_exc()
        return jsonify({"mensaje": "Error en la operación"}), 500

#Eliminar Usuario(Sus imagenes)
@app.route("/eliminar_usuario/<int:usuario_id>", methods=["DELETE"])
def eliminar_usuario(usuario_id):
    try:
        # Eliminar imágenes del usuario (físico y base de datos)
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT imagen_path FROM imagenes WHERE usuario_id=%s", (usuario_id,))
        imagenes = cursor.fetchall()
        for img in imagenes:
            ruta = os.path.join("uploads", img[0])
            if os.path.exists(ruta):
                os.remove(ruta)
        # Eliminar registros de imágenes
        cursor.execute("DELETE FROM imagenes WHERE usuario_id=%s", (usuario_id,))
        # Eliminar usuario
        cursor.execute("DELETE FROM usuarios WHERE id=%s", (usuario_id,))
        mysql.connection.commit()
        cursor.close()
        # Eliminar carpeta si está vacía
        carpeta_usuario = os.path.join("uploads", f"user_{usuario_id}")
        if os.path.isdir(carpeta_usuario):
            try:
                os.rmdir(carpeta_usuario)
            except:
                pass
        return jsonify({"mensaje": "Usuario y sus imágenes eliminados"}), 200
    except Exception as e:
        print("Error eliminando usuario:", e)
        return jsonify({"mensaje": "Error al eliminar usuario"}), 500
  

# Ejecutar la app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)


