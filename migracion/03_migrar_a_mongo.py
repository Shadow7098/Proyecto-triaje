Codigo para hacer la transformacion y migrar los datos de SQL Server (base TriajeIPS) a MongoDB (base TriajeIPS_mongo)
aplicando un modelo documental: no se copia cada tabla como una colección,
sino que se decide qué se embebe y qué se referencia.

Colecciones resultantes:
  triajes   -> Triaje + Triaje_Sintoma (array embebido) + Atencion + Diagnostico (embebidos)
  pacientes -> Paciente + EPS (embebida)
  medicos   -> Medico + Especialidad (embebida)
  ips       -> IPS
  sintomas  -> Sintoma (catálogo)

Requisitos:  pip install pyodbc pymongo
Uso:         python 03_migrar_a_mongo.py

---------------------------------------3
CODIGO APARTIR DE LA SIGUIENTE LINEA:
---------------------------------------3

import random
from collections import defaultdict
from datetime import datetime

import pyodbc
from pymongo import MongoClient


# 1. Configuración

SERVIDOR = "SM_BUITRAGO"      # o "localhost\\SQLEXPRESS"
BASE = "TriajeIPS"
DRIVER = "ODBC Driver 17 for SQL Server"
USUARIO = None              # None = autenticación de Windows
CLAVE = None

MONGO_URI = "mongodb://localhost:27017"
BASE_MONGO = "TriajeIPS_mongo"


# 2. Conexiones

if USUARIO:
    autenticacion = f"UID={USUARIO};PWD={CLAVE};"
else:
    autenticacion = "Trusted_Connection=yes;"
sql = pyodbc.connect(f"DRIVER={{{DRIVER}}};SERVER={SERVIDOR};DATABASE={BASE};{autenticacion}"
                     "TrustServerCertificate=yes;")
mongo = MongoClient(MONGO_URI)[BASE_MONGO]


def leer(consulta, parametros=()):
    """Ejecuta una consulta en SQL Server y devuelve las filas como diccionarios."""
    cursor = sql.cursor()
    cursor.execute(consulta, *parametros)
    columnas = [c[0] for c in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def contar(consulta, parametros=()):
    cursor = sql.cursor()
    cursor.execute(consulta, *parametros)
    return cursor.fetchone()[0]


def a_datetime(fecha):
    """MongoDB no acepta objetos 'date' de Python, solo 'datetime'."""
    return datetime(fecha.year, fecha.month, fecha.day)



# 3. Transformación: de tablas a documentos
#    El _id de cada documento es el id que tenía en SQL Server.


# --- Catálogos que se referencian: casi iguales a sus tablas ---
sintomas = [{"_id": f["id_sintoma"], "nombre": f["nombre"], "categoria": f["categoria"],
             "nivel_alerta": f["nivel_alerta"]}
            for f in leer("SELECT * FROM Sintoma ORDER BY id_sintoma")]

ips = [{"_id": f["id_ips"], "nombre": f["nombre"], "ciudad": f["ciudad"], "direccion": f["direccion"],
        "nivel_complejidad": f["nivel_complejidad"], "capacidad_urgencias": f["capacidad_urgencias"]}
       for f in leer("SELECT * FROM IPS ORDER BY id_ips")]

# --- Pacientes: la EPS va EMBEBIDA (casi no cambia y siempre se consulta con el paciente) ---
pacientes = []
for f in leer("""SELECT p.*, e.nombre AS eps_nombre, e.nit AS eps_nit, e.regimen AS eps_regimen
                 FROM Paciente p JOIN EPS e ON e.id_eps = p.id_eps
                 ORDER BY p.id_paciente"""):
    pacientes.append({
        "_id": f["id_paciente"], "tipo_documento": f["tipo_documento"],
        "numero_documento": f["numero_documento"], "nombres": f["nombres"], "apellidos": f["apellidos"],
        "fecha_nacimiento": a_datetime(f["fecha_nacimiento"]), "sexo": f["sexo"],
        "telefono": f["telefono"], "ciudad": f["ciudad"],
        "eps": {"nombre": f["eps_nombre"], "nit": f["eps_nit"], "regimen": f["eps_regimen"]},
    })

# --- Médicos: la especialidad va EMBEBIDA; la IPS se REFERENCIA ---
medicos = []
for f in leer("""SELECT m.*, es.nombre AS especialidad_nombre
                 FROM Medico m JOIN Especialidad es ON es.id_especialidad = m.id_especialidad
                 ORDER BY m.id_medico"""):
    medicos.append({
        "_id": f["id_medico"], "nombres": f["nombres"], "apellidos": f["apellidos"],
        "registro_medico": f["registro_medico"],
        "especialidad": {"id": f["id_especialidad"], "nombre": f["especialidad_nombre"]},
        "ips_id": f["id_ips"],
    })

# --- Triajes: aquí se unen varias tablas en un solo documento ---
# En vez de una consulta por triaje (1.100), leemos todo una vez y agrupamos en memoria.
sintomas_de_triaje = defaultdict(list)          # id_triaje -> lista de síntomas
for f in leer("""SELECT ts.id_triaje, ts.id_sintoma, s.nombre, s.categoria, s.nivel_alerta,
                        ts.intensidad, ts.duracion_horas
                 FROM Triaje_Sintoma ts JOIN Sintoma s ON s.id_sintoma = ts.id_sintoma
                 ORDER BY ts.id_triaje_sintoma"""):
    sintomas_de_triaje[f["id_triaje"]].append({
        "sintoma_id": f["id_sintoma"],          # referencia al catálogo
        "nombre": f["nombre"],                  # copia del nombre (evita un $lookup en cada lectura)
        "categoria": f["categoria"],
        "nivel_alerta": f["nivel_alerta"],
        "intensidad": f["intensidad"],
        "duracion_horas": f["duracion_horas"],
    })

atencion_de_triaje = {}                         # id_triaje -> subdocumento de atención
for f in leer("""SELECT a.*, d.codigo_cie10, d.descripcion
                 FROM Atencion a JOIN Diagnostico d ON d.id_diagnostico = a.id_diagnostico"""):
    atencion_de_triaje[f["id_triaje"]] = {
        "medico_id": f["id_medico"],            # referencia al médico
        "fecha_hora_inicio": f["fecha_hora_inicio"],
        "duracion_minutos": f["duracion_minutos"],
        "resultado": f["resultado"],
        "diagnostico": {"codigo_cie10": f["codigo_cie10"], "descripcion": f["descripcion"]},
    }

triajes = []
for f in leer("SELECT * FROM Triaje ORDER BY id_triaje"):
    documento = {
        "_id": f["id_triaje"],
        "paciente_id": f["id_paciente"],        # referencias
        "ips_id": f["id_ips"],
        "fecha_hora": f["fecha_hora"],
        "canal": f["canal"],
        "nivel_asignado": f["nivel_asignado"],
        "puntaje_total": f["puntaje_total"],
        "sintomas": sintomas_de_triaje[f["id_triaje"]],     # array de documentos embebidos
    }
    if f["id_triaje"] in atencion_de_triaje:                # los triajes sin atención no llevan el campo
        documento["atencion"] = atencion_de_triaje[f["id_triaje"]]
    triajes.append(documento)


# 4. Carga en MongoDB (se borra lo anterior para poder repetir la migración)

COLECCIONES = {"sintomas": sintomas, "ips": ips, "pacientes": pacientes, "medicos": medicos, "triajes": triajes}
for nombre, documentos in COLECCIONES.items():
    mongo.drop_collection(nombre)
    mongo[nombre].insert_many(documentos)
    print(f"Colección {nombre:<10} {len(documentos):>5} documentos")


# 5. Verificación: ¿los datos pasaron completos y consistentes?

fallos = 0


def comprobar(descripcion, condicion):
    global fallos
    print(("  [OK]    " if condicion else "  [ERROR] ") + descripcion)
    if not condicion:
        fallos += 1


print("\n--- 1. Conteo de registros: SQL Server contra MongoDB ---")
for tabla, coleccion in [("Paciente", "pacientes"), ("Medico", "medicos"), ("IPS", "ips"),
                         ("Sintoma", "sintomas"), ("Triaje", "triajes")]:
    en_sql, en_mongo = contar(f"SELECT COUNT(*) FROM {tabla}"), mongo[coleccion].count_documents({})
    comprobar(f"{tabla}: {en_sql} filas en SQL, {en_mongo} documentos en {coleccion}", en_sql == en_mongo)

sintomas_embebidos = next(mongo.triajes.aggregate([
    {"$group": {"_id": None, "total": {"$sum": {"$size": "$sintomas"}}}}]))["total"]
en_sql = contar("SELECT COUNT(*) FROM Triaje_Sintoma")
comprobar(f"Triaje_Sintoma: {en_sql} filas en SQL, {sintomas_embebidos} síntomas dentro de los triajes",
          en_sql == sintomas_embebidos)

con_atencion = mongo.triajes.count_documents({"atencion": {"$exists": True}})
en_sql = contar("SELECT COUNT(*) FROM Atencion")
comprobar(f"Atencion: {en_sql} filas en SQL, {con_atencion} triajes con atención embebida", en_sql == con_atencion)

print("\n--- 2. Referencias: cada id referenciado existe en su colección ---")
ids_pacientes = set(mongo.pacientes.distinct("_id"))
ids_ips = set(mongo.ips.distinct("_id"))
ids_medicos = set(mongo.medicos.distinct("_id"))
ids_sintomas = set(mongo.sintomas.distinct("_id"))
comprobar("triajes.paciente_id -> pacientes", set(mongo.triajes.distinct("paciente_id")) <= ids_pacientes)
comprobar("triajes.ips_id -> ips", set(mongo.triajes.distinct("ips_id")) <= ids_ips)
comprobar("triajes.atencion.medico_id -> medicos", set(mongo.triajes.distinct("atencion.medico_id")) <= ids_medicos)
comprobar("triajes.sintomas.sintoma_id -> sintomas", set(mongo.triajes.distinct("sintomas.sintoma_id")) <= ids_sintomas)
comprobar("medicos.ips_id -> ips", set(mongo.medicos.distinct("ips_id")) <= ids_ips)

print("\n--- 3. Comparación de 5 triajes al azar: SQL Server contra MongoDB ---")
for id_triaje in random.sample(sorted(d["_id"] for d in triajes), 5):
    doc = mongo.triajes.find_one({"_id": id_triaje})
    fila = leer("SELECT nivel_asignado, puntaje_total FROM Triaje WHERE id_triaje = ?", (id_triaje,))[0]
    n_sintomas = contar("SELECT COUNT(*) FROM Triaje_Sintoma WHERE id_triaje = ?", (id_triaje,))
    atencion = leer("SELECT resultado FROM Atencion WHERE id_triaje = ?", (id_triaje,))
    igual = (doc["nivel_asignado"] == fila["nivel_asignado"] and doc["puntaje_total"] == fila["puntaje_total"]
             and len(doc["sintomas"]) == n_sintomas
             and (doc["atencion"]["resultado"] if "atencion" in doc else None)
             == (atencion[0]["resultado"] if atencion else None))
    comprobar(f"Triaje {id_triaje}: nivel {fila['nivel_asignado']}, puntaje {fila['puntaje_total']}, "
              f"{n_sintomas} síntoma(s), {'con' if atencion else 'sin'} atención", igual)

print("\nMigración correcta." if fallos == 0 else f"\nHay {fallos} verificaciones con error.")
sql.close()
