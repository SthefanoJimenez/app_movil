import numpy as np

def similitud_coseno(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

import os
import json
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import db_config
from utils.face_utils import obtener_embeddings_lbp as obtener_embeddings
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


# Ruta: Agregar imagen + embeddings SIFT a un usuario
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
            return jsonify({"mensaje": "No se detectaron características LBP"}), 400

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

        # Almacenar similitudes agrupadas por usuario
        umbral_similitud = 0.975
        cantidad_minima = 2  # Requiere al menos 2 coincidencias por usuario

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
                continue  # Saltar si hay conflicto de tamaño

            similitud = similitud_coseno(emb_ext, emb_guardado)

            if similitud >= umbral_similitud:
                if usuario_id not in candidatos:
                    candidatos[usuario_id] = {
                        "nombre": nombre,
                        "apellido": apellido,
                        "codigo_unico": codigo,
                        "requisitoriado": bool(requisitoriado),
                        "similitudes": [],
                        "imagenes": []
                    }
                candidatos[usuario_id]["similitudes"].append(similitud)
                candidatos[usuario_id]["imagenes"].append(imagen_path)

        # Buscar usuario con más coincidencias válidas
        mejor_usuario = None
        max_similitudes = 0

        for uid, data in candidatos.items():
            if len(data["similitudes"]) >= cantidad_minima:
                promedio = sum(data["similitudes"]) / len(data["similitudes"])
                if len(data["similitudes"]) > max_similitudes:
                    max_similitudes = len(data["similitudes"])
                    mejor_usuario = {
                        "usuario_id": uid,
                        "nombre": data["nombre"],
                        "apellido": data["apellido"],
                        "codigo_unico": data["codigo_unico"],
                        "similitud_promedio": round(promedio, 4),
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

# Ejecutar la app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)


