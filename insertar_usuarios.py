"""
Script para insertar usuarios en Turso
"""
import os
os.environ['USE_TURSO'] = 'true'

from database import get_conn
from datetime import datetime

usuarios = [
    "TOLEDINHO",
    "MARGAFLOWER",
    "YORYO",
    "SANDRA YORYO",
    "PIRATA",
    "VALLES",
    "CRISTIAN",
    "PITU",
    "YAREMA",
    "FRANCIS PITU",
    "PIRULO",
    "MIGUEL COLORAO",
    "VEGALILEO",
    "TUTIO",
    "MASON",
    "SAMU RETOLD FC",
    "KIKO",
    "ANA KIKO",
    "OMINAS SCARIOLO",
    "BICHO",
    "FERNANDO DAMIÁN",
    "MUITO",
    "ÁLVARO",
    "VIRGINIA (ÁLVARO)",
    "ALI ALBIACH",
    "JUANCA",
    "SEÑOR PATO",
    "PATITO YEDRA",
    "PELI PATO",
    "ANTONIO CASTAÑO",
    "FRANCISCO ARMARIO",
    "JOSÉ CASTAÑO",
    "CRISTÓFORO COLOMBO",
    "CONCHI ROBALO",
    "NOLY",
    "BOLO",
    "RUZ",
    "ANA ROBALO",
    "TERESA ROBALO",
    "PAULA ROBALO",
    "JUAN ROBALO",
    "SANTI ROBALO",
    "BALDO ROBALO",
    "SANTI ALBIACH",
    "PACO MACOY",
    "MANU VIÑAS",
    "LOURDES VIÑAS",
    "LUCATONI",
    "PEPE SÁNCHEZ",
    "JUANLU",
    "GUILLE",
    "JENNY",
    "ÁSPERA",
    "POMARE",
    "JUANMA MACÍAS",
    "LIDIA",
    "ANTONIO ARMARIO",
    "JONI"
]

print("=" * 60)
print(f"INSERTANDO {len(usuarios)} USUARIOS EN TURSO")
print("=" * 60)

conn = get_conn()
c = conn.cursor()

fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
insertados = 0
ya_existian = 0

for nombre in usuarios:
    nombre_mayus = nombre.upper().strip()

    # Verificar si ya existe
    c.execute("SELECT id FROM usuarios WHERE LOWER(nombre) = LOWER(?)", (nombre_mayus,))
    existe = c.fetchone()

    if not existe:
        c.execute(
            "INSERT INTO usuarios (nombre, email, fecha_registro, activo) VALUES (?, ?, ?, ?)",
            (nombre_mayus, None, fecha_registro, 1)
        )
        print(f"✅ {nombre_mayus}")
        insertados += 1
    else:
        print(f"⏭️  {nombre_mayus} (ya existe)")
        ya_existian += 1

conn.commit()
conn.close()

print("\n" + "=" * 60)
print(f"✅ COMPLETADO")
print("=" * 60)
print(f"  Insertados: {insertados}")
print(f"  Ya existían: {ya_existian}")
print(f"  Total: {len(usuarios)}")
