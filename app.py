import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
from pytz import timezone
from zoneinfo import ZoneInfo
from flask import render_template

app = Flask(__name__)
CORS(app)

# MongoDB Atlas URI desde variable de entorno
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["BasePryEsp32"]
collection = db["Datos"]



# Ruta para recibir datos del ESP32
@app.route("/api/data", methods=["POST"])
def recibir_dato():
    try:
        data = request.get_json()
        print("JSON recibido:", data)

        required_keys = ["dispositivo", "temperatura", "humedad", "luz", "movimiento"]
        if not all(k in data for k in required_keys):
            return jsonify({"error": "Faltan campos"}), 400

        if not (isinstance(data["temperatura"], (int, float)) and
                isinstance(data["humedad"], (int, float)) and
                isinstance(data["luz"], int) and
                isinstance(data["movimiento"], int)):
            return jsonify({"error": "Tipos inválidos"}), 400

        documento = {
            "dispositivo": data["dispositivo"],
            "temperatura": float(data["temperatura"]),
            "humedad": float(data["humedad"]),
            "luz": int(data["luz"]),
            "movimiento": int(data["movimiento"]),
            "timestamp": datetime.utcnow() - timedelta(hours=6)
        }
        result = collection.insert_one(documento)
        return jsonify({"message": "Guardado", "id": str(result.inserted_id)}), 200
    except Exception as e:
        print("Error MongoDB:", str(e))
        return jsonify({"error": str(e)}), 500



# Ruta para ver los últimos 50 datos
@app.route("/api/datos", methods=["GET"])
def ver_datos():
    datos = list(collection.find().sort("timestamp", -1).limit(50))
    for d in datos:
        d["_id"] = str(d["_id"])
        d["timestamp"] = d["timestamp"].isoformat()

    return jsonify(datos), 200


@app.route("/ver-datos")
def ver_pagina_datos():
    return render_template("index.html")

@app.route("/api/estadisticas", methods=["GET"])
def estadisticas():
    try:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "temp_prom": {"$avg": "$temperatura"},
                    "temp_min": {"$min": "$temperatura"},
                    "temp_max": {"$max": "$temperatura"},
                    "hum_prom": {"$avg": "$humedad"},
                    "hum_min": {"$min": "$humedad"},
                    "hum_max": {"$max": "$humedad"},
                    "luz_prom": {"$avg": "$luz"},
                    "mov_total": {"$sum": "$movimiento"},
                    "total_registros": {"$sum": 1}
                }
            }
        ]
        result = list(collection.aggregate(pipeline))
        return jsonify(result[0] if result else {}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ver-estadisticas")
def ver_estadisticas():
    return render_template("estadisticas.html")


@app.route("/", methods=["GET"])
def index():
    return "API Flask con MongoDB funcionando en Render", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
