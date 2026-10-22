IF DB_ID('TriajeIPS') IS NULL
    CREATE DATABASE TriajeIPS;
GO

USE TriajeIPS;
GO

-- Borra las tablas si ya existían (primero las que dependen de otras)
DROP TABLE IF EXISTS Atencion;
DROP TABLE IF EXISTS Triaje_Sintoma;
DROP TABLE IF EXISTS Triaje;
DROP TABLE IF EXISTS Medico;
DROP TABLE IF EXISTS Paciente;
DROP TABLE IF EXISTS Diagnostico;
DROP TABLE IF EXISTS Sintoma;
DROP TABLE IF EXISTS Especialidad;
DROP TABLE IF EXISTS IPS;
DROP TABLE IF EXISTS EPS;
GO

-- ===== Catálogos (tablas pequeñas que no dependen de otras) =====

CREATE TABLE EPS (
    id_eps   INT IDENTITY(1,1) PRIMARY KEY,
    nombre   NVARCHAR(100) NOT NULL,
    nit      VARCHAR(20)   NOT NULL UNIQUE,
    regimen  NVARCHAR(20)  NOT NULL CHECK (regimen IN ('Contributivo', 'Subsidiado'))
);

CREATE TABLE IPS (
    id_ips              INT IDENTITY(1,1) PRIMARY KEY,
    nombre              NVARCHAR(100) NOT NULL,
    ciudad              NVARCHAR(60)  NOT NULL,
    direccion           NVARCHAR(150) NOT NULL,
    nivel_complejidad   TINYINT       NOT NULL CHECK (nivel_complejidad BETWEEN 1 AND 3),
    capacidad_urgencias INT           NOT NULL CHECK (capacidad_urgencias > 0)
);

CREATE TABLE Especialidad (
    id_especialidad INT IDENTITY(1,1) PRIMARY KEY,
    nombre          NVARCHAR(80) NOT NULL UNIQUE
);

CREATE TABLE Sintoma (
    id_sintoma   INT IDENTITY(1,1) PRIMARY KEY,
    nombre       NVARCHAR(80) NOT NULL UNIQUE,
    categoria    NVARCHAR(50) NOT NULL,
    nivel_alerta TINYINT      NOT NULL CHECK (nivel_alerta BETWEEN 1 AND 3)  -- gravedad base del síntoma
);

CREATE TABLE Diagnostico (
    id_diagnostico  INT IDENTITY(1,1) PRIMARY KEY,
    codigo_cie10    VARCHAR(10)   NOT NULL UNIQUE,
    descripcion     NVARCHAR(200) NOT NULL,
    id_especialidad INT           NOT NULL REFERENCES Especialidad(id_especialidad)
);

-- ===== Personas =====

CREATE TABLE Paciente (
    id_paciente      INT IDENTITY(1,1) PRIMARY KEY,
    tipo_documento   VARCHAR(5)   NOT NULL CHECK (tipo_documento IN ('CC', 'TI', 'RC', 'CE')),
    numero_documento VARCHAR(20)  NOT NULL,
    nombres          NVARCHAR(80) NOT NULL,
    apellidos        NVARCHAR(80) NOT NULL,
    fecha_nacimiento DATE         NOT NULL,
    sexo             CHAR(1)      NOT NULL CHECK (sexo IN ('F', 'M')),
    telefono         VARCHAR(20)  NULL,
    ciudad           NVARCHAR(60) NOT NULL,
    id_eps           INT          NOT NULL REFERENCES EPS(id_eps),
    UNIQUE (tipo_documento, numero_documento)
);

CREATE TABLE Medico (
    id_medico       INT IDENTITY(1,1) PRIMARY KEY,
    nombres         NVARCHAR(80) NOT NULL,
    apellidos       NVARCHAR(80) NOT NULL,
    registro_medico VARCHAR(20)  NOT NULL UNIQUE,
    id_especialidad INT          NOT NULL REFERENCES Especialidad(id_especialidad),
    id_ips          INT          NOT NULL REFERENCES IPS(id_ips)
);

-- ===== Proceso de triaje y atención =====

CREATE TABLE Triaje (
    id_triaje      INT IDENTITY(1,1) PRIMARY KEY,
    id_paciente    INT          NOT NULL REFERENCES Paciente(id_paciente),
    id_ips         INT          NOT NULL REFERENCES IPS(id_ips),
    fecha_hora     DATETIME     NOT NULL,
    canal          NVARCHAR(20) NOT NULL CHECK (canal IN ('Cuestionario', 'Chatbot')),
    nivel_asignado TINYINT      NOT NULL CHECK (nivel_asignado BETWEEN 1 AND 3),  -- 1 normal, 2 media, 3 urgente
    puntaje_total  INT          NOT NULL CHECK (puntaje_total >= 0)
);

-- Detalle del triaje: los síntomas reportados en cada valoración (relación muchos a muchos)
CREATE TABLE Triaje_Sintoma (
    id_triaje_sintoma INT IDENTITY(1,1) PRIMARY KEY,
    id_triaje         INT     NOT NULL REFERENCES Triaje(id_triaje),
    id_sintoma        INT     NOT NULL REFERENCES Sintoma(id_sintoma),
    intensidad        TINYINT NOT NULL CHECK (intensidad BETWEEN 1 AND 10),
    duracion_horas    INT     NOT NULL CHECK (duracion_horas >= 0),
    UNIQUE (id_triaje, id_sintoma)  -- un síntoma no se repite dentro del mismo triaje
);

-- Cada triaje tiene como máximo una atención
CREATE TABLE Atencion (
    id_atencion       INT IDENTITY(1,1) PRIMARY KEY,
    id_triaje         INT          NOT NULL REFERENCES Triaje(id_triaje),
    id_medico         INT          NOT NULL REFERENCES Medico(id_medico),
    id_diagnostico    INT          NOT NULL REFERENCES Diagnostico(id_diagnostico),
    fecha_hora_inicio DATETIME     NOT NULL,  -- la espera = fecha_hora_inicio - Triaje.fecha_hora
    duracion_minutos  INT          NOT NULL CHECK (duracion_minutos > 0),
    resultado         NVARCHAR(30) NOT NULL
        CHECK (resultado IN ('Alta', 'Observacion', 'Hospitalizacion', 'Remision')),
    UNIQUE (id_triaje)  -- relación 0..1: un triaje no puede tener dos atenciones
);
GO
