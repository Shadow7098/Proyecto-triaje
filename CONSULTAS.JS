Consultas sobre la base TriajeIPS_mongo (colección triajes)

Consulta 1: Casos urgentes sin atención 
¿Qué pacientes clasificados como urgentes (nivel 3) no tienen ninguna atención registrada?

db.triajes.aggregate([
  { $match: { nivel_asignado: 3, atencion: { $exists: false } } },
  { $sort: { fecha_hora: -1 } },
  { $limit: 20 },
  { $lookup: { from: "pacientes", localField: "paciente_id", foreignField: "_id", as: "paciente" } },
  { $lookup: { from: "ips", localField: "ips_id", foreignField: "_id", as: "ips" } },
  { $unwind: "$paciente" },
  { $unwind: "$ips" },
  { $project: { fecha_hora: 1, puntaje_total: 1, canal: 1, "paciente.nombres": 1, "paciente.apellidos": 1, "paciente.telefono": 1, "paciente.eps.nombre": 1, "ips.nombre": 1, "ips.ciudad": 1 } }
])

 Consulta 2: Urgentes de régimen subsidiado 
¿Cuáles son los casos urgentes más graves de pacientes del régimen subsidiado?

db.triajes.aggregate([
  { $match: { nivel_asignado: 3 } },
  { $lookup: { from: "pacientes", localField: "paciente_id", foreignField: "_id", as: "paciente" } },
  { $unwind: "$paciente" },
  { $match: { "paciente.eps.regimen": "Subsidiado" } },
  { $sort: { puntaje_total: -1 } },
  { $limit: 10 },
  { $project: { fecha_hora: 1, puntaje_total: 1, "atencion.resultado": 1, "paciente.nombres": 1, "paciente.apellidos": 1, "paciente.ciudad": 1, "paciente.eps.nombre": 1 } }
])

Consulta 3: Síntomas críticos con alta intensidad 
¿Qué síntomas de máxima alerta se reportan con más intensidad en los casos urgentes?

db.triajes.aggregate([
  { $match: { nivel_asignado: 3 } },
  { $unwind: "$sintomas" },
  { $match: { "sintomas.nivel_alerta": 3, "sintomas.intensidad": { $gte: 9 } } },
  { $sort: { "sintomas.intensidad": -1, "sintomas.duracion_horas": -1 } },
  { $limit: 15 },
  { $project: { fecha_hora: 1, "sintomas.nombre": 1, "sintomas.categoria": 1, "sintomas.intensidad": 1, "sintomas.duracion_horas": 1 } }
])

Consulta 4: Historial de un paciente 
¿Cuál es el historial completo de triajes de un paciente (por ejemplo, el paciente 152)?
db.triajes.aggregate([
  { $match: { paciente_id: 152 } },
  { $sort: { fecha_hora: 1 } },
  { $lookup: { from: "ips", localField: "ips_id", foreignField: "_id", as: "ips" } },
  { $unwind: "$ips" },
  { $project: { fecha_hora: 1, canal: 1, nivel_asignado: 1, puntaje_total: 1, "sintomas.nombre": 1, "sintomas.intensidad": 1, "ips.nombre": 1, "atencion.resultado": 1, "atencion.diagnostico.descripcion": 1 } }
])

Consulta 5: Hospitalizaciones con médico y especialidad 
¿Qué médicos, especialidades y sedes están detrás de las hospitalizaciones más recientes?

db.triajes.aggregate([
  { $match: { "atencion.resultado": "Hospitalizacion" } },
  { $sort: { fecha_hora: -1 } },
  { $limit: 20 },
  { $lookup: { from: "medicos", localField: "atencion.medico_id", foreignField: "_id", as: "medico" } },
  { $lookup: { from: "ips", localField: "ips_id", foreignField: "_id", as: "ips" } },
  { $unwind: "$medico" },
  { $unwind: "$ips" },
  { $project: { fecha_hora: 1, nivel_asignado: 1, "atencion.diagnostico.descripcion": 1, "medico.nombres": 1, "medico.apellidos": 1, "medico.especialidad.nombre": 1, "ips.nombre": 1 } }
])

Consulta 6: Posibles casos subclasificados 
¿Qué triajes de nivel 2 (media) terminaron en hospitalización y tenían un puntaje cercano al umbral de urgencia?

db.triajes.aggregate([
  { $match: { nivel_asignado: 2, "atencion.resultado": "Hospitalizacion" } },
  { $sort: { puntaje_total: -1 } },
  { $limit: 10 },
  { $lookup: { from: "pacientes", localField: "paciente_id", foreignField: "_id", as: "paciente" } },
  { $unwind: "$paciente" },
  { $project: { fecha_hora: 1, puntaje_total: 1, "sintomas.nombre": 1, "sintomas.intensidad": 1, "atencion.diagnostico.descripcion": 1, "paciente.nombres": 1, "paciente.apellidos": 1 } }
])

Consulta 7: Posibles casos sobreclasificados 
¿Qué triajes de nivel 3 (urgente) terminaron en alta y tenían un puntaje apenas por encima del umbral?

db.triajes.aggregate([
  { $match: { nivel_asignado: 3, "atencion.resultado": "Alta" } },
  { $sort: { puntaje_total: 1 } },
  { $limit: 10 },
  { $lookup: { from: "ips", localField: "ips_id", foreignField: "_id", as: "ips" } },
  { $unwind: "$ips" },
  { $project: { fecha_hora: 1, puntaje_total: 1, "sintomas.nombre": 1, "sintomas.intensidad": 1, "atencion.diagnostico.descripcion": 1, "ips.nombre": 1 } }
])

Consulta 8: Informe completo de auditoría (múltiples $lookup) 
¿Cómo se ve el recorrido completo de los casos urgentes atendidos: paciente, sede, médico y diagnóstico?

db.triajes.aggregate([
  { $match: { nivel_asignado: 3, atencion: { $exists: true } } },
  { $sort: { fecha_hora: -1 } },
  { $limit: 10 },
  { $lookup: { from: "pacientes", localField: "paciente_id", foreignField: "_id", as: "paciente" } },
  { $lookup: { from: "ips", localField: "ips_id", foreignField: "_id", as: "ips" } },
  { $lookup: { from: "medicos", localField: "atencion.medico_id", foreignField: "_id", as: "medico" } },
  { $unwind: "$paciente" },
  { $unwind: "$ips" },
  { $unwind: "$medico" },
  { $project: { fecha_hora: 1, puntaje_total: 1, canal: 1, "paciente.nombres": 1, "paciente.apellidos": 1, "paciente.eps.nombre": 1, "ips.nombre": 1, "ips.ciudad": 1, "medico.nombres": 1, "medico.apellidos": 1, "medico.especialidad.nombre": 1, "atencion.fecha_hora_inicio": 1, "atencion.resultado": 1, "atencion.diagnostico.codigo_cie10": 1, "atencion.diagnostico.descripcion": 1 } }
])
