"""
Script para recrear las tablas en Turso con las columnas correctas
"""
import os
os.environ['USE_TURSO'] = 'true'

from database import get_conn

print("=" * 60)
print("RECREAR TABLAS EN TURSO")
print("=" * 60)
print("\n⚠️  ADVERTENCIA: Esto eliminará TODOS los datos en Turso")

respuesta = input("\n¿Continuar? (escribe 'SI' para confirmar): ")

if respuesta.upper() != "SI":
    print("❌ Operación cancelada")
    exit()

conn = get_conn()
c = conn.cursor()

try:
    print("\n🗑️  Eliminando tablas existentes...")

    # Eliminar tablas en orden (por foreign keys)
    c.execute("DROP TABLE IF EXISTS pronosticos")
    print("   ✅ pronosticos eliminada")

    c.execute("DROP TABLE IF EXISTS partidos")
    print("   ✅ partidos eliminada")

    c.execute("DROP TABLE IF EXISTS jornadas")
    print("   ✅ jornadas eliminada")

    c.execute("DROP TABLE IF EXISTS usuarios")
    print("   ✅ usuarios eliminada")

    conn.commit()

    print("\n📋 Creando tablas nuevas...")

    # Crear tabla usuarios
    c.execute('''CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        email TEXT,
        fecha_registro TEXT,
        activo INTEGER DEFAULT 1
    )''')
    print("   ✅ usuarios creada")

    # Crear tabla jornadas
    c.execute('''CREATE TABLE jornadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER NOT NULL,
        nombre TEXT,
        es_estrella INTEGER DEFAULT 0,
        fecha TEXT,
        fase TEXT,
        estado_pronosticos TEXT DEFAULT 'cerrada'
    )''')
    print("   ✅ jornadas creada")

    # Crear tabla partidos
    c.execute('''CREATE TABLE partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jornada_id INTEGER,
        numero_partido INTEGER,
        nombre TEXT,
        resultado_real TEXT,
        es_doble INTEGER DEFAULT 0,
        FOREIGN KEY (jornada_id) REFERENCES jornadas (id)
    )''')
    print("   ✅ partidos creada")

    # Crear tabla pronosticos
    c.execute('''CREATE TABLE pronosticos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partido_id INTEGER,
        participante TEXT,
        prediccion TEXT,
        puntos INTEGER,
        FOREIGN KEY (partido_id) REFERENCES partidos (id)
    )''')
    print("   ✅ pronosticos creada")

    conn.commit()

    print("\n" + "=" * 60)
    print("✅ TABLAS RECREADAS EXITOSAMENTE")
    print("=" * 60)
    print("\nAhora puedes:")
    print("  1. Recargar tu app en Streamlit Cloud")
    print("  2. Subir el CSV de usuarios (usuarios_para_cargar.csv)")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
