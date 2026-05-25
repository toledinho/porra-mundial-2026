"""
Script para migrar la base de datos SQLite local a Turso
"""
import sqlite3
import os

# Importar el módulo de database configurado para Turso
os.environ["USE_TURSO"] = "true"
from database import get_conn as get_turso_conn

def migrar_datos():
    """Migra todos los datos de SQLite local a Turso"""

    # Conectar a SQLite local
    conn_local = sqlite3.connect('porra_mundial_2026.db')
    cursor_local = conn_local.cursor()

    # Conectar a Turso
    conn_turso = get_turso_conn()
    cursor_turso = conn_turso.cursor()

    print("🚀 Iniciando migración a Turso...")

    # 1. Crear tablas en Turso
    print("\n📋 Creando estructura de tablas...")

    tablas = [
        '''CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            email TEXT,
            fecha_registro TEXT,
            activo INTEGER DEFAULT 1
        )''',
        '''CREATE TABLE IF NOT EXISTS jornadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL,
            nombre TEXT,
            es_estrella INTEGER DEFAULT 0,
            fecha TEXT,
            fase TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jornada_id INTEGER,
            numero_partido INTEGER,
            nombre TEXT,
            resultado_real TEXT,
            es_doble INTEGER DEFAULT 0,
            FOREIGN KEY (jornada_id) REFERENCES jornadas (id)
        )''',
        '''CREATE TABLE IF NOT EXISTS pronosticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_id INTEGER,
            participante TEXT,
            prediccion TEXT,
            puntos INTEGER,
            FOREIGN KEY (partido_id) REFERENCES partidos (id)
        )'''
    ]

    for tabla in tablas:
        cursor_turso.execute(tabla)

    conn_turso.commit()
    print("✅ Tablas creadas")

    # 2. Migrar usuarios
    print("\n👥 Migrando usuarios...")
    cursor_local.execute("SELECT * FROM usuarios")
    usuarios = cursor_local.fetchall()

    for usuario in usuarios:
        try:
            cursor_turso.execute(
                "INSERT INTO usuarios (id, nombre, email, fecha_registro, activo) VALUES (?, ?, ?, ?, ?)",
                usuario
            )
        except Exception as e:
            print(f"  ⚠️ Usuario {usuario[1]} ya existe, saltando...")

    conn_turso.commit()
    print(f"✅ {len(usuarios)} usuarios migrados")

    # 3. Migrar jornadas
    print("\n📅 Migrando jornadas...")
    cursor_local.execute("SELECT * FROM jornadas")
    jornadas = cursor_local.fetchall()

    for jornada in jornadas:
        try:
            cursor_turso.execute(
                "INSERT INTO jornadas (id, numero, nombre, es_estrella, fecha, fase) VALUES (?, ?, ?, ?, ?, ?)",
                jornada
            )
        except Exception as e:
            print(f"  ⚠️ Jornada {jornada[2]} ya existe, saltando...")

    conn_turso.commit()
    print(f"✅ {len(jornadas)} jornadas migradas")

    # 4. Migrar partidos
    print("\n⚽ Migrando partidos...")
    cursor_local.execute("SELECT * FROM partidos")
    partidos = cursor_local.fetchall()

    for partido in partidos:
        try:
            cursor_turso.execute(
                "INSERT INTO partidos (id, jornada_id, numero_partido, nombre, resultado_real, es_doble) VALUES (?, ?, ?, ?, ?, ?)",
                partido
            )
        except Exception as e:
            print(f"  ⚠️ Error migrando partido: {e}")

    conn_turso.commit()
    print(f"✅ {len(partidos)} partidos migrados")

    # 5. Migrar pronósticos
    print("\n📝 Migrando pronósticos...")
    cursor_local.execute("SELECT * FROM pronosticos")
    pronosticos = cursor_local.fetchall()

    for pronostico in pronosticos:
        try:
            cursor_turso.execute(
                "INSERT INTO pronosticos (id, partido_id, participante, prediccion, puntos) VALUES (?, ?, ?, ?, ?)",
                pronostico
            )
        except Exception as e:
            print(f"  ⚠️ Error migrando pronóstico: {e}")

    conn_turso.commit()
    print(f"✅ {len(pronosticos)} pronósticos migrados")

    # Cerrar conexiones
    conn_local.close()
    conn_turso.close()

    print("\n🎉 ¡Migración completada con éxito!")
    print("\n📊 Resumen:")
    print(f"  - Usuarios: {len(usuarios)}")
    print(f"  - Jornadas: {len(jornadas)}")
    print(f"  - Partidos: {len(partidos)}")
    print(f"  - Pronósticos: {len(pronosticos)}")

if __name__ == "__main__":
    migrar_datos()
