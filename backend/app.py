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
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import db_config

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
        nombre         = request.form['nombre']
        apellido       = request.form['apellido']
        codigo_unico   = request.form['codigo_unico']
        email          = request.form['email']
        requisitoriado = request.form['requisitoriado'] == 'true'

        cursor = mysql.connection.cursor()
        sql = """
            INSERT INTO usuarios (nombre, apellido, codigo_unico, email, requisitoriado)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (nombre, apellido, codigo_unico, email, requisitoriado))
        mysql.connection.commit()

        # Obtener ID generado
        inserted_id = cursor.lastrowid
        print(f"Usuario registrado con ID: {inserted_id}")  # sale en la consola

        cursor.close()

        # Devolver sólo el mensaje con el ID incluido
        return jsonify({
            "mensaje": f"Usuario registrado exitosamente con ID {inserted_id}"
        }), 200

    except Exception as e:
        print("Error al registrar usuario:", e)
        return jsonify({"mensaje": "Error al registrar usuario"}), 500


# Ruta: Agregar imagen + embeddings LBP + LPQ a un usuario
@app.route("/agregar_imagen/<int:usuario_id>", methods=["POST"])
def agregar_imagen(usuario_id):
    try:
        imagen = request.files['imagen']
        filename = secure_filename(imagen.filename)

        # 📂 Crear carpeta del usuario si no existe
        carpeta_usuario = os.path.join("uploads", f"user_{usuario_id}")
        os.makedirs(carpeta_usuario, exist_ok=True)

        # 🖼️ Guardar imagen dentro de la carpeta del usuario
        ruta_guardado = os.path.join(carpeta_usuario, filename)
        imagen.save(ruta_guardado)

        with open(ruta_guardado, 'rb') as f:
            imagen_bytes = f.read()

        embeddings = obtener_embeddings(imagen_bytes)
        if embeddings is None:
            return jsonify({"mensaje": "No se detectaron características LBP+LPQ+HOG+SIFT"}), 400

        # Guardar solo la ruta relativa a la carpeta del usuario
        ruta_relativa = os.path.join(f"user_{usuario_id}", filename)

        # 💾 Guardar ruta + embeddings en la base de datos
        cursor = mysql.connection.cursor()
        sql = """INSERT INTO imagenes (usuario_id, imagen_path, embeddings)
                 VALUES (%s, %s, %s)"""
        cursor.execute(sql, (usuario_id, ruta_relativa, json.dumps(embeddings)))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"mensaje": "Imagen agregada exitosamente"}), 200

    except Exception as e:
        print("Error al agregar imagen:", e)
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

        # Extraer características
        with open(ruta_temporal, 'rb') as f:
            imagen_bytes = f.read()
        emb_ext = obtener_embeddings(imagen_bytes)

        if emb_ext is None:
            return jsonify({"mensaje": "No se detectaron características en la imagen"}), 400

        # Obtener embeddings de la base
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT i.embeddings, i.imagen_path, u.id, u.nombre, u.apellido, u.codigo_unico, u.requisitoriado
            FROM imagenes i
            JOIN usuarios u ON i.usuario_id = u.id
        """)
        resultados = cursor.fetchall()
        cursor.close()

        # Umbrales (ajústalos según tus experimentos)
        umbral_similitud = 0.85    # similitud coseno, mayor o igual
        umbral_euclidiana = 0.50   # distancia euclidiana, menor o igual
        cantidad_minima = 4

        candidatos = {}

        for fila in resultados:
            emb_guardado = json.loads(fila[0])
            imagen_path = fila[1]
            usuario_id = fila[2]
            nombre = fila[3]
            apellido = fila[4]
            codigo = fila[5]
            requisitoriado = fila[6]

            if len(emb_guardado) != len(emb_ext):
                continue

            sim_cos = similitud_coseno(emb_ext, emb_guardado)
            dist_euc = distancia_euclidiana(emb_ext, emb_guardado)

            # Puedes requerir ambas condiciones, o solo una, o guardar ambas para análisis
            if sim_cos >= umbral_similitud and dist_euc <= umbral_euclidiana:
                if usuario_id not in candidatos:
                    candidatos[usuario_id] = {
                        "nombre": nombre,
                        "apellido": apellido,
                        "codigo_unico": codigo,
                        "requisitoriado": bool(requisitoriado),
                        "similitudes": [],
                        "distancias": [],
                        "imagenes": []
                    }
                candidatos[usuario_id]["similitudes"].append(sim_cos)
                candidatos[usuario_id]["distancias"].append(dist_euc)
                candidatos[usuario_id]["imagenes"].append(imagen_path)

        # Buscar usuario con más coincidencias válidas
        mejor_usuario = None
        max_similitudes = 0

        for uid, data in candidatos.items():
            if len(data["similitudes"]) >= cantidad_minima:
                promedio_sim = sum(data["similitudes"]) / len(data["similitudes"])
                promedio_dist = sum(data["distancias"]) / len(data["distancias"])
                if len(data["similitudes"]) > max_similitudes:
                    max_similitudes = len(data["similitudes"])
                    mejor_usuario = {
                        "usuario_id": uid,
                        "nombre": data["nombre"],
                        "apellido": data["apellido"],
                        "codigo_unico": data["codigo_unico"],
                        "similitud_promedio": round(promedio_sim, 4),
                        "distancia_promedio": round(promedio_dist, 4),
                        "requisitoriado": data["requisitoriado"],
                        "imagen_referencia": data["imagenes"][0]
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


