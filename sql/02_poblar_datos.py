PARTE 2: GENERACION DE DATOS PARA LA BASE
Genera datos de ejemplo (5.500 registros) y los carga en SQL Server.
Antes de ejecutarlo, se debera correr 01_crear_tablas.sql en SQL Server.

Uso:  python 02_poblar_datos.py
"""
import random
from datetime import datetime, timedelta

import pyodbc

# ---------------------------------------------------------------
# 1. Configuración de la conexión (cámbiala según tu equipo)
# ---------------------------------------------------------------
SERVIDOR = "SM_BUITRAGO"      # o "localhost\\SQLEXPRESS"
BASE = "TriajeIPS"
DRIVER = "ODBC Driver 17 for SQL Server"
USUARIO = None              # None = autenticación de Windows
CLAVE = None

# ---------------------------------------------------------------
# 2. Cantidades (suman 5.500 registros)
# ---------------------------------------------------------------
N_PACIENTES = 600
N_TRIAJES = 1100
N_ATENCIONES = 990          # el 10 % de los triajes queda sin atención
N_TRIAJE_SINTOMAS = 2660    # entre 1 y 4 síntomas por triaje

# Reglas del triaje: puntaje = suma de (intensidad x nivel_alerta) de cada síntoma
UMBRAL_URGENTE = 40         # puntaje >= 40  -> nivel 3 (urgente)
UMBRAL_MEDIO = 20           # puntaje >= 20  -> nivel 2 (media), si no nivel 1 (normal)

random.seed(42)             # así salen los mismos datos cada vez
HOY = datetime(2026, 10, 15)

# ---------------------------------------------------------------
# 3. Catálogos (tablas pequeñas)
# ---------------------------------------------------------------
NOMBRES_EPS = ["EPS Vida Sana", "EPS Nueva Esperanza", "EPS Unisalud", "EPS Bienestar",
               "EPS Cooperativa Salud", "EPS Familia Sana", "EPS Integral",
               "EPS Protección Total", "EPS Mutual Andina", "EPS Salud Capital"]

# (nombre, ciudad, nivel_complejidad, capacidad_urgencias)
DATOS_IPS = [("IPS Clínica del Norte", "Medellín", 3, 60), ("IPS Hospital San Rafael", "Medellín", 3, 80),
             ("IPS Centro Médico Aburrá", "Medellín", 2, 35), ("IPS Clínica La Esperanza", "Bogotá", 3, 90),
             ("IPS Hospital Santa Clara", "Bogotá", 2, 50), ("IPS Clínica del Valle", "Cali", 3, 70),
             ("IPS Centro de Salud Pacífico", "Cali", 1, 20), ("IPS Clínica Marina", "Barranquilla", 2, 45),
             ("IPS Hospital Santander", "Bucaramanga", 2, 40), ("IPS Clínica Caribe", "Cartagena", 2, 38)]

# El id de cada especialidad es su posición en la lista (1 a 10)
NOMBRES_ESPECIALIDAD = ["Medicina General", "Urgencias", "Cardiología", "Neumología", "Gastroenterología",
                        "Neurología", "Pediatría", "Ortopedia", "Ginecología", "Medicina Interna"]

# (nombre, categoría, nivel_alerta de 1 a 3)
DATOS_SINTOMAS = [
    ("Tos seca", "Respiratorio", 1), ("Congestión nasal", "Respiratorio", 1),
    ("Dolor de garganta", "Respiratorio", 1), ("Dificultad para respirar", "Respiratorio", 3),
    ("Silbidos al respirar", "Respiratorio", 2), ("Tos con sangre", "Respiratorio", 3),
    ("Dolor de pecho", "Cardiovascular", 3), ("Palpitaciones", "Cardiovascular", 2),
    ("Desmayo", "Cardiovascular", 3), ("Náuseas", "Digestivo", 1), ("Vómito", "Digestivo", 2),
    ("Diarrea", "Digestivo", 1), ("Dolor abdominal intenso", "Digestivo", 3),
    ("Acidez estomacal", "Digestivo", 1), ("Sangre en heces", "Digestivo", 3),
    ("Dolor de cabeza", "Neurológico", 1), ("Migraña intensa", "Neurológico", 2),
    ("Mareo", "Neurológico", 2), ("Convulsiones", "Neurológico", 3),
    ("Debilidad en un lado del cuerpo", "Neurológico", 3), ("Confusión", "Neurológico", 3),
    ("Fiebre", "General", 2), ("Fiebre alta persistente", "General", 3), ("Cansancio", "General", 1),
    ("Dolor lumbar", "Musculoesquelético", 1), ("Dolor articular", "Musculoesquelético", 1),
    ("Trauma con deformidad", "Musculoesquelético", 3), ("Dolor al orinar", "Urinario", 1),
    ("Sangrado vaginal", "Ginecológico", 3), ("Erupción en la piel", "Piel", 1)]

# (código CIE-10, descripción, id_especialidad)
DATOS_DIAGNOSTICOS = [
    ("J00", "Rinofaringitis aguda (resfriado común)", 1), ("J02.9", "Faringitis aguda no especificada", 1),
    ("J06.9", "Infección aguda de las vías respiratorias superiores", 1), ("A90", "Dengue clásico", 1),
    ("B34.9", "Infección viral no especificada", 1), ("N39.0", "Infección de vías urinarias", 1),
    ("L50.9", "Urticaria no especificada", 1), ("R50.9", "Fiebre no especificada", 1),
    ("R55", "Síncope y colapso", 2), ("E86", "Deshidratación", 2), ("T78.4", "Alergia no especificada", 2),
    ("R07.4", "Dolor torácico no especificado", 2), ("I20.9", "Angina de pecho", 3),
    ("I21.9", "Infarto agudo de miocardio", 3), ("I48", "Fibrilación y aleteo auricular", 3),
    ("I50.9", "Insuficiencia cardíaca", 3), ("J18.9", "Neumonía no especificada", 4),
    ("J20.9", "Bronquitis aguda", 4), ("J45.9", "Asma", 4),
    ("J44.9", "Enfermedad pulmonar obstructiva crónica", 4),
    ("A09", "Diarrea y gastroenteritis infecciosa", 5), ("K29.7", "Gastritis no especificada", 5),
    ("K35.8", "Apendicitis aguda", 5), ("K80.2", "Colelitiasis", 5),
    ("K21.9", "Enfermedad por reflujo gastroesofágico", 5), ("G43.9", "Migraña", 6),
    ("G40.9", "Epilepsia", 6), ("I63.9", "Infarto cerebral", 6), ("R51", "Cefalea", 6),
    ("J21.9", "Bronquiolitis aguda", 7), ("B09", "Infección viral con lesiones de piel y mucosas", 7),
    ("M54.5", "Lumbago no especificado", 8), ("S52.5", "Fractura del extremo distal del radio", 8),
    ("S93.4", "Esguince de tobillo", 8), ("M25.5", "Dolor articular", 8),
    ("O20.0", "Amenaza de aborto", 9), ("N76.0", "Vaginitis aguda", 9),
    ("O47.0", "Falso trabajo de parto antes de 37 semanas", 9),
    ("I10", "Hipertensión esencial", 10), ("E11.9", "Diabetes mellitus tipo 2", 10)]

NOMBRES_M = ["Juan", "Carlos", "Andrés", "Santiago", "Camilo", "Felipe", "Daniel", "Sebastián", "Mateo",
             "Julián", "David", "Esteban", "Miguel", "Alejandro", "Jorge", "Luis", "Nicolás", "Samuel"]
NOMBRES_F = ["María", "Laura", "Valentina", "Camila", "Daniela", "Sofía", "Paula", "Natalia", "Juliana",
             "Isabella", "Andrea", "Carolina", "Mariana", "Luisa", "Catalina", "Gabriela", "Sara", "Diana"]
APELLIDOS = ["Gómez", "Rodríguez", "Martínez", "López", "García", "Hernández", "Pérez", "Sánchez", "Ramírez",
             "Torres", "Díaz", "Vargas", "Castro", "Rojas", "Moreno", "Jiménez", "Ortiz", "Gutiérrez",
             "Restrepo", "Cardona", "Henao", "Zapata", "Ospina", "Mejía", "Londoño", "Giraldo"]

# Diagnósticos plausibles según la categoría del síntoma principal: (leves, graves)
# Nivel 1 usa los leves, nivel 3 los graves y nivel 2 una mezcla de ambos.
CATEGORIA_DIAGNOSTICOS = {
    "Respiratorio": (["J00", "J02.9", "J06.9", "J20.9"], ["J18.9", "J45.9", "J44.9"]),
    "Cardiovascular": (["R07.4", "I10"], ["I20.9", "I21.9", "I48", "I50.9", "R55"]),
    "Digestivo": (["A09", "K29.7", "K21.9"], ["K35.8", "K80.2"]),
    "Neurológico": (["R51", "G43.9"], ["G40.9", "I63.9"]),
    "General": (["R50.9", "B34.9"], ["A90", "E86"]),
    "Musculoesquelético": (["M54.5", "M25.5"], ["S52.5", "S93.4"]),
    "Urinario": (["N39.0"], ["N39.0"]),
    "Ginecológico": (["N76.0"], ["O20.0", "O47.0"]),
    "Piel": (["L50.9", "B09"], ["T78.4"]),
}

# ---------------------------------------------------------------
# 4. Generación de los datos
#    Cada fila es una tupla en el mismo orden de las columnas de la tabla.
# ---------------------------------------------------------------
eps = [(i + 1, nombre, f"900{random.randint(100000, 999999)}-{random.randint(0, 9)}",
        "Subsidiado" if i % 3 == 0 else "Contributivo")
       for i, nombre in enumerate(NOMBRES_EPS)]

ips = [(i + 1, nombre, ciudad, f"Calle {random.randint(1, 80)} # {random.randint(1, 99)}-{random.randint(1, 99)}",
        nivel, capacidad)
       for i, (nombre, ciudad, nivel, capacidad) in enumerate(DATOS_IPS)]

especialidades = [(i + 1, nombre) for i, nombre in enumerate(NOMBRES_ESPECIALIDAD)]
sintomas = [(i + 1, nombre, categoria, alerta) for i, (nombre, categoria, alerta) in enumerate(DATOS_SINTOMAS)]
diagnosticos = [(i + 1, codigo, descripcion, esp) for i, (codigo, descripcion, esp) in enumerate(DATOS_DIAGNOSTICOS)]

# Médicos: cada IPS tiene 5 (uno de Medicina General, uno de Urgencias y tres de otras especialidades)
medicos = []
medicos_por_ips = {}
for fila_ips in ips:
    id_ips = fila_ips[0]
    medicos_por_ips[id_ips] = []
    for id_esp in [1, 2] + [random.randint(3, 10) for _ in range(3)]:
        id_medico = len(medicos) + 1
        nombre = random.choice(NOMBRES_M + NOMBRES_F)
        apellidos = f"{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
        medicos.append((id_medico, nombre, apellidos, f"RM-{10000 + id_medico}", id_esp, id_ips))
        medicos_por_ips[id_ips].append(id_medico)

# Pacientes
ciudades = [fila[2] for fila in ips]
pacientes = []
for id_paciente in range(1, N_PACIENTES + 1):
    sexo = random.choice("MF")
    nombre = random.choice(NOMBRES_M if sexo == "M" else NOMBRES_F)
    edad = random.randint(0, 90)
    nacimiento = (HOY - timedelta(days=edad * 365 + random.randint(0, 364))).date()
    tipo_doc = "RC" if edad < 7 else "TI" if edad < 18 else "CC"
    documento = str(10_000_000 + id_paciente * 1000 + random.randint(0, 999))  # nunca se repite
    telefono = f"3{random.randint(100000000, 299999999)}"
    pacientes.append((id_paciente, tipo_doc, documento, nombre, f"{random.choice(APELLIDOS)} {random.choice(APELLIDOS)}",
                      nacimiento, sexo, telefono, random.choice(ciudades), random.randint(1, len(eps))))

# Cuántos síntomas tiene cada triaje (1 a 4), ajustando para que el total sea exacto
sintomas_por_triaje = [random.randint(1, 4) for _ in range(N_TRIAJES)]
while sum(sintomas_por_triaje) != N_TRIAJE_SINTOMAS:
    i = random.randrange(N_TRIAJES)
    if sum(sintomas_por_triaje) < N_TRIAJE_SINTOMAS and sintomas_por_triaje[i] < 4:
        sintomas_por_triaje[i] += 1
    elif sum(sintomas_por_triaje) > N_TRIAJE_SINTOMAS and sintomas_por_triaje[i] > 1:
        sintomas_por_triaje[i] -= 1

# Todos los pacientes tienen al menos un triaje; el resto se reparte al azar
pacientes_de_triaje = list(range(1, N_PACIENTES + 1)) + \
                      [random.randint(1, N_PACIENTES) for _ in range(N_TRIAJES - N_PACIENTES)]
random.shuffle(pacientes_de_triaje)

# Primero armamos los triajes "en borrador" para poder ordenarlos por fecha antes de numerarlos
borradores = []
for i in range(N_TRIAJES):
    detalle = []
    puntaje = 0
    for sintoma in random.sample(sintomas, sintomas_por_triaje[i]):
        intensidad = random.randint(1, 10)
        puntaje += intensidad * sintoma[3]               # sintoma[3] es el nivel_alerta
        detalle.append((sintoma[0], intensidad, random.randint(1, 72)))
    nivel = 3 if puntaje >= UMBRAL_URGENTE else 2 if puntaje >= UMBRAL_MEDIO else 1
    fecha = HOY - timedelta(days=random.randint(0, 364), hours=random.randint(0, 23),
                            minutes=random.randint(0, 59))
    borradores.append((fecha, pacientes_de_triaje[i], random.randint(1, len(ips)),
                       random.choice(["Cuestionario", "Chatbot"]), nivel, puntaje, detalle))
borradores.sort(key=lambda b: b[0])

triajes = []
triaje_sintomas = []
for id_triaje, (fecha, id_paciente, id_ips, canal, nivel, puntaje, detalle) in enumerate(borradores, start=1):
    triajes.append((id_triaje, id_paciente, id_ips, fecha, canal, nivel, puntaje))
    for id_sintoma, intensidad, duracion in detalle:
        triaje_sintomas.append((len(triaje_sintomas) + 1, id_triaje, id_sintoma, intensidad, duracion))

# Atenciones: se atiende a 990 de los 1.100 triajes, elegidos al azar
espera_por_nivel = {1: (25, 180), 2: (10, 60), 3: (0, 15)}        # minutos de espera (mín, máx)
resultados_por_nivel = {1: ["Alta"] * 9 + ["Observacion"],
                        2: ["Alta"] * 6 + ["Observacion"] * 2 + ["Remision", "Hospitalizacion"],
                        3: ["Alta", "Observacion", "Observacion", "Hospitalizacion", "Hospitalizacion", "Remision"]}
medico_especialidad = {m[0]: m[4] for m in medicos}
sintoma_por_id = {s[0]: s for s in sintomas}
diagnostico_por_codigo = {d[1]: d for d in diagnosticos}

atenciones = []
for indice in sorted(random.sample(range(N_TRIAJES), N_ATENCIONES)):
    id_triaje, _, id_ips, fecha, _, nivel, _ = triajes[indice]
    # El diagnóstico depende de los síntomas: se parte del síntoma principal (el de mayor alerta)
    detalle = borradores[indice][6]
    principal = max(detalle, key=lambda d: (sintoma_por_id[d[0]][3], d[1]))
    leves, graves = CATEGORIA_DIAGNOSTICOS[sintoma_por_id[principal[0]][2]]
    codigos = leves if nivel == 1 else graves if nivel == 3 else leves + graves
    id_diagnostico, _, _, especialidad_dx = diagnostico_por_codigo[random.choice(codigos)]
    # Atiende un médico de esa especialidad en la misma IPS; si no hay, uno de Medicina General
    # (el primer médico de cada IPS siempre es de Medicina General)
    candidatos = [m for m in medicos_por_ips[id_ips] if medico_especialidad[m] == especialidad_dx]
    id_medico = random.choice(candidatos or [medicos_por_ips[id_ips][0]])
    espera = random.randint(*espera_por_nivel[nivel])
    duracion = random.randint(30, 120) if nivel == 3 else random.randint(10, 45)
    atenciones.append((len(atenciones) + 1, id_triaje, id_medico, id_diagnostico,
                       fecha + timedelta(minutes=espera), duracion, random.choice(resultados_por_nivel[nivel])))

# ---------------------------------------------------------------
# 5. Carga en SQL Server (el orden respeta las llaves foráneas)
# ---------------------------------------------------------------
TABLAS = [
    ("EPS", "id_eps, nombre, nit, regimen", eps),
    ("IPS", "id_ips, nombre, ciudad, direccion, nivel_complejidad, capacidad_urgencias", ips),
    ("Especialidad", "id_especialidad, nombre", especialidades),
    ("Sintoma", "id_sintoma, nombre, categoria, nivel_alerta", sintomas),
    ("Diagnostico", "id_diagnostico, codigo_cie10, descripcion, id_especialidad", diagnosticos),
    ("Paciente", "id_paciente, tipo_documento, numero_documento, nombres, apellidos, "
                 "fecha_nacimiento, sexo, telefono, ciudad, id_eps", pacientes),
    ("Medico", "id_medico, nombres, apellidos, registro_medico, id_especialidad, id_ips", medicos),
    ("Triaje", "id_triaje, id_paciente, id_ips, fecha_hora, canal, nivel_asignado, puntaje_total", triajes),
    ("Triaje_Sintoma", "id_triaje_sintoma, id_triaje, id_sintoma, intensidad, duracion_horas", triaje_sintomas),
    ("Atencion", "id_atencion, id_triaje, id_medico, id_diagnostico, fecha_hora_inicio, "
                 "duracion_minutos, resultado", atenciones),
]

if USUARIO:
    autenticacion = f"UID={USUARIO};PWD={CLAVE};"
else:
    autenticacion = "Trusted_Connection=yes;"
conexion = pyodbc.connect(f"DRIVER={{{DRIVER}}};SERVER={SERVIDOR};DATABASE={BASE};{autenticacion}"
                          "TrustServerCertificate=yes;")
cursor = conexion.cursor()
cursor.fast_executemany = True

for tabla, columnas, filas in TABLAS:
    marcas = ", ".join("?" * (columnas.count(",") + 1))
    # Las llaves primarias son IDENTITY: para insertar nuestros propios ids hay que activarlo
    cursor.execute(f"SET IDENTITY_INSERT dbo.{tabla} ON")
    cursor.executemany(f"INSERT INTO dbo.{tabla} ({columnas}) VALUES ({marcas})", filas)
    cursor.execute(f"SET IDENTITY_INSERT dbo.{tabla} OFF")
conexion.commit()

# ---------------------------------------------------------------
# 6. Comprobación: filas en SQL Server contra filas generadas
# ---------------------------------------------------------------
total = 0
for tabla, _, filas in TABLAS:
    en_base = cursor.execute(f"SELECT COUNT(*) FROM dbo.{tabla}").fetchone()[0]
    total += en_base
    print(f"{tabla:<16} {en_base:>6}", "" if en_base == len(filas) else "  <-- NO COINCIDE")
print(f"{'TOTAL':<16} {total:>6}")
conexion.close()
