"""
Script para migrar datos de SQLite local a Turso
"""
import sqlite3
import sys

# Configurar para usar Turso
import os
os.environ['USE_TURSO'] = 'true'

# Importar después de configurar la variable
from database import get_conn as get_turso_conn

def migrar_datos():
    print("=" * 60)
    print("MIGRACIÓN DE SQLITE LOCAL A TURSO")
    print("=" * 60)

    # Conectar a SQLite local
    print("\n📂 Conectando a SQLite local...")
    sqlite_conn = sqlite3.connect("porra_mundial_2026.db")
    sqlite_cursor = sqlite_conn.cursor()

    # Conectar a Turso
    print("☁️  Conectando a Turso...")
    turso_conn = get_turso_conn()
    turso_cursor = turso_conn.cursor()

    try:
        # Migrar USUARIOS
        print("\n👥 Migrando usuarios...")
        sqlite_cursor.execute("SELECT * FROM usuarios")
        usuarios = sqlite_cursor.fetchall()

        print(f"   Encontrados {len(usuarios)} usuarios en SQLite local")

        for usuario in usuarios:
            # Verificar si ya existe
            turso_cursor.execute(
                "SELECT id FROM usuarios WHERE LOWER(nombre) = LOWER(?)",
                (usuario[1],)  # usuario[1] es el nombre
            )
            existe = turso_cursor.fetchone()

            if not existe:
                turso_cursor.execute(
                    "INSERT INTO usuarios (nombre, email, fecha_registro, activo) VALUES (?, ?, ?, ?)",
                    (usuario[1], usuario[2], usuario[3], usuario[4])
                )
                print(f"   ✅ {usuario[1]}")
            else:
                print(f"   ⏭️  {usuario[1]} (ya existe)")

        turso_conn.commit()

        # Migrar JORNADAS
        print("\n📅 Migrando jornadas...")
        sqlite_cursor.execute("SELECT * FROM jornadas")
        jornadas = sqlite_cursor.fetchall()

        print(f"   Encontradas {len(jornadas)} jornadas en SQLite local")

        jornada_id_map = {}  # Mapeo de IDs antiguos a nuevos

        for jornada in jornadas:
            # jornada = (id, numero, nombre, es_estrella, fecha, fase, estado_pronosticos)
            old_id = jornada[0]

            # Verificar si ya existe
            turso_cursor.execute(
                "SELECT id FROM jornadas WHERE numero = ?",
                (jornada[1],)
            )
            existe = turso_cursor.fetchone()

            if not existe:
                # Obtener estado_pronosticos si existe (puede no existir en tablas antiguas)
                estado = jornada[6] if len(jornada) > 6 else 'cerrada'

                turso_cursor.execute(
                    "INSERT INTO jornadas (numero, nombre, es_estrella, fecha, fase, estado_pronosticos) VALUES (?, ?, ?, ?, ?, ?)",
                    (jornada[1], jornada[2], jornada[3], jornada[4], jornada[5], estado)
                )
                new_id = turso_cursor.lastrowid
                jornada_id_map[old_id] = new_id
                print(f"   ✅ Jornada {jornada[1]}: {jornada[2]}")
            else:
                jornada_id_map[old_id] = existe[0]
                print(f"   ⏭️  Jornada {jornada[1]} (ya existe)")

        turso_conn.commit()

        # Migrar PARTIDOS
        print("\n⚽ Migrando partidos...")
        sqlite_cursor.execute("SELECT * FROM partidos")
        partidos = sqlite_cursor.fetchall()

        print(f"   Encontrados {len(partidos)} partidos en SQLite local")

        partido_id_map = {}

        for partido in partidos:
            # partido = (id, jornada_id, numero_partido, nombre, resultado_real, es_doble)
            old_id = partido[0]
            old_jornada_id = partido[1]
            new_jornada_id = jornada_id_map.get(old_jornada_id)

            if new_jornada_id:
                turso_cursor.execute(
                    "INSERT INTO partidos (jornada_id, numero_partido, nombre, resultado_real, es_doble) VALUES (?, ?, ?, ?, ?)",
                    (new_jornada_id, partido[2], partido[3], partido[4], partido[5])
                )
                new_id = turso_cursor.lastrowid
                partido_id_map[old_id] = new_id
                print(f"   ✅ Partido {partido[2]}: {partido[3]}")

        turso_conn.commit()

        # Migrar PRONÓSTICOS
        print("\n🎯 Migrando pronósticos...")
        sqlite_cursor.execute("SELECT * FROM pronosticos")
        pronosticos = sqlite_cursor.fetchall()

        print(f"   Encontrados {len(pronosticos)} pronósticos en SQLite local")

        for pronostico in pronosticos:
            # pronostico = (id, partido_id, participante, prediccion, puntos)
            old_partido_id = pronostico[1]
            new_partido_id = partido_id_map.get(old_partido_id)

            if new_partido_id:
                turso_cursor.execute(
                    "INSERT INTO pronosticos (partido_id, participante, prediccion, puntos) VALUES (?, ?, ?, ?)",
                    (new_partido_id, pronostico[2], pronostico[3], pronostico[4])
                )

        turso_conn.commit()
        print(f"   ✅ {len(pronosticos)} pronósticos migrados")

        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("\nResumen:")
        print(f"  👥 Usuarios: {len(usuarios)}")
        print(f"  📅 Jornadas: {len(jornadas)}")
        print(f"  ⚽ Partidos: {len(partidos)}")
        print(f"  🎯 Pronósticos: {len(pronosticos)}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sqlite_conn.close()
        turso_conn.close()

    return True

if __name__ == "__main__":
    print("\n⚠️  ADVERTENCIA: Este script migrará todos los datos de SQLite local a Turso")
    print("Si ya tienes datos en Turso, pueden duplicarse.")

    respuesta = input("\n¿Continuar? (escribe 'SI' para confirmar): ")

    if respuesta.upper() == "SI":
        success = migrar_datos()
        if success:
            print("\n🎉 Ahora puedes usar tu app con todos los datos en Turso (persistente)")
        else:
            print("\n❌ La migración falló. Revisa los errores arriba.")
    else:
        print("\n❌ Migración cancelada")
