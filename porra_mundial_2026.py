import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import io
import base64
from database import get_conn

# Lista oficial de selecciones participantes en el Mundial 2026 (48 equipos)
SELECCIONES_MUNDIAL_2026 = [
    "Alemania", "Arabia Saudita", "Argelia", "Argentina", "Australia",
    "Austria", "Bélgica", "Bosnia y Herzegovina", "Brasil", "Cabo Verde",
    "Canadá", "Catar", "Colombia", "Corea del Sur", "Costa de Marfil",
    "Croacia", "Curazao", "Ecuador", "Egipto", "Escocia",
    "España", "Estados Unidos", "Francia", "Ghana", "Haití",
    "Inglaterra", "Irak", "Irán", "Japón", "Jordania",
    "Marruecos", "México", "Noruega", "Nueva Zelanda", "Países Bajos",
    "Panamá", "Paraguay", "Portugal", "República Checa", "República Democrática del Congo",
    "Senegal", "Sudáfrica", "Suecia", "Suiza", "Túnez",
    "Turquía", "Uruguay", "Uzbekistán"
]

# Configuración de la página
st.set_page_config(
    page_title="Porra Mundial 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Función para convertir imagen a base64
def get_base64_image(image_path):
    """Convierte una imagen a base64 para incrustarla en HTML"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Sistema de puntuación Mundial 2026
def calcular_puntos(prediccion, resultado_real):
    """
    Sistema de puntuación:
    - 12 puntos: Resultado exacto con diferencia de goles > 1
    - 10 puntos: Resultado exacto con diferencia de goles = 1 o empate
    - 6 puntos: Ganador correcto + diferencia correcta (O empate sin resultado exacto - NUEVO)
    - 4 puntos: Ganador correcto pero diferencia incorrecta
    - 0 puntos: Ganador incorrecto
    """
    if prediccion is None or prediccion == "" or pd.isna(prediccion):
        return 0

    try:
        pred_local, pred_visitante = map(int, str(prediccion).split('-'))
        real_local, real_visitante = map(int, str(resultado_real).split('-'))
    except:
        return 0

    # Resultado exacto
    if pred_local == real_local and pred_visitante == real_visitante:
        dif_goles = abs(real_local - real_visitante)
        if dif_goles > 1:
            return 12
        else:
            return 10

    # Determinar ganadores
    if pred_local > pred_visitante:
        resultado_previsto = 'local'
    elif pred_local < pred_visitante:
        resultado_previsto = 'visitante'
    else:
        resultado_previsto = 'empate'

    if real_local > real_visitante:
        resultado_real_ganador = 'local'
    elif real_local < real_visitante:
        resultado_real_ganador = 'visitante'
    else:
        resultado_real_ganador = 'empate'

    # NUEVO: Si acertó empate (pero no resultado exacto) = 6 puntos
    if resultado_previsto == 'empate' and resultado_real_ganador == 'empate':
        return 6

    # Ganador correcto
    if resultado_previsto == resultado_real_ganador:
        dif_prevista = pred_local - pred_visitante
        dif_real = real_local - real_visitante

        if dif_prevista == dif_real:
            return 6
        else:
            return 4

    return 0

# Funciones de base de datos
def init_db():
    """Inicializa la base de datos"""
    conn = get_conn()
    c = conn.cursor()

    # Tabla de usuarios/participantes
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        email TEXT,
        fecha_registro TEXT,
        activo INTEGER DEFAULT 1
    )''')

    # Migración: Añadir columna activo si no existe (para bases de datos antiguas)
    try:
        c.execute("SELECT activo FROM usuarios LIMIT 1")
    except:
        c.execute("ALTER TABLE usuarios ADD COLUMN activo INTEGER DEFAULT 1")
        conn.commit()

    # Tabla de jornadas
    c.execute('''CREATE TABLE IF NOT EXISTS jornadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER NOT NULL,
        nombre TEXT,
        es_estrella INTEGER DEFAULT 0,
        fecha TEXT,
        fase TEXT,
        estado_pronosticos TEXT DEFAULT 'cerrada',
        fecha_fin TEXT
    )''')

    # Migración: Añadir columna estado_pronosticos si no existe (para bases de datos antiguas)
    try:
        c.execute("SELECT estado_pronosticos FROM jornadas LIMIT 1")
    except:
        c.execute("ALTER TABLE jornadas ADD COLUMN estado_pronosticos TEXT DEFAULT 'cerrada'")
        conn.commit()

    # Migración: Añadir columna fecha_fin si no existe
    try:
        c.execute("SELECT fecha_fin FROM jornadas LIMIT 1")
    except:
        c.execute("ALTER TABLE jornadas ADD COLUMN fecha_fin TEXT")
        conn.commit()

    # Tabla de partidos
    c.execute('''CREATE TABLE IF NOT EXISTS partidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jornada_id INTEGER,
        numero_partido INTEGER,
        nombre TEXT,
        resultado_real TEXT,
        es_doble INTEGER DEFAULT 0,
        FOREIGN KEY (jornada_id) REFERENCES jornadas (id)
    )''')

    # Tabla de pronósticos
    c.execute('''CREATE TABLE IF NOT EXISTS pronosticos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partido_id INTEGER,
        participante TEXT,
        prediccion TEXT,
        puntos INTEGER,
        FOREIGN KEY (partido_id) REFERENCES partidos (id)
    )''')

    conn.commit()
    conn.close()

# La función get_conn() ahora viene del módulo database.py

# Funciones de gestión de usuarios
def crear_usuario(nombre, email=""):
    """Crea un nuevo usuario"""
    try:
        conn = get_conn()
        c = conn.cursor()

        # Verificar si ya existe un usuario con ese nombre (case-insensitive)
        c.execute("SELECT COUNT(*) FROM usuarios WHERE LOWER(nombre) = LOWER(?)", (nombre,))
        if c.fetchone()[0] > 0:
            conn.close()
            return False, "El usuario ya existe (no se distingue entre mayúsculas/minúsculas)"

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO usuarios (nombre, email, fecha_registro, activo) VALUES (?, ?, ?, 1)",
                  (nombre, email, fecha))
        conn.commit()
        conn.close()
        return True, "Usuario creado correctamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def eliminar_usuario(nombre):
    """Elimina un usuario (marca como inactivo)"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET activo = 0 WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()
    return True

def reactivar_usuario(nombre):
    """Reactiva un usuario"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET activo = 1 WHERE nombre = ?", (nombre,))
    conn.commit()
    conn.close()
    return True

def actualizar_nombre_usuario(nombre_anterior, nombre_nuevo):
    """Actualiza el nombre de un usuario en todas las tablas"""
    try:
        conn = get_conn()
        c = conn.cursor()

        # Verificar que el nuevo nombre no existe ya (case-insensitive)
        c.execute("SELECT COUNT(*) FROM usuarios WHERE LOWER(nombre) = LOWER(?) AND LOWER(nombre) != LOWER(?)",
                  (nombre_nuevo, nombre_anterior))
        if c.fetchone()[0] > 0:
            conn.close()
            return False, "El nuevo nombre ya está en uso por otro usuario (no se distingue entre mayúsculas/minúsculas)"

        # Actualizar en tabla usuarios
        c.execute("UPDATE usuarios SET nombre = ? WHERE nombre = ?", (nombre_nuevo, nombre_anterior))

        # Actualizar en tabla pronósticos
        c.execute("UPDATE pronosticos SET participante = ? WHERE participante = ?", (nombre_nuevo, nombre_anterior))

        conn.commit()
        conn.close()
        return True, "Nombre actualizado correctamente en todos los registros"
    except Exception as e:
        return False, f"Error al actualizar: {str(e)}"

def get_usuarios(solo_activos=True):
    """Obtiene la lista de usuarios"""
    conn = get_conn()
    if solo_activos:
        df = pd.read_sql_query("SELECT * FROM usuarios WHERE activo = 1 ORDER BY nombre", conn)
    else:
        df = pd.read_sql_query("SELECT * FROM usuarios ORDER BY activo DESC, nombre", conn)
    conn.close()
    return df

def verificar_usuario_existe(nombre):
    """Verifica si un usuario existe y está activo (case-insensitive)"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usuarios WHERE LOWER(nombre) = LOWER(?) AND activo = 1", (nombre,))
    existe = c.fetchone()[0] > 0
    conn.close()
    return existe

def obtener_nombre_correcto_usuario(nombre):
    """Obtiene el nombre correcto del usuario desde la BD (case-insensitive)"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT nombre FROM usuarios WHERE LOWER(nombre) = LOWER(?) AND activo = 1", (nombre,))
    resultado = c.fetchone()
    conn.close()
    return resultado[0] if resultado else None

def cargar_usuarios_desde_archivo(archivo):
    """Carga múltiples usuarios desde un archivo"""
    try:
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)

        usuarios_creados = 0
        usuarios_existentes = 0

        # Buscar columna de nombres
        columna_nombre = None
        for col in df.columns:
            if 'nombre' in col.lower() or 'participante' in col.lower():
                columna_nombre = col
                break

        if columna_nombre is None:
            columna_nombre = df.columns[0]

        for _, row in df.iterrows():
            nombre = row[columna_nombre]
            if pd.notna(nombre) and nombre != '':
                email = row.get('email', '') or row.get('Email', '') or row.get('EMAIL', '') or ''
                success, _ = crear_usuario(str(nombre).strip(), str(email).strip() if email else '')
                if success:
                    usuarios_creados += 1
                else:
                    usuarios_existentes += 1

        return True, f"✅ {usuarios_creados} usuarios creados. {usuarios_existentes} ya existían."
    except Exception as e:
        return False, f"Error al procesar archivo: {str(e)}"

def crear_jornada(numero, nombre, es_estrella, fase="Fase de Grupos", fecha_fin=None):
    """Crea una nueva jornada"""
    conn = get_conn()
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO jornadas (numero, nombre, es_estrella, fecha, fase, fecha_fin) VALUES (?, ?, ?, ?, ?, ?)",
              (numero, nombre, es_estrella, fecha, fase, fecha_fin))
    jornada_id = c.lastrowid
    conn.commit()
    conn.close()
    return jornada_id

def procesar_archivo_pronosticos(archivo, jornada_id, partidos_ids, partidos_data):
    """Procesa solo el archivo de pronósticos (los partidos ya están creados)

    Args:
        archivo: Archivo Excel/CSV a procesar
        jornada_id: ID de la jornada
        partidos_ids: Lista de IDs de los partidos creados
        partidos_data: Datos de los partidos con resultados
    """
    try:
        # Leer archivo
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)

        conn = get_conn()
        c = conn.cursor()

        num_partidos = len(partidos_ids)

        # Procesar pronósticos de participantes
        usuarios_no_registrados = []
        pronosticos_procesados = 0

        for idx, row in df.iterrows():
            participante = row.get('Participante') or row.get('participante') or row.iloc[0]
            if pd.isna(participante) or participante == '' or 'Partido' in str(participante):
                continue

            participante = str(participante).strip()

            # Verificar si el usuario existe y obtener el nombre correcto de la BD
            if not verificar_usuario_existe(participante):
                usuarios_no_registrados.append(participante)
                continue

            # Obtener el nombre correcto desde la BD (para mantener consistencia)
            participante_correcto = obtener_nombre_correcto_usuario(participante)
            if not participante_correcto:
                usuarios_no_registrados.append(participante)
                continue

            # Obtener predicciones
            for i in range(num_partidos):
                prediccion = None
                # Buscar predicción en diferentes formatos de columna
                if f'Pred{i+1}' in row:
                    prediccion = row[f'Pred{i+1}']
                elif f'Prediccion{i+1}' in row:
                    prediccion = row[f'Prediccion{i+1}']
                elif f'pred{i+1}' in row:
                    prediccion = row[f'pred{i+1}']
                elif len(row) > i + 1:
                    prediccion = row.iloc[i + 1]

                if prediccion and not pd.isna(prediccion):
                    prediccion = str(prediccion).strip()

                    # Calcular puntos si hay resultado real
                    resultado_real = partidos_data[i]['resultado'].strip() if partidos_data[i]['resultado'].strip() else None
                    puntos = 0
                    if resultado_real:
                        puntos = calcular_puntos(prediccion, resultado_real)
                        # Verificar si este partido puntúa doble
                        if partidos_data[i]['es_doble']:
                            puntos *= 2

                    c.execute("""INSERT INTO pronosticos (partido_id, participante, prediccion, puntos)
                                VALUES (?, ?, ?, ?)""",
                             (partidos_ids[i], participante_correcto, prediccion, puntos))
                    pronosticos_procesados += 1

        conn.commit()
        conn.close()

        mensaje = f"✅ Jornada creada. {pronosticos_procesados} pronósticos procesados."
        if usuarios_no_registrados:
            mensaje += f"\n⚠️ Usuarios no registrados (ignorados): {', '.join(set(usuarios_no_registrados))}"

        return True, mensaje

    except Exception as e:
        return False, f"Error al procesar archivo: {str(e)}"

def procesar_archivo_jornada(archivo, jornada_id, partido_doble=None):
    """Procesa el archivo Excel/CSV con los datos de la jornada

    Args:
        archivo: Archivo Excel/CSV a procesar
        jornada_id: ID de la jornada
        partido_doble: Número del partido que puntúa doble (None si no hay)
    """
    try:
        # Leer archivo
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)

        conn = get_conn()
        c = conn.cursor()

        # Determinar número de partidos desde el archivo
        # Contar columnas que no son 'Participante' y que contienen predicciones
        columnas = df.columns.tolist()

        # Buscar todas las columnas de predicciones (formato: Pred1, Pred2, etc.)
        num_partidos = 0
        for col in columnas:
            if 'pred' in col.lower() or 'prediccion' in col.lower():
                num_partidos += 1

        # Si no encuentra columnas con ese formato, contar columnas después de 'Participante'
        if num_partidos == 0:
            # Buscar índice de columna 'Participante'
            participante_idx = 0
            for i, col in enumerate(columnas):
                if 'participante' in str(col).lower():
                    participante_idx = i
                    break
            num_partidos = len(columnas) - participante_idx - 1

        # Obtener nombres de partidos (primera fila después de columna participante)
        nombres_partidos = []
        resultados_reales = []

        # Buscar columnas de partidos y resultados
        for i in range(num_partidos):
            # Las columnas deberían ser: Participante, Partido1, Resultado1, Partido2, Resultado2, etc.
            # O: Participante, Pred1, Pred2, Pred3... y luego Resultado1, Resultado2...
            if f'Partido{i+1}' in columnas:
                nombres_partidos.append(df[f'Partido{i+1}'].iloc[0] if pd.notna(df[f'Partido{i+1}'].iloc[0]) else f'Partido {i+1}')
                resultados_reales.append(df[f'Resultado{i+1}'].iloc[0] if f'Resultado{i+1}' in columnas else None)
            elif len(columnas) > i + 1:  # Asumiendo formato simple
                nombres_partidos.append(f'Partido {i+1}')
                resultados_reales.append(None)

        # Crear partidos en la BD
        partidos_ids = []
        for i, nombre_partido in enumerate(nombres_partidos):
            # Verificar si este partido es el que puntúa doble
            es_doble = (partido_doble is not None and i + 1 == partido_doble)
            resultado = resultados_reales[i] if i < len(resultados_reales) else None

            c.execute("""INSERT INTO partidos (jornada_id, numero_partido, nombre, resultado_real, es_doble)
                        VALUES (?, ?, ?, ?, ?)""",
                     (jornada_id, i+1, nombre_partido, resultado, es_doble))
            partidos_ids.append(c.lastrowid)

        # Procesar pronósticos de participantes
        usuarios_no_registrados = []
        for idx, row in df.iterrows():
            participante = row.get('Participante') or row.iloc[0]
            if pd.isna(participante) or participante == '' or 'Partido' in str(participante):
                continue

            participante = str(participante).strip()

            # Verificar si el usuario existe y obtener el nombre correcto de la BD
            if not verificar_usuario_existe(participante):
                usuarios_no_registrados.append(participante)
                continue

            # Obtener el nombre correcto desde la BD (para mantener consistencia)
            participante_correcto = obtener_nombre_correcto_usuario(participante)
            if not participante_correcto:
                usuarios_no_registrados.append(participante)
                continue

            # Obtener predicciones
            for i in range(num_partidos):
                prediccion = None
                # Buscar predicción en diferentes formatos de columna
                if f'Pred{i+1}' in row:
                    prediccion = row[f'Pred{i+1}']
                elif f'Prediccion{i+1}' in row:
                    prediccion = row[f'Prediccion{i+1}']
                elif len(row) > i + 1:
                    prediccion = row.iloc[i + 1]

                if prediccion and not pd.isna(prediccion):
                    # Calcular puntos si hay resultado real
                    resultado_real = resultados_reales[i] if i < len(resultados_reales) else None
                    puntos = 0
                    if resultado_real:
                        puntos = calcular_puntos(prediccion, resultado_real)
                        # Verificar si este partido puntúa doble
                        if partido_doble is not None and i + 1 == partido_doble:
                            puntos *= 2

                    c.execute("""INSERT INTO pronosticos (partido_id, participante, prediccion, puntos)
                                VALUES (?, ?, ?, ?)""",
                             (partidos_ids[i], participante_correcto, str(prediccion), puntos))

        conn.commit()
        conn.close()

        if usuarios_no_registrados:
            return True, f"⚠️ Jornada procesada. Usuarios no registrados (ignorados): {', '.join(usuarios_no_registrados)}"

        return True, "✅ Jornada procesada correctamente"

    except Exception as e:
        return False, f"Error al procesar archivo: {str(e)}"

def actualizar_resultados_jornada(jornada_id, resultados):
    """Actualiza los resultados reales y recalcula puntos

    Solo actualiza los partidos que tengan un resultado válido (no vacío).
    Conserva los resultados existentes si no se proporciona uno nuevo.
    """
    conn = get_conn()
    c = conn.cursor()

    try:
        # Actualizar resultados de partidos
        for partido_id, resultado in resultados.items():
            # Limpiar resultado
            resultado_limpio = resultado.strip() if resultado and resultado.strip() else ""

            # Solo actualizar si hay un resultado válido (formato X-X)
            if resultado_limpio and '-' in resultado_limpio:
                c.execute("UPDATE partidos SET resultado_real = ? WHERE id = ?", (resultado_limpio, partido_id))

                # Obtener si es partido doble
                c.execute("SELECT es_doble FROM partidos WHERE id = ?", (partido_id,))
                es_doble = c.fetchone()[0]

                # Recalcular puntos de todos los pronósticos de este partido
                c.execute("SELECT id, prediccion FROM pronosticos WHERE partido_id = ?", (partido_id,))
                pronosticos = c.fetchall()

                for pron_id, prediccion in pronosticos:
                    puntos = calcular_puntos(prediccion, resultado_limpio)
                    if es_doble:
                        puntos *= 2
                    c.execute("UPDATE pronosticos SET puntos = ? WHERE id = ?", (puntos, pron_id))

        conn.commit()
        conn.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        conn.close()
        return False

@st.cache_data(ttl=60)
def get_clasificacion_jornada(jornada_id):
    """Obtiene la clasificación de una jornada específica, incluyendo usuarios sin participar"""
    conn = get_conn()

    # Obtener puntos desglosados de usuarios que participaron
    query = """
        SELECT
            p.participante,
            SUM(p.puntos) as puntos_totales,
            COUNT(CASE
                WHEN (p.puntos IN (10, 12) AND pa.es_doble = 0) OR (p.puntos IN (20, 24) AND pa.es_doble = 1)
                THEN 1
            END) as exactos,
            COUNT(CASE
                WHEN (p.puntos = 6 AND pa.es_doble = 0) OR (p.puntos = 12 AND pa.es_doble = 1)
                THEN 1
            END) as ganador_diferencia,
            COUNT(CASE
                WHEN (p.puntos = 4 AND pa.es_doble = 0) OR (p.puntos = 8 AND pa.es_doble = 1)
                THEN 1
            END) as solo_ganador
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        WHERE pa.jornada_id = ?
        GROUP BY p.participante
        ORDER BY puntos_totales DESC
    """
    df_participantes = pd.read_sql_query(query, conn, params=(jornada_id,))

    # Obtener todos los usuarios activos
    usuarios_activos = pd.read_sql_query("SELECT nombre FROM usuarios WHERE activo = 1", conn)

    conn.close()

    # Crear DataFrame con todos los usuarios
    todos_usuarios = []
    for usuario in usuarios_activos['nombre']:
        if usuario in df_participantes['participante'].values:
            # Usuario participó
            fila = df_participantes[df_participantes['participante'] == usuario].iloc[0]
            todos_usuarios.append({
                'participante': usuario,
                'puntos_totales': fila['puntos_totales'],
                'exactos': fila['exactos'],
                'ganador_diferencia': fila['ganador_diferencia'],
                'solo_ganador': fila['solo_ganador']
            })
        else:
            # Usuario NO participó
            todos_usuarios.append({
                'participante': usuario,
                'puntos_totales': 0,
                'exactos': 0,
                'ganador_diferencia': 0,
                'solo_ganador': 0
            })

    df_final = pd.DataFrame(todos_usuarios)
    # Ordenar por puntos (descendente) y luego alfabéticamente por nombre (ascendente)
    df_final = df_final.sort_values(by=['puntos_totales', 'participante'], ascending=[False, True]).reset_index(drop=True)

    return df_final

@st.cache_data(ttl=60)
def get_clasificacion_general(incluir_deuda=False):
    """Obtiene la clasificación general del torneo

    Args:
        incluir_deuda: Si True, incluye columnas de jornadas sin participar y deuda (solo para admin)
    """
    conn = get_conn()
    query = """
        SELECT
            p.participante,
            SUM(p.puntos) as puntos_totales,
            COUNT(CASE
                WHEN (p.puntos IN (10, 12) AND pa.es_doble = 0) OR (p.puntos IN (20, 24) AND pa.es_doble = 1)
                THEN 1
            END) as exactos,
            COUNT(CASE
                WHEN (p.puntos = 6 AND pa.es_doble = 0) OR (p.puntos = 12 AND pa.es_doble = 1)
                THEN 1
            END) as ganador_diferencia,
            COUNT(CASE
                WHEN (p.puntos = 4 AND pa.es_doble = 0) OR (p.puntos = 8 AND pa.es_doble = 1)
                THEN 1
            END) as solo_ganador,
            COUNT(DISTINCT pa.jornada_id) as jornadas_jugadas
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        GROUP BY p.participante
        ORDER BY puntos_totales DESC
    """
    df = pd.read_sql_query(query, conn)

    # Calcular mejor jornada para cada participante usando CTE
    query_mejor_jornada = """
        WITH puntos_por_jornada AS (
            SELECT
                p.participante,
                pa.jornada_id,
                SUM(p.puntos) as puntos_jornada
            FROM pronosticos p
            INNER JOIN partidos pa ON p.partido_id = pa.id
            GROUP BY p.participante, pa.jornada_id
        )
        SELECT
            participante,
            MAX(puntos_jornada) as mejor_jornada
        FROM puntos_por_jornada
        GROUP BY participante
    """
    df_mejor_jornada = pd.read_sql_query(query_mejor_jornada, conn)

    # Hacer merge con la clasificación general
    df = df.merge(df_mejor_jornada, on='participante', how='left')
    df['mejor_jornada'] = df['mejor_jornada'].fillna(0)

    # Obtener todos los usuarios activos
    usuarios_activos = pd.read_sql_query("SELECT nombre FROM usuarios WHERE activo = 1", conn)

    # Obtener total de jornadas creadas
    jornadas_totales = pd.read_sql_query("SELECT COUNT(*) as total FROM jornadas", conn)['total'].iloc[0]

    # Obtener todas las jornadas con su tipo (normal o estrella)
    jornadas_info = pd.read_sql_query("SELECT id, es_estrella FROM jornadas", conn)

    # Crear DataFrame completo con todos los usuarios
    todos_usuarios = []

    for usuario in usuarios_activos['nombre']:
        if usuario in df['participante'].values:
            # Usuario tiene pronósticos
            fila = df[df['participante'] == usuario].iloc[0]
            datos = {
                'participante': usuario,
                'puntos_totales': fila['puntos_totales'],
                'exactos': fila['exactos'],
                'ganador_diferencia': fila['ganador_diferencia'],
                'solo_ganador': fila['solo_ganador'],
                'jornadas_jugadas': fila['jornadas_jugadas'],
                'mejor_jornada': fila['mejor_jornada']
            }

            if incluir_deuda:
                # Obtener jornadas en las que SÍ participó
                jornadas_participadas = pd.read_sql_query("""
                    SELECT DISTINCT pa.jornada_id
                    FROM pronosticos p
                    INNER JOIN partidos pa ON p.partido_id = pa.id
                    WHERE p.participante = ?
                """, conn, params=(usuario,))

                jornadas_participadas_ids = set(jornadas_participadas['jornada_id'].tolist())

                # Calcular jornadas sin participar
                sin_participar = jornadas_totales - len(jornadas_participadas_ids)
                datos['jornadas_sin_participar'] = sin_participar

                # Calcular deuda
                deuda = 0
                for _, jornada in jornadas_info.iterrows():
                    if jornada['id'] not in jornadas_participadas_ids:
                        if jornada['es_estrella'] == 1:
                            deuda += 2  # Jornada estrella: 2€
                        else:
                            deuda += 1  # Jornada normal: 1€
                datos['debe_euros'] = deuda

        else:
            # Usuario NO tiene ningún pronóstico
            datos = {
                'participante': usuario,
                'puntos_totales': 0,
                'exactos': 0,
                'ganador_diferencia': 0,
                'solo_ganador': 0,
                'jornadas_jugadas': 0,
                'mejor_jornada': 0
            }

            if incluir_deuda:
                datos['jornadas_sin_participar'] = jornadas_totales

                # Calcular deuda total
                deuda = 0
                for _, jornada in jornadas_info.iterrows():
                    if jornada['es_estrella'] == 1:
                        deuda += 2
                    else:
                        deuda += 1
                datos['debe_euros'] = deuda

        todos_usuarios.append(datos)

    conn.close()

    df_final = pd.DataFrame(todos_usuarios)
    # Ordenar por puntos (descendente) y luego alfabéticamente por nombre (ascendente)
    df_final = df_final.sort_values(by=['puntos_totales', 'participante'], ascending=[False, True]).reset_index(drop=True)

    return df_final

@st.cache_data(ttl=60)
def get_jornadas():
    """Obtiene todas las jornadas"""
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM jornadas ORDER BY numero DESC", conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def get_jornada_vigente():
    """Obtiene la jornada vigente: la más reciente que aún no haya pasado su fecha fin"""
    conn = get_conn()
    hoy = datetime.now().strftime("%Y-%m-%d")
    query = """
        SELECT * FROM jornadas
        WHERE fecha_fin IS NOT NULL
        AND date(fecha_fin) >= date(?)
        ORDER BY numero DESC
        LIMIT 1
    """
    df = pd.read_sql_query(query, conn, params=(hoy,))
    conn.close()
    return df.iloc[0] if len(df) > 0 else None

@st.cache_data(ttl=60)
def get_evolucion_puntos():
    """Obtiene la evolución de puntos por jornada de cada participante"""
    conn = get_conn()
    query = """
        SELECT
            j.numero as jornada,
            p.participante,
            SUM(p.puntos) as puntos
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        INNER JOIN jornadas j ON pa.jornada_id = j.id
        GROUP BY j.numero, p.participante
        ORDER BY j.numero, p.participante
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def get_estadisticas_participante(participante):
    """Obtiene estadísticas detalladas de un participante"""
    conn = get_conn()

    # Puntos por jornada
    query_jornadas = """
        SELECT
            j.numero,
            j.nombre,
            SUM(p.puntos) as puntos
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        INNER JOIN jornadas j ON pa.jornada_id = j.id
        WHERE p.participante = ?
        GROUP BY j.id
        ORDER BY j.numero
    """
    df_jornadas = pd.read_sql_query(query_jornadas, conn, params=(participante,))

    # Estadísticas generales
    query_stats = """
        SELECT
            COUNT(CASE WHEN puntos = 12 THEN 1 END) as exactos_dif_mayor,
            COUNT(CASE WHEN puntos = 10 THEN 1 END) as exactos_dif_menor,
            COUNT(CASE WHEN puntos = 6 THEN 1 END) as ganador_dif_correcta,
            COUNT(CASE WHEN puntos = 4 THEN 1 END) as solo_ganador,
            COUNT(CASE WHEN puntos = 0 THEN 1 END) as fallos
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        WHERE p.participante = ?
    """
    df_stats = pd.read_sql_query(query_stats, conn, params=(participante,))

    conn.close()
    return df_jornadas, df_stats

def exportar_pronosticos_jornada(jornada_id):
    """Exporta todos los pronósticos de una jornada en formato CSV para auditoría"""
    conn = get_conn()

    # Obtener información de la jornada
    query_jornada = "SELECT numero, nombre, fase FROM jornadas WHERE id = ?"
    jornada_info = pd.read_sql_query(query_jornada, conn, params=(jornada_id,))

    # Obtener partidos de la jornada
    query_partidos = """
        SELECT id, numero_partido, nombre, resultado_real, es_doble
        FROM partidos
        WHERE jornada_id = ?
        ORDER BY numero_partido
    """
    partidos = pd.read_sql_query(query_partidos, conn, params=(jornada_id,))

    # Obtener todos los pronósticos
    query_pronosticos = """
        SELECT
            p.participante,
            pa.numero_partido,
            pa.nombre as partido,
            p.prediccion,
            pa.resultado_real,
            p.puntos,
            pa.es_doble
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        WHERE pa.jornada_id = ?
        ORDER BY p.participante, pa.numero_partido
    """
    pronosticos = pd.read_sql_query(query_pronosticos, conn, params=(jornada_id,))
    conn.close()

    # Crear DataFrame pivotado (participantes en filas, partidos en columnas)
    data_export = {'Participante': []}

    # Obtener lista única de participantes
    participantes = pronosticos['participante'].unique()

    for participante in participantes:
        data_export['Participante'].append(participante)

        # Añadir pronóstico de cada partido
        prons_participante = pronosticos[pronosticos['participante'] == participante]

        for _, partido in partidos.iterrows():
            num_partido = partido['numero_partido']
            pron = prons_participante[prons_participante['numero_partido'] == num_partido]

            col_nombre = f"Partido_{num_partido}"
            col_pred = f"Pred_{num_partido}"
            col_resultado = f"Resultado_{num_partido}"
            col_puntos = f"Puntos_{num_partido}"

            # Crear columnas si no existen
            if col_nombre not in data_export:
                data_export[col_nombre] = []
            if col_pred not in data_export:
                data_export[col_pred] = []
            if col_resultado not in data_export:
                data_export[col_resultado] = []
            if col_puntos not in data_export:
                data_export[col_puntos] = []

            # Añadir datos
            if len(pron) > 0:
                data_export[col_nombre].append(pron.iloc[0]['partido'])
                data_export[col_pred].append(pron.iloc[0]['prediccion'])
                _r = pron.iloc[0]['resultado_real']
                _r = str(_r) if _r is not None and str(_r).lower() != 'nan' else None
                data_export[col_resultado].append(_r if _r else 'Pendiente')
                puntos_display = pron.iloc[0]['puntos']
                if pron.iloc[0]['es_doble'] and puntos_display > 0:
                    puntos_display = f"{puntos_display} (x2)"
                data_export[col_puntos].append(puntos_display)
            else:
                data_export[col_nombre].append(partido['nombre'])
                data_export[col_pred].append('N/A')
                data_export[col_resultado].append('N/A')
                data_export[col_puntos].append(0)

    df_export = pd.DataFrame(data_export)

    # Añadir total de puntos
    total_puntos = []
    for participante in participantes:
        prons_part = pronosticos[pronosticos['participante'] == participante]
        total_puntos.append(prons_part['puntos'].sum())

    df_export['Total_Puntos'] = total_puntos

    return df_export, jornada_info

# Inicializar base de datos
init_db()

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .stat-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 1rem;
        color: #666;
    }
    .header-image {
        height: 120px;
        width: 100%;
        object-fit: cover;
        margin-bottom: 1rem;
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# Funciones auxiliares para manejo de sesión con localStorage
def get_session_from_browser():
    """Obtiene el nivel de usuario guardado en localStorage del navegador"""
    from streamlit.components.v1 import html

    # Script para leer localStorage y guardarlo en session_state
    js_code = """
    <script>
        const userLevel = localStorage.getItem('porra_user_level');
        if (userLevel) {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: userLevel}, '*');
        }
    </script>
    """
    return html(js_code, height=0)

def save_session_to_browser(user_level):
    """Guarda el nivel de usuario en localStorage del navegador"""
    from streamlit.components.v1 import html

    js_code = f"""
    <script>
        localStorage.setItem('porra_user_level', '{user_level}');
    </script>
    """
    html(js_code, height=0)

def clear_session_from_browser():
    """Limpia la sesión del localStorage del navegador"""
    from streamlit.components.v1 import html

    js_code = """
    <script>
        localStorage.removeItem('porra_user_level');
    </script>
    """
    html(js_code, height=0)

# Sistema de autenticación con tres niveles
def check_password():
    """Retorna el nivel de acceso: 'admin', 'responsable', o None"""

    def password_entered():
        """Verifica la contraseña introducida"""
        # Verificar que la clave existe antes de acceder
        if "password" not in st.session_state:
            return

        password = st.session_state["password"]
        admin_pwd = st.secrets.get("admin_password", "admin123")
        responsable_pwd = st.secrets.get("responsable_password", "peña2026")

        if password == admin_pwd:
            st.session_state["user_level"] = "admin"
            st.session_state["password_correct"] = True
            save_session_to_browser("admin")
        elif password == responsable_pwd:
            st.session_state["user_level"] = "responsable"
            st.session_state["password_correct"] = True
            save_session_to_browser("responsable")
        else:
            st.session_state["password_correct"] = False
            st.session_state["user_level"] = None

        # Limpiar password del estado
        if "password" in st.session_state:
            del st.session_state["password"]

    # Inicializar estado desde cookies si existe
    if "password_correct" not in st.session_state:
        # Intentar recuperar sesión desde query params (solución simple)
        try:
            import streamlit as st_check
            if 'session_token' in st.query_params:
                token = st.query_params['session_token']
                if token == 'admin_token':
                    st.session_state["user_level"] = "admin"
                    st.session_state["password_correct"] = True
                elif token == 'responsable_token':
                    st.session_state["user_level"] = "responsable"
                    st.session_state["password_correct"] = True
                else:
                    st.session_state["password_correct"] = False
                    st.session_state["user_level"] = None
            else:
                st.session_state["password_correct"] = False
                st.session_state["user_level"] = None
        except:
            st.session_state["password_correct"] = False
            st.session_state["user_level"] = None

    # Si ya está autenticado, mostrar info y botón de logout
    if st.session_state.get("password_correct", False):
        # Mantener el token en la URL para persistencia
        if st.session_state["user_level"] == "admin":
            st.query_params['session_token'] = 'admin_token'
        elif st.session_state["user_level"] == "responsable":
            st.query_params['session_token'] = 'responsable_token'

        with st.sidebar:
            if st.session_state["user_level"] == "admin":
                st.success("🔐 Sesión: **Administrador**")
            else:
                st.success("👤 Sesión: **Responsable Peña**")

            if st.button("🚪 Cerrar Sesión"):
                st.session_state["password_correct"] = False
                st.session_state["user_level"] = None
                clear_session_from_browser()
                # Limpiar token de la URL
                if 'session_token' in st.query_params:
                    del st.query_params['session_token']
                st.rerun()

            st.markdown("---")

        return st.session_state["user_level"]

    # Mostrar formulario de login
    with st.sidebar:
        st.markdown("### 🔐 Iniciar Sesión")
        st.text_input(
            "Contraseña",
            type="password",
            on_change=password_entered,
            key="password",
            placeholder="Ingresa tu contraseña"
        )

        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Contraseña incorrecta")

        st.markdown("---")
        st.info("""
        **Niveles de acceso:**

        👤 **Responsable Peña**
        - Ingresar pronósticos

        🔐 **Administrador**
        - Gestión completa
        """)

    return None

# Verificar autenticación
user_level = check_password()
is_admin = (user_level == "admin")
is_responsable = (user_level == "responsable")
is_authenticated = (is_admin or is_responsable)

# Header
st.markdown('<div class="main-header">⚽ Porra Mundial 2026 ⚽</div>', unsafe_allow_html=True)

# Indicador de base de datos en sidebar
with st.sidebar:
    from database import USE_TURSO
    if USE_TURSO:
        st.success("💾 Base de datos: **Turso Cloud** (persistente)")
    else:
        st.warning("💾 Base de datos: **SQLite Local** (se pierde al reiniciar)")

# Tabs principales - mostrar según nivel de acceso
if is_admin:
    # Admin ve todo
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Inicio",
        "👥 Usuarios",
        "➕ Nueva Jornada",
        "📝 Ingresar Pronósticos",
        "⚽ Resultados",
        "🏆 Clasificaciones",
        "📈 Estadísticas",
        "📜 Histórico"
    ])
elif is_responsable:
    # Responsable ve ingresar pronósticos, consultas e histórico
    tab1, tab4, tab6, tab7, tab8, tab_info = st.tabs([
        "📊 Inicio",
        "📝 Ingresar Pronósticos",
        "🏆 Clasificaciones",
        "📈 Estadísticas",
        "📜 Histórico",
        "ℹ️ Info"
    ])
    # Crear tabs dummy
    tab2 = tab3 = tab5 = None
else:
    # Usuarios públicos ven histórico también
    tab1, tab6, tab7, tab8, tab_info = st.tabs([
        "📊 Inicio",
        "🏆 Clasificaciones",
        "📈 Estadísticas",
        "📜 Histórico",
        "ℹ️ Info"
    ])
    # Crear tabs dummy
    tab2 = tab3 = tab4 = tab5 = None

# TAB 1: INICIO
with tab1:
    st.header("Resumen del Torneo")

    # Mostrar jornada vigente si existe
    jornada_vigente = get_jornada_vigente()

    if jornada_vigente is not None:
        # Header de jornada vigente con estilo
        estrella_badge = "⭐" if jornada_vigente['es_estrella'] else ""
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 1.5rem;
                    border-radius: 15px;
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h2 style='color: white; margin: 0; text-align: center;'>
                🔴 JORNADA EN CURSO
            </h2>
            <h3 style='color: white; margin: 0.5rem 0 0 0; text-align: center; font-weight: normal;'>
                {jornada_vigente['nombre']} - {jornada_vigente['fase']} {estrella_badge}
            </h3>
        </div>
        """, unsafe_allow_html=True)

        # Obtener partidos de la jornada vigente
        conn = get_conn()
        partidos_vigentes = pd.read_sql_query(
            "SELECT * FROM partidos WHERE jornada_id = ? ORDER BY numero_partido",
            conn, params=(int(jornada_vigente['id']),)
        )
        conn.close()

        if len(partidos_vigentes) > 0:
            # Mostrar partidos en un grid de 2 columnas
            for i in range(0, len(partidos_vigentes), 2):
                cols = st.columns(2)

                for col_idx, col in enumerate(cols):
                    partido_idx = i + col_idx
                    if partido_idx < len(partidos_vigentes):
                        partido = partidos_vigentes.iloc[partido_idx]

                        # Determinar estado y color
                        resultado_val = str(partido['resultado_real']) if partido['resultado_real'] is not None else ''
                        if resultado_val.strip() and resultado_val.strip().lower() != 'nan':
                            estado_icon = "✅"
                            estado_text = partido['resultado_real']
                            bg_color = "#d4edda"
                            border_color = "#28a745"
                        else:
                            estado_icon = "⏳"
                            estado_text = "Pendiente"
                            bg_color = "#fff3cd"
                            border_color = "#ffc107"

                        doble_badge = "⭐ DOBLE" if partido['es_doble'] else ""

                        # Extraer equipos del nombre (formato: "Equipo1 vs Equipo2")
                        nombre_partido = partido['nombre']
                        equipos = nombre_partido.split(' vs ') if ' vs ' in nombre_partido else [nombre_partido, '']
                        equipo_local = equipos[0] if len(equipos) > 0 else ''
                        equipo_visitante = equipos[1] if len(equipos) > 1 else ''

                        # Extraer resultado si existe
                        resultado_val = str(partido['resultado_real']) if partido['resultado_real'] is not None else ''
                        if resultado_val.strip() and resultado_val.strip().lower() != 'nan':
                            goles = partido['resultado_real'].split('-')
                            goles_local = goles[0].strip() if len(goles) > 0 else ''
                            goles_visitante = goles[1].strip() if len(goles) > 1 else ''
                        else:
                            goles_local = '-'
                            goles_visitante = '-'

                        with col:
                            st.markdown(f"""
                            <div style='background-color: {bg_color};
                                        border-left: 5px solid {border_color};
                                        padding: 1rem;
                                        border-radius: 10px;
                                        margin-bottom: 1rem;
                                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;'>
                                    <span style='font-weight: bold; color: #333; font-size: 0.85rem;'>
                                        PARTIDO {partido['numero_partido']} {doble_badge}
                                    </span>
                                    <span style='font-size: 1.1rem;'>{estado_icon}</span>
                                </div>
                                <div style='display: grid; grid-template-columns: 2fr 1fr 0.5fr 1fr 2fr; align-items: center; gap: 0.5rem;'>
                                    <div style='text-align: right; font-weight: 500; color: #333;'>{equipo_local}</div>
                                    <div style='text-align: center; font-size: 1.5rem; font-weight: bold; color: {border_color};'>{goles_local}</div>
                                    <div style='text-align: center; font-weight: bold; color: #666;'>-</div>
                                    <div style='text-align: center; font-size: 1.5rem; font-weight: bold; color: {border_color};'>{goles_visitante}</div>
                                    <div style='text-align: left; font-weight: 500; color: #333;'>{equipo_visitante}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ No hay partidos configurados para esta jornada")

        st.markdown("---")

    jornadas_df = get_jornadas()

    if len(jornadas_df) > 0:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{len(jornadas_df)}</div>
                <div class="stat-label">Jornadas Jugadas</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            jornadas_estrella = len(jornadas_df[jornadas_df['es_estrella'] == 1])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{jornadas_estrella}</div>
                <div class="stat-label">Jornadas Estrella ⭐</div>
            </div>
            """, unsafe_allow_html=True)

        # Obtener clasificación para stats (sin deuda)
        clasificacion = get_clasificacion_general(incluir_deuda=False)

        with col3:
            if len(clasificacion) > 0:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">{len(clasificacion)}</div>
                    <div class="stat-label">Participantes</div>
                </div>
                """, unsafe_allow_html=True)

        with col4:
            if len(clasificacion) > 0:
                lider = clasificacion.iloc[0]['participante']
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number">👑</div>
                    <div class="stat-label">Líder: {lider}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # Clasificación General Completa
        st.subheader("🏆 Clasificación General del Mundial 2026")

        # Obtener clasificación con o sin deuda según el rol
        clasificacion_completa = get_clasificacion_general(incluir_deuda=is_admin)

        if len(clasificacion_completa) > 0:
            # Añadir posición
            clasificacion_display = clasificacion_completa.copy()
            clasificacion_display.insert(0, 'Posición', range(1, len(clasificacion_display) + 1))

            # Formatear columnas según el rol
            if is_admin:
                clasificacion_display.columns = ['Posición', 'Participante', 'Puntos', 'Exactos',
                                                 'Ganador+Dif', 'Solo Ganador', 'Jornadas Jugadas', 'Mejor Jornada',
                                                 'Jornadas Sin Participar', 'Debe (€)']
            else:
                clasificacion_display.columns = ['Posición', 'Participante', 'Puntos', 'Exactos',
                                                 'Ganador+Dif', 'Solo Ganador', 'Jornadas', 'Mejor Jornada']

            st.dataframe(clasificacion_display, use_container_width=True, hide_index=True)
    else:
        st.info("👋 ¡Bienvenido! No hay jornadas registradas aún. Ve a la pestaña 'Nueva Jornada' para comenzar.")

# TAB 2: USUARIOS (Solo Admin)
if tab2 is not None:
  with tab2:
    st.header("👥 Gestión de Usuarios")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📋 Usuarios Registrados")

        # Filtro
        mostrar_inactivos = st.checkbox("Mostrar usuarios inactivos", value=False)
        usuarios_df = get_usuarios(solo_activos=not mostrar_inactivos)

        if len(usuarios_df) > 0:
            # Mostrar tabla con opciones
            st.dataframe(usuarios_df, use_container_width=True, hide_index=True)

            col_stats, col_export = st.columns([2, 1])

            with col_stats:
                # Manejar si la columna 'activo' no existe (BD corrupta)
                if 'activo' in usuarios_df.columns:
                    st.markdown(f"**Total usuarios activos:** {len(usuarios_df[usuarios_df['activo'] == 1])}")
                else:
                    st.markdown(f"**Total usuarios:** {len(usuarios_df)}")
                    st.warning("⚠️ Columna 'activo' no encontrada. Usa 'HERRAMIENTAS AVANZADAS' abajo para recrear tablas.")

            with col_export:
                # Exportar solo nombres de usuarios activos
                if 'activo' in usuarios_df.columns:
                    usuarios_export = usuarios_df[usuarios_df['activo'] == 1][['nombre']].copy()
                else:
                    usuarios_export = usuarios_df[['nombre']].copy()

                csv_usuarios = usuarios_export.to_csv(index=False).encode('utf-8')

                st.download_button(
                    label="📥 Exportar Nombres (CSV)",
                    data=csv_usuarios,
                    file_name=f"usuarios_porra_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )

            # Editar usuario
            st.markdown("---")
            st.subheader("✏️ Editar Nombre de Usuario")

            if 'activo' in usuarios_df.columns:
                usuarios_activos = usuarios_df[usuarios_df['activo'] == 1]['nombre'].tolist()
            else:
                usuarios_activos = usuarios_df['nombre'].tolist()

            if usuarios_activos:
                usuario_editar = st.selectbox("Selecciona usuario a editar", usuarios_activos, key="select_editar")
                nuevo_nombre_edit = st.text_input("Nuevo nombre", value=usuario_editar, key="input_nuevo_nombre")

                if st.button("💾 Guardar Cambio", type="primary"):
                    if nuevo_nombre_edit.strip() and nuevo_nombre_edit.strip() != usuario_editar:
                        success, mensaje = actualizar_nombre_usuario(usuario_editar, nuevo_nombre_edit.strip())
                        if success:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error(mensaje)
                    elif nuevo_nombre_edit.strip() == usuario_editar:
                        st.info("El nombre no ha cambiado")
                    else:
                        st.error("El nuevo nombre no puede estar vacío")
            else:
                st.info("No hay usuarios activos para editar")

            # Eliminar usuario
            st.markdown("---")
            st.subheader("❌ Desactivar Usuario")

            if usuarios_activos:
                usuario_eliminar = st.selectbox("Selecciona usuario a desactivar", usuarios_activos, key="select_eliminar")

                if st.button("🗑️ Desactivar Usuario", type="secondary"):
                    eliminar_usuario(usuario_eliminar)
                    st.success(f"Usuario '{usuario_eliminar}' desactivado")
                    st.rerun()
            else:
                st.info("No hay usuarios activos para desactivar")

            # Reactivar usuario
            usuarios_inactivos = usuarios_df[usuarios_df['activo'] == 0]['nombre'].tolist()
            if usuarios_inactivos:
                st.markdown("---")
                st.subheader("✅ Reactivar Usuario")
                usuario_reactivar = st.selectbox("Selecciona usuario a reactivar", usuarios_inactivos)

                if st.button("♻️ Reactivar Usuario", type="secondary"):
                    reactivar_usuario(usuario_reactivar)
                    st.success(f"Usuario '{usuario_reactivar}' reactivado")
                    st.rerun()
        else:
            st.info("No hay usuarios registrados. Añade el primero abajo.")

    with col2:
        st.subheader("➕ Añadir Usuario")

        with st.form("form_nuevo_usuario"):
            nuevo_nombre = st.text_input("Nombre del participante *", placeholder="Ej: Juan Pérez")
            nuevo_email = st.text_input("Email (opcional)", placeholder="juan@ejemplo.com")

            submit_usuario = st.form_submit_button("✅ Crear Usuario", type="primary", use_container_width=True)

            if submit_usuario:
                if nuevo_nombre.strip():
                    success, mensaje = crear_usuario(nuevo_nombre.strip(), nuevo_email.strip())
                    if success:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)
                else:
                    st.error("El nombre es obligatorio")

        st.markdown("---")
        st.subheader("📂 Cargar Usuarios Masivamente")

        st.markdown("""
        **Formato del archivo:**
        - Columna 'Nombre' o 'Participante' (obligatorio)
        - Columna 'Email' (opcional)

        **Ejemplo CSV:**
        ```
        Nombre,Email
        Juan Pérez,juan@mail.com
        María García,maria@mail.com
        ```
        """)

        archivo_usuarios = st.file_uploader(
            "Selecciona archivo con usuarios",
            type=['xlsx', 'xls', 'csv'],
            key="upload_usuarios"
        )

        if archivo_usuarios and st.button("📥 Cargar Usuarios", type="primary"):
            success, mensaje = cargar_usuarios_desde_archivo(archivo_usuarios)
            if success:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)

    # SECCIÓN DE ADMINISTRACIÓN: Eliminar Usuario
    st.markdown("---")
    st.markdown("### 🗑️ Zona de Administración")

    with st.expander("⚠️ Eliminar Usuario Permanentemente", expanded=False):
        st.error("""
        **ADVERTENCIA CRÍTICA:** Esta acción eliminará permanentemente:
        - El usuario seleccionado
        - **TODOS sus pronósticos** en todas las jornadas
        - Su historial completo

        Esta acción **NO se puede deshacer** y afectará las clasificaciones.
        """)

        usuarios_activos = get_usuarios()
        if len(usuarios_activos) > 0:
            col_select, col_confirm = st.columns(2)

            with col_select:
                usuario_eliminar = st.selectbox(
                    "Selecciona usuario a eliminar",
                    options=usuarios_activos['nombre'].tolist(),
                    key="usuario_eliminar_select"
                )

            with col_confirm:
                confirmar_eliminar_usuario = st.text_input(
                    "Escribe 'ELIMINAR' para confirmar",
                    key="confirmar_eliminar_usuario"
                )

            if st.button("🗑️ Eliminar Usuario Definitivamente", type="secondary", disabled=(confirmar_eliminar_usuario != "ELIMINAR")):
                try:
                    conn = get_conn()
                    c = conn.cursor()

                    # Eliminar todos los pronósticos del usuario
                    c.execute("DELETE FROM pronosticos WHERE LOWER(participante) = LOWER(?)", (usuario_eliminar,))

                    # Eliminar el usuario
                    c.execute("DELETE FROM usuarios WHERE LOWER(nombre) = LOWER(?)", (usuario_eliminar,))

                    conn.commit()
                    conn.close()

                    st.success(f"✅ Usuario '{usuario_eliminar}' y todos sus pronósticos eliminados correctamente")
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error al eliminar usuario: {e}")
        else:
            st.info("No hay usuarios para eliminar")

    # SECCIÓN DE LIMPIEZA: Eliminar jornadas excepto la primera
    st.markdown("---")
    with st.expander("🗑️ Limpiar Jornadas (Mantener solo la primera)", expanded=False):
        st.warning("""
        **⚠️ ADVERTENCIA:**

        Esta acción eliminará **TODAS las jornadas excepto la primera**, incluyendo:
        - Partidos de esas jornadas
        - Pronósticos de esas jornadas
        - Resultados de esas jornadas

        **LA PRIMERA JORNADA SE CONSERVA INTACTA** con todos sus datos.

        Esto es útil para mantener la estructura inicial pero limpiar pruebas.
        """)

        confirmar_limpiar = st.text_input(
            "Escribe 'LIMPIAR JORNADAS' para confirmar",
            key="confirmar_limpiar_jornadas"
        )

        if st.button("🗑️ Mantener Solo Primera Jornada", type="secondary", disabled=(confirmar_limpiar != "LIMPIAR JORNADAS")):
            try:
                conn = get_conn()
                c = conn.cursor()

                # Obtener todas las jornadas
                c.execute("SELECT id, numero, nombre FROM jornadas ORDER BY numero")
                jornadas = c.fetchall()

                if len(jornadas) > 1:
                    primera_jornada_id = jornadas[0][0]
                    jornadas_eliminar = [j[0] for j in jornadas[1:]]

                    eliminadas = 0
                    for jornada_id in jornadas_eliminar:
                        # Obtener IDs de partidos
                        c.execute("SELECT id FROM partidos WHERE jornada_id = ?", (jornada_id,))
                        partido_ids = [row[0] for row in c.fetchall()]

                        # Eliminar pronósticos
                        if partido_ids:
                            placeholders = ','.join(['?' for _ in partido_ids])
                            c.execute(f"DELETE FROM pronosticos WHERE partido_id IN ({placeholders})", partido_ids)

                        # Eliminar partidos
                        c.execute("DELETE FROM partidos WHERE jornada_id = ?", (jornada_id,))

                        # Eliminar jornada
                        c.execute("DELETE FROM jornadas WHERE id = ?", (jornada_id,))
                        eliminadas += 1

                    conn.commit()
                    conn.close()

                    st.success(f"✅ {eliminadas} jornadas eliminadas. La primera jornada ({jornadas[0][2]}) se ha conservado con todos sus datos.")
                    st.balloons()
                    st.rerun()
                else:
                    conn.close()
                    st.info("ℹ️ Solo existe una jornada, no hay nada que eliminar.")

            except Exception as e:
                st.error(f"❌ Error al limpiar jornadas: {e}")
                import traceback
                st.code(traceback.format_exc())

    # SECCIÓN OCULTA: Recrear todas las tablas (solo para emergencias)
    st.markdown("---")
    with st.expander("🔧 HERRAMIENTAS AVANZADAS (Solo Emergencias)", expanded=False):
        st.error("""
        **⚠️ PELIGRO EXTREMO ⚠️**

        Esta herramienta eliminará **TODAS LAS TABLAS** y las recreará desde cero.
        Perderás:
        - Todos los usuarios
        - Todas las jornadas
        - Todos los partidos
        - Todos los pronósticos

        **ÚSALO SOLO SI LA BASE DE DATOS ESTÁ CORRUPTA Y NECESITAS EMPEZAR DE CERO.**
        """)

        confirmar_recrear = st.text_input(
            "Escribe 'RECREAR TABLAS' para confirmar",
            key="confirmar_recrear_tablas"
        )

        if st.button("💣 RECREAR TODAS LAS TABLAS", type="secondary", disabled=(confirmar_recrear != "RECREAR TABLAS")):
            try:
                conn = get_conn()
                c = conn.cursor()

                with st.spinner("Eliminando tablas..."):
                    c.execute("DROP TABLE IF EXISTS pronosticos")
                    c.execute("DROP TABLE IF EXISTS partidos")
                    c.execute("DROP TABLE IF EXISTS jornadas")
                    c.execute("DROP TABLE IF EXISTS usuarios")
                    conn.commit()

                with st.spinner("Creando tablas nuevas..."):
                    # Usuarios
                    c.execute('''CREATE TABLE usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        email TEXT,
                        fecha_registro TEXT,
                        activo INTEGER DEFAULT 1
                    )''')

                    # Jornadas
                    c.execute('''CREATE TABLE jornadas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        numero INTEGER NOT NULL,
                        nombre TEXT,
                        es_estrella INTEGER DEFAULT 0,
                        fecha TEXT,
                        fase TEXT,
                        estado_pronosticos TEXT DEFAULT 'cerrada',
                        fecha_fin TEXT
                    )''')

                    # Partidos
                    c.execute('''CREATE TABLE partidos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        jornada_id INTEGER,
                        numero_partido INTEGER,
                        nombre TEXT,
                        resultado_real TEXT,
                        es_doble INTEGER DEFAULT 0,
                        FOREIGN KEY (jornada_id) REFERENCES jornadas (id)
                    )''')

                    # Pronósticos
                    c.execute('''CREATE TABLE pronosticos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        partido_id INTEGER,
                        participante TEXT,
                        prediccion TEXT,
                        puntos INTEGER,
                        FOREIGN KEY (partido_id) REFERENCES partidos (id)
                    )''')

                    conn.commit()
                    conn.close()

                st.success("✅ Tablas recreadas exitosamente. La base de datos está ahora vacía y lista para usar.")
                st.balloons()
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al recrear tablas: {e}")
                import traceback
                st.code(traceback.format_exc())

# TAB 3: NUEVA JORNADA (Solo Admin)
if tab3 is not None:
  with tab3:
    st.header("➕ Crear Nueva Jornada")

    # Verificar que haya usuarios registrados
    usuarios_registrados_check = get_usuarios()
    if len(usuarios_registrados_check) == 0:
        st.warning("⚠️ No hay usuarios registrados. Ve a la pestaña 'Usuarios' para añadir participantes primero.")
    else:
        jornadas_existentes = get_jornadas()
        siguiente_numero = len(jornadas_existentes) + 1

        st.markdown("### 📋 Paso 1: Información de la Jornada")

        col1, col2, col3 = st.columns(3)

        with col1:
            numero_jornada = st.number_input("Número de Jornada", min_value=1, value=siguiente_numero, key="num_jornada")

        with col2:
            nombre_jornada = st.text_input("Nombre de la Jornada", value=f"Jornada {siguiente_numero}", key="nombre_jornada")

        with col3:
            fase = st.text_input("Fase del Mundial", value="Fase de Grupos",
                               placeholder="Ej: Octavos, Semifinales, Final...", key="fase_jornada")

        st.markdown("**Fecha de la Jornada**")
        st.info("La jornada se mostrará en la página principal desde que se cree hasta que pase esta fecha")

        fecha_fin = st.date_input(
            "Fecha del último partido de la jornada",
            value=None,
            help="La jornada estará vigente hasta esta fecha",
            key="fecha_fin_jornada"
        )

        st.markdown("---")
        st.markdown("### ⚽ Paso 2: Configurar Partidos")

        col_partidos, col_estrella = st.columns([2, 1])

        with col_partidos:
            num_partidos = st.number_input("¿Cuántos partidos tiene esta jornada?", min_value=1, max_value=20, value=5, key="num_partidos")

        with col_estrella:
            es_estrella = st.checkbox("⭐ Jornada Estrella", key="es_estrella")
            if es_estrella:
                partido_doble = st.selectbox("¿Qué partido puntúa doble?",
                                            options=list(range(1, num_partidos + 1)),
                                            format_func=lambda x: f"Partido {x}",
                                            key="partido_doble_select")
            else:
                partido_doble = None

        st.markdown("**Ingresa los detalles de cada partido:**")

        # Crear formulario dinámico para cada partido
        partidos_data = []
        for i in range(num_partidos):
            st.markdown(f"**Partido {i+1}** {'⭐ (Doble)' if es_estrella and partido_doble == i+1 else ''}")

            # Layout: Equipo Local [goles] - [goles] Equipo Visitante
            col_local, col_gol_local, col_vs, col_gol_visit, col_visitante = st.columns([3, 1, 0.5, 1, 3])

            with col_local:
                equipo_local = st.selectbox(
                    f"Equipo Local {i+1}",
                    options=[""] + SELECCIONES_MUNDIAL_2026,
                    format_func=lambda x: "Selecciona equipo local..." if x == "" else x,
                    key=f"equipo_local_{i}",
                    label_visibility="collapsed"
                )

            with col_gol_local:
                goles_local = st.text_input(
                    f"Goles Local {i+1}",
                    placeholder="0",
                    key=f"goles_local_{i}",
                    label_visibility="collapsed"
                )

            with col_vs:
                st.markdown("<div style='text-align: center; padding-top: 8px;'>-</div>", unsafe_allow_html=True)

            with col_gol_visit:
                goles_visitante = st.text_input(
                    f"Goles Visitante {i+1}",
                    placeholder="0",
                    key=f"goles_visit_{i}",
                    label_visibility="collapsed"
                )

            with col_visitante:
                equipo_visitante = st.selectbox(
                    f"Equipo Visitante {i+1}",
                    options=[""] + SELECCIONES_MUNDIAL_2026,
                    format_func=lambda x: "Selecciona equipo visitante..." if x == "" else x,
                    key=f"equipo_visit_{i}",
                    label_visibility="collapsed"
                )

            # Construir nombre del partido y resultado
            if equipo_local.strip() and equipo_visitante.strip():
                nombre_partido = f"{equipo_local.strip()} vs {equipo_visitante.strip()}"
            else:
                nombre_partido = ""

            if goles_local.strip() and goles_visitante.strip():
                resultado = f"{goles_local.strip()}-{goles_visitante.strip()}"
            else:
                resultado = ""

            partidos_data.append({
                'numero': i + 1,
                'nombre': nombre_partido,
                'resultado': resultado,
                'es_doble': es_estrella and partido_doble == i + 1
            })

        st.markdown("---")
        st.markdown("### 📁 Paso 3: Modo de Creación")

        modo_creacion = st.radio(
            "¿Cómo quieres crear la jornada?",
            options=["crear_vacia", "cargar_archivo"],
            format_func=lambda x: "🎯 Crear jornada vacía (para rellenar en la peña)" if x == "crear_vacia" else "📁 Cargar archivo con pronósticos",
            key="modo_creacion"
        )

        archivo = None

        if modo_creacion == "crear_vacia":
            st.info("""
            **Modo: Jornada vacía**

            Se creará la jornada con los partidos configurados pero sin pronósticos.
            Los usuarios podrán ingresar sus pronósticos desde la peña usando la sección "📝 Ingresar Pronósticos".

            La jornada se creará en estado **"Abierta"** para que se puedan ingresar pronósticos.
            """)

            abrir_pronosticos = True  # Por defecto abierta

        else:  # cargar_archivo
            st.markdown("""
            **Formato del archivo Excel/CSV:**
            - **Columna 1:** Participante (debe coincidir con los nombres registrados)
            - **Columnas siguientes:** Predicciones en formato `X-X` (ej: `2-1`)
            - El número de columnas debe coincidir con el número de partidos configurados arriba

            **Ejemplo para 5 partidos:**
            ```
            Participante | Pred1 | Pred2 | Pred3 | Pred4 | Pred5
            Juan Pérez  | 2-1   | 0-0   | 1-1   | 3-0   | 2-2
            María García| 1-1   | 1-0   | 2-1   | 2-1   | 1-1
            ```
            """)

            archivo = st.file_uploader("Selecciona archivo Excel o CSV con pronósticos",
                                       type=['xlsx', 'xls', 'csv'],
                                       help="Archivo con participantes y sus pronósticos",
                                       key="upload_jornada")

            abrir_pronosticos = st.checkbox(
                "Mantener jornada abierta para más pronósticos",
                value=False,
                help="Si marcas esto, otros usuarios podrán seguir ingresando pronósticos"
            )

        # Validaciones antes de crear
        puede_crear = (modo_creacion == "crear_vacia") or (archivo is not None)

        if st.button("🚀 Crear Jornada", type="primary", disabled=not puede_crear):
            # Validar que se hayan ingresado todos los datos
            errores = []

            if not nombre_jornada.strip():
                errores.append("El nombre de la jornada es obligatorio")

            if not fase.strip():
                errores.append("La fase del mundial es obligatoria")

            # Validar partidos
            partidos_validos = []
            for p in partidos_data:
                if not p['nombre'].strip():
                    errores.append(f"El nombre del Partido {p['numero']} es obligatorio")
                    continue

                if p['resultado'].strip():
                    # Validar formato de resultado
                    if '-' not in p['resultado'] or not all(x.isdigit() for x in p['resultado'].split('-')):
                        errores.append(f"El resultado del Partido {p['numero']} tiene formato incorrecto (use X-X)")
                        continue

                partidos_validos.append(p)

            if errores:
                for error in errores:
                    st.error(f"❌ {error}")
            else:
                with st.spinner("Procesando jornada..."):
                    # Convertir fecha a string si existe
                    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d") if fecha_fin else None

                    # Crear jornada
                    jornada_id = crear_jornada(numero_jornada, nombre_jornada, 1 if es_estrella else 0, fase, fecha_fin_str)

                    # Establecer estado de pronósticos
                    estado = 'abierta' if abrir_pronosticos else 'cerrada'

                    conn = get_conn()
                    c = conn.cursor()

                    # Actualizar estado de jornada
                    c.execute("UPDATE jornadas SET estado_pronosticos = ? WHERE id = ?", (estado, jornada_id))

                    # Crear partidos manualmente
                    partidos_ids = []
                    for p in partidos_validos:
                        c.execute("""INSERT INTO partidos (jornada_id, numero_partido, nombre, resultado_real, es_doble)
                                    VALUES (?, ?, ?, ?, ?)""",
                                 (jornada_id, p['numero'], p['nombre'], p['resultado'] if p['resultado'].strip() else None, 1 if p['es_doble'] else 0))
                        partidos_ids.append(c.lastrowid)

                    conn.commit()
                    conn.close()

                    # Procesar archivo de pronósticos si hay
                    if archivo:
                        success, message = procesar_archivo_pronosticos(archivo, jornada_id, partidos_ids, partidos_validos)

                        if success:
                            st.success(f"✅ {message}")
                            if abrir_pronosticos:
                                st.info("ℹ️ La jornada está **abierta** para que se puedan ingresar más pronósticos.")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        # Modo jornada vacía
                        st.success(f"✅ Jornada creada correctamente!")
                        st.success(f"🎯 La jornada está **abierta** para ingresar pronósticos.")
                        st.info("Los usuarios pueden ingresar sus pronósticos desde la sección '📝 Ingresar Pronósticos'")
                        st.balloons()

# TAB 4: INGRESAR PRONÓSTICOS (Responsable y Admin)
if tab4 is not None:
  with tab4:
    st.header("📝 Ingresar Pronósticos")

    # Obtener jornadas abiertas
    conn = get_conn()
    jornadas_abiertas = pd.read_sql_query(
        "SELECT * FROM jornadas WHERE estado_pronosticos = 'abierta' ORDER BY numero DESC",
        conn
    )
    conn.close()

    if len(jornadas_abiertas) == 0:
        st.warning("⚠️ No hay jornadas abiertas para ingresar pronósticos.")
        st.info("El administrador debe crear y abrir una jornada primero.")
    else:
        # Seleccionar jornada
        jornada_seleccionada = st.selectbox(
            "Selecciona la jornada",
            options=jornadas_abiertas['id'].tolist(),
            format_func=lambda x: f"Jornada {jornadas_abiertas[jornadas_abiertas['id'] == x]['numero'].iloc[0]} - {jornadas_abiertas[jornadas_abiertas['id'] == x]['nombre'].iloc[0]}",
            key="jornada_pronosticos"
        )

        jornada_info = jornadas_abiertas[jornadas_abiertas['id'] == jornada_seleccionada].iloc[0]

        st.markdown(f"### {jornada_info['nombre']}")
        st.markdown(f"**Fase:** {jornada_info['fase']}")
        if jornada_info['es_estrella']:
            st.markdown("⭐ **Jornada Estrella** - Un partido puntúa doble")

        st.markdown("---")

        # Buscar usuario
        usuarios_activos = get_usuarios()
        usuario_nombres = usuarios_activos['nombre'].tolist()

        col_search, col_button = st.columns([3, 1])

        with col_search:
            usuario_seleccionado = st.selectbox(
                "Busca tu nombre",
                options=[""] + usuario_nombres,
                format_func=lambda x: "Selecciona tu nombre..." if x == "" else x,
                key="buscar_usuario"
            )

        if usuario_seleccionado and usuario_seleccionado != "":
            st.markdown(f"### Pronósticos de: **{usuario_seleccionado}**")

            # Obtener partidos de la jornada
            conn = get_conn()
            partidos_df = pd.read_sql_query(
                "SELECT * FROM partidos WHERE jornada_id = ? ORDER BY numero_partido",
                conn, params=(jornada_seleccionada,)
            )

            # Verificar si ya tiene pronósticos
            pronosticos_existentes = pd.read_sql_query(
                """SELECT p.partido_id, p.prediccion
                   FROM pronosticos p
                   WHERE p.participante = ? AND p.partido_id IN (SELECT id FROM partidos WHERE jornada_id = ?)""",
                conn, params=(usuario_seleccionado, jornada_seleccionada)
            )
            conn.close()

            # Crear diccionario de pronósticos existentes
            pron_dict = {}
            if len(pronosticos_existentes) > 0:
                pron_dict = dict(zip(pronosticos_existentes['partido_id'], pronosticos_existentes['prediccion']))

            # Formulario para ingresar pronósticos
            with st.form(key=f"form_pronosticos_{usuario_seleccionado}"):
                pronosticos = {}

                for _, partido in partidos_df.iterrows():
                    doble_text = " ⭐ (Doble)" if partido['es_doble'] else ""
                    st.markdown(f"**Partido {partido['numero_partido']}**{doble_text}")

                    # Extraer equipos del nombre
                    nombre_partido = partido['nombre']
                    equipos = nombre_partido.split(' vs ') if ' vs ' in nombre_partido else [nombre_partido, '']

                    # Extraer pronóstico actual si existe
                    valor_actual = pron_dict.get(partido['id'], "")
                    goles = valor_actual.split('-') if valor_actual and '-' in valor_actual else ['', '']

                    col_local, col_gol_local, col_vs, col_gol_visit, col_visitante = st.columns([3, 1, 0.5, 1, 3])

                    with col_local:
                        st.markdown(f"<div style='padding-top: 8px;'>{equipos[0] if len(equipos) > 0 else ''}</div>", unsafe_allow_html=True)

                    with col_gol_local:
                        gol_local_pred = st.text_input(
                            f"Goles Local Pred {partido['id']}",
                            value="",
                            placeholder="0",
                            key=f"gol_local_pred_{partido['id']}",
                            label_visibility="collapsed"
                        )

                    with col_vs:
                        st.markdown("<div style='text-align: center; padding-top: 8px;'>-</div>", unsafe_allow_html=True)

                    with col_gol_visit:
                        gol_visit_pred = st.text_input(
                            f"Goles Visitante Pred {partido['id']}",
                            value="",
                            placeholder="0",
                            key=f"gol_visit_pred_{partido['id']}",
                            label_visibility="collapsed"
                        )

                    with col_visitante:
                        st.markdown(f"<div style='padding-top: 8px;'>{equipos[1] if len(equipos) > 1 else ''}</div>", unsafe_allow_html=True)

                    # Construir predicción final
                    if gol_local_pred.strip() and gol_visit_pred.strip():
                        pronosticos[partido['id']] = f"{gol_local_pred.strip()}-{gol_visit_pred.strip()}"
                    else:
                        pronosticos[partido['id']] = ""

                submitted = st.form_submit_button("💾 Guardar Pronósticos", type="primary", use_container_width=True)

                if submitted:
                    # Validar que todos los pronósticos estén completos
                    errores = []
                    for partido_id, pred in pronosticos.items():
                        if not pred or pred.strip() == "":
                            errores.append("Todos los partidos deben tener pronóstico")
                            break
                        if '-' not in pred or not all(x.strip().isdigit() for x in pred.split('-')):
                            errores.append(f"Formato incorrecto: {pred}. Usa formato X-X (ej: 2-1)")
                            break

                    if errores:
                        for error in errores:
                            st.error(f"❌ {error}")
                    else:
                        # Guardar pronósticos
                        conn = get_conn()
                        c = conn.cursor()

                        for partido_id, prediccion in pronosticos.items():
                            prediccion = prediccion.strip()

                            # Verificar si ya existe pronóstico
                            c.execute(
                                "SELECT id FROM pronosticos WHERE partido_id = ? AND participante = ?",
                                (partido_id, usuario_seleccionado)
                            )
                            existe = c.fetchone()

                            if existe:
                                # Actualizar
                                c.execute(
                                    "UPDATE pronosticos SET prediccion = ? WHERE partido_id = ? AND participante = ?",
                                    (prediccion, partido_id, usuario_seleccionado)
                                )
                            else:
                                # Insertar nuevo (sin puntos aún)
                                c.execute(
                                    "INSERT INTO pronosticos (partido_id, participante, prediccion, puntos) VALUES (?, ?, ?, 0)",
                                    (partido_id, usuario_seleccionado, prediccion)
                                )

                        conn.commit()
                        conn.close()
                        st.cache_data.clear()

                        st.success(f"✅ Pronósticos de **{usuario_seleccionado}** guardados correctamente!")
                        st.balloons()

            # Mostrar si ya tiene pronósticos guardados
            if len(pron_dict) > 0:
                st.info(f"ℹ️ Este usuario ya tiene pronósticos guardados para esta jornada. Puedes modificarlos y volver a guardar.")

# TAB 5: RESULTADOS (Actualizar resultados de jornadas existentes - Solo Admin)
if tab5 is not None:
  with tab5:
    st.header("⚽ Actualizar Resultados de Partidos")

    st.info("💡 **Actualización en tiempo real:** Puedes ingresar resultados partido por partido a medida que vayan terminando. Los puntos se recalculan automáticamente y las clasificaciones se actualizan al instante.")

    jornadas = get_jornadas()

    if len(jornadas) == 0:
        st.info("No hay jornadas creadas aún. Ve a 'Nueva Jornada' para crear una.")
    else:
        st.markdown("Selecciona una jornada para actualizar o ingresar resultados:")

        jornada_seleccionada = st.selectbox(
            "Jornada",
            options=jornadas['id'].tolist(),
            format_func=lambda x: f"{jornadas[jornadas['id'] == x]['nombre'].iloc[0]} - {jornadas[jornadas['id'] == x]['fase'].iloc[0]}",
            key="jornada_resultados"
        )

        # Obtener info de la jornada
        jornada_info = jornadas[jornadas['id'] == jornada_seleccionada].iloc[0]
        estado_actual = jornada_info.get('estado_pronosticos', 'cerrada')

        # Controles de estado de jornada
        st.markdown("---")
        col_estado, col_boton = st.columns([2, 1])

        with col_estado:
            if estado_actual == 'abierta':
                st.success("🟢 **Estado:** Abierta para pronósticos")
            else:
                st.info("🔒 **Estado:** Cerrada para pronósticos")

        with col_boton:
            if estado_actual == 'abierta':
                if st.button("🔒 Cerrar Pronósticos", use_container_width=True):
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("UPDATE jornadas SET estado_pronosticos = 'cerrada' WHERE id = ?", (jornada_seleccionada,))
                    conn.commit()
                    conn.close()
                    st.success("✅ Jornada cerrada")
                    st.rerun()
            else:
                if st.button("🟢 Abrir Pronósticos", use_container_width=True):
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("UPDATE jornadas SET estado_pronosticos = 'abierta' WHERE id = ?", (jornada_seleccionada,))
                    conn.commit()
                    conn.close()
                    st.success("✅ Jornada abierta")
                    st.rerun()

        # Obtener partidos de esa jornada
        conn = get_conn()
        partidos_df = pd.read_sql_query(
            "SELECT * FROM partidos WHERE jornada_id = ? ORDER BY numero_partido",
            conn, params=(jornada_seleccionada,)
        )
        conn.close()

        if len(partidos_df) > 0:
            # Botón de exportar pronósticos de esta jornada
            st.markdown("---")
            df_pronosticos_export, info_jornada_export = exportar_pronosticos_jornada(jornada_seleccionada)
            csv_pronosticos_export = df_pronosticos_export.to_csv(index=False).encode('utf-8')

            st.download_button(
                label="📥 Exportar Pronósticos para Auditoría",
                data=csv_pronosticos_export,
                file_name=f"pronosticos_jornada_{jornadas[jornadas['id'] == jornada_seleccionada]['numero'].iloc[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

            st.markdown("---")
            st.markdown("**Actualiza los resultados de los partidos:**")

            with st.form(key="form_actualizar_resultados"):
                resultados_nuevos = {}
                for idx, partido in partidos_df.iterrows():
                    st.markdown(f"**Partido {partido['numero_partido']}** {'⭐ (Doble)' if partido['es_doble'] else ''}")

                    # Extraer equipos del nombre (formato: "Equipo1 vs Equipo2")
                    nombre_partido = partido['nombre']
                    equipos = nombre_partido.split(' vs ') if ' vs ' in nombre_partido else [nombre_partido, '']

                    # Extraer resultado actual si existe
                    resultado_actual = str(partido['resultado_real']) if partido['resultado_real'] is not None and str(partido['resultado_real']).lower() != 'nan' else ""
                    goles = resultado_actual.split('-') if resultado_actual and '-' in resultado_actual else ['', '']

                    col_local, col_gol_local, col_vs, col_gol_visit, col_visitante = st.columns([3, 1, 0.5, 1, 3])

                    with col_local:
                        st.markdown(f"<div style='padding-top: 8px;'>{equipos[0] if len(equipos) > 0 else ''}</div>", unsafe_allow_html=True)

                    with col_gol_local:
                        gol_local = st.text_input(
                            f"Goles Local {partido['id']}",
                            value="",
                            placeholder=goles[0].strip() if len(goles) > 0 and goles[0].strip() else "0",
                            key=f"gol_local_update_{partido['id']}",
                            label_visibility="collapsed"
                        )

                    with col_vs:
                        st.markdown("<div style='text-align: center; padding-top: 8px;'>-</div>", unsafe_allow_html=True)

                    with col_gol_visit:
                        gol_visit = st.text_input(
                            f"Goles Visitante {partido['id']}",
                            value="",
                            placeholder=goles[1].strip() if len(goles) > 1 and goles[1].strip() else "0",
                            key=f"gol_visit_update_{partido['id']}",
                            label_visibility="collapsed"
                        )

                    with col_visitante:
                        st.markdown(f"<div style='padding-top: 8px;'>{equipos[1] if len(equipos) > 1 else ''}</div>", unsafe_allow_html=True)

                    # Construir resultado final
                    if gol_local.strip() and gol_visit.strip():
                        resultados_nuevos[partido['id']] = f"{gol_local.strip()}-{gol_visit.strip()}"
                    else:
                        resultados_nuevos[partido['id']] = ""

                submitted = st.form_submit_button("💾 Guardar Resultados", type="primary", use_container_width=True)

            if submitted:
                # Validar formatos
                errores = []
                for partido_id, resultado in resultados_nuevos.items():
                    if resultado.strip():
                        if '-' not in resultado or not all(x.strip().isdigit() for x in resultado.split('-')):
                            errores.append(f"Resultado con formato incorrecto: {resultado}")

                if errores:
                    for error in errores:
                        st.error(f"❌ {error}")
                else:
                    success = actualizar_resultados_jornada(jornada_seleccionada, resultados_nuevos)
                    if success:
                        st.success("✅ Resultados actualizados y puntos recalculados correctamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar resultados")
        else:
            st.warning("Esta jornada no tiene partidos registrados")

        # SECCIÓN DE ADMINISTRACIÓN: Eliminar Jornada
        st.markdown("---")
        st.markdown("### 🗑️ Zona de Administración")

        with st.expander("⚠️ Eliminar Jornada Completa", expanded=False):
            st.warning("""
            **ADVERTENCIA:** Esta acción eliminará permanentemente:
            - La jornada seleccionada
            - Todos los partidos de esta jornada
            - Todos los pronósticos de esta jornada

            Esta acción **NO se puede deshacer**.
            """)

            col_confirm1, col_confirm2 = st.columns(2)

            with col_confirm1:
                confirmar_texto = st.text_input(
                    "Escribe 'ELIMINAR' para confirmar",
                    key="confirmar_eliminar_jornada"
                )

            with col_confirm2:
                if st.button("🗑️ Eliminar Jornada Definitivamente", type="secondary", disabled=(confirmar_texto != "ELIMINAR")):
                    try:
                        conn = get_conn()
                        c = conn.cursor()

                        # Obtener IDs de partidos para eliminar pronósticos
                        c.execute("SELECT id FROM partidos WHERE jornada_id = ?", (jornada_seleccionada,))
                        partido_ids = [row[0] for row in c.fetchall()]

                        # Eliminar pronósticos
                        if partido_ids:
                            placeholders = ','.join(['?' for _ in partido_ids])
                            c.execute(f"DELETE FROM pronosticos WHERE partido_id IN ({placeholders})", partido_ids)

                        # Eliminar partidos
                        c.execute("DELETE FROM partidos WHERE jornada_id = ?", (jornada_seleccionada,))

                        # Eliminar jornada
                        c.execute("DELETE FROM jornadas WHERE id = ?", (jornada_seleccionada,))

                        conn.commit()
                        conn.close()

                        st.success(f"✅ Jornada '{jornada_info['nombre']}' eliminada correctamente")
                        st.balloons()
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error al eliminar jornada: {e}")

# TAB 6: CLASIFICACIONES
with tab6:
    st.header("🏆 Clasificaciones")

    # Obtener clasificación con o sin deuda según el rol
    clasificacion_general = get_clasificacion_general(incluir_deuda=is_admin)

    if len(clasificacion_general) > 0:
        # Clasificación General
        st.subheader("📊 Clasificación General del Mundial 2026")

        # Añadir posición
        clasificacion_general.insert(0, 'Posición', range(1, len(clasificacion_general) + 1))

        # Formatear columnas según el rol
        clasificacion_display = clasificacion_general.copy()

        if is_admin:
            # Admin ve todas las columnas incluyendo deuda
            clasificacion_display.columns = ['Posición', 'Participante', 'Puntos', 'Exactos',
                                             'Ganador+Dif', 'Solo Ganador', 'Jornadas Jugadas', 'Mejor Jornada',
                                             'Jornadas Sin Participar', 'Debe (€)']
            st.warning("⚠️ **Solo visible para admin:** Las columnas 'Jornadas Sin Participar' y 'Debe (€)' no son visibles para otros usuarios")
        else:
            # Usuarios normales no ven columnas de deuda
            clasificacion_display.columns = ['Posición', 'Participante', 'Puntos', 'Exactos',
                                             'Ganador+Dif', 'Solo Ganador', 'Jornadas', 'Mejor Jornada']

        st.dataframe(clasificacion_display, use_container_width=True, hide_index=True)

        # Botón de descarga
        csv = clasificacion_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Clasificación (CSV)",
            data=csv,
            file_name=f"clasificacion_mundial_2026_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

        st.markdown("---")

        # Clasificación por Jornada Individual
        st.subheader("📅 Clasificación por Jornada Individual")

        jornadas = get_jornadas()
        if len(jornadas) > 0:
            jornada_seleccionada = st.selectbox(
                "Selecciona una jornada",
                options=jornadas['id'].tolist(),
                format_func=lambda x: jornadas[jornadas['id'] == x]['nombre'].iloc[0],
                key="jornada_individual"
            )

            clasificacion_jornada = get_clasificacion_jornada(jornada_seleccionada)
            clasificacion_jornada.insert(0, 'Posición', range(1, len(clasificacion_jornada) + 1))
            clasificacion_jornada.columns = ['Posición', 'Participante', 'Puntos Jornada', 'Exactos', 'Ganador+Dif', 'Solo Ganador']

            st.dataframe(clasificacion_jornada, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Clasificación por Jornadas Personalizadas (NUEVO)
        st.subheader("🎯 Clasificación por Jornadas Personalizadas")
        st.markdown("*Selecciona múltiples jornadas para ver la clasificación acumulada (ideal para premios por bloques)*")

        if len(jornadas) > 0:
            # Multiselect de jornadas
            jornadas_seleccionadas = st.multiselect(
                "Selecciona las jornadas a incluir",
                options=jornadas['id'].tolist(),
                format_func=lambda x: f"Jornada {jornadas[jornadas['id'] == x]['numero'].iloc[0]} - {jornadas[jornadas['id'] == x]['nombre'].iloc[0]}",
                default=None,
                key="jornadas_personalizadas"
            )

            if len(jornadas_seleccionadas) > 0:
                # Obtener clasificación acumulada de las jornadas seleccionadas
                conn = get_conn()
                query = f"""
                    SELECT
                        p.participante,
                        SUM(p.puntos) as puntos_totales,
                        COUNT(CASE WHEN p.puntos > 0 THEN 1 END) as aciertos,
                        COUNT(p.id) as total_predicciones
                    FROM pronosticos p
                    INNER JOIN partidos pa ON p.partido_id = pa.id
                    WHERE pa.jornada_id IN ({','.join(['?']*len(jornadas_seleccionadas))})
                    GROUP BY p.participante
                    ORDER BY puntos_totales DESC
                """
                clasificacion_personalizada = pd.read_sql_query(query, conn, params=tuple(jornadas_seleccionadas))
                conn.close()

                # Mostrar jornadas incluidas
                nombres_jornadas = [jornadas[jornadas['id'] == jid]['nombre'].iloc[0] for jid in jornadas_seleccionadas]
                st.info(f"📊 **Jornadas incluidas:** {', '.join(nombres_jornadas)}")

                # Añadir posición
                clasificacion_personalizada.insert(0, 'Posición', range(1, len(clasificacion_personalizada) + 1))
                clasificacion_personalizada.columns = ['Posición', 'Participante', 'Puntos Acumulados', 'Aciertos', 'Total Pronósticos']

                # Mostrar clasificación
                st.dataframe(clasificacion_personalizada, use_container_width=True, hide_index=True)

                # Botón de descarga
                csv_personalizada = clasificacion_personalizada.to_csv(index=False).encode('utf-8')
                jornadas_nums = [str(jornadas[jornadas['id'] == jid]['numero'].iloc[0]) for jid in jornadas_seleccionadas]
                filename = f"clasificacion_jornadas_{'_'.join(jornadas_nums)}_{datetime.now().strftime('%Y%m%d')}.csv"

                st.download_button(
                    label="📥 Descargar Clasificación Personalizada (CSV)",
                    data=csv_personalizada,
                    file_name=filename,
                    mime="text/csv",
                    key="download_personalizada"
                )
            else:
                st.info("👆 Selecciona al menos una jornada para ver la clasificación acumulada")
    else:
        st.info("No hay datos de clasificación aún. Crea una jornada primero.")

# TAB 7: ESTADÍSTICAS
with tab7:
    st.header("📈 Estadísticas y Análisis")

    clasificacion = get_clasificacion_general()

    if len(clasificacion) > 0:
        # Evolución de puntos
        st.subheader("📊 Evolución de Puntos por Jornada")

        evolucion = get_evolucion_puntos()

        if len(evolucion) > 0:
            # Calcular puntos acumulados
            evolucion_acumulada = evolucion.pivot(index='jornada', columns='participante', values='puntos').fillna(0).cumsum()

            fig = go.Figure()

            for participante in evolucion_acumulada.columns:
                fig.add_trace(go.Scatter(
                    x=evolucion_acumulada.index,
                    y=evolucion_acumulada[participante],
                    mode='lines+markers',
                    name=participante,
                    line=dict(width=2),
                    marker=dict(size=8)
                ))

            fig.update_layout(
                title="Evolución de Puntos Acumulados",
                xaxis_title="Jornada",
                yaxis_title="Puntos Acumulados",
                hovermode='x unified',
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Estadísticas por participante
        st.subheader("👤 Estadísticas Individuales")

        participante_seleccionado = st.selectbox(
            "Selecciona un participante",
            options=clasificacion['participante'].tolist()
        )

        df_jornadas, df_stats = get_estadisticas_participante(participante_seleccionado)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Distribución de Puntuaciones**")
            stats = df_stats.iloc[0]

            fig_pie = go.Figure(data=[go.Pie(
                labels=['Exactos (12pts)', 'Exactos (10pts)', 'Ganador+Dif (6pts)', 'Solo Ganador (4pts)', 'Fallos (0pts)'],
                values=[stats['exactos_dif_mayor'], stats['exactos_dif_menor'],
                       stats['ganador_dif_correcta'], stats['solo_ganador'], stats['fallos']],
                hole=0.3
            )])

            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.markdown("**Puntos por Jornada**")

            fig_bar = px.bar(df_jornadas, x='numero', y='puntos',
                            labels={'numero': 'Jornada', 'puntos': 'Puntos'},
                            text='puntos')
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # Comparativa de participantes
        st.subheader("⚖️ Evolución de Participantes")

        # Multiselect para elegir participantes
        todos_participantes = clasificacion['participante'].tolist()

        participantes_seleccionados = st.multiselect(
            "Selecciona los participantes a comparar",
            options=todos_participantes,
            default=todos_participantes[:5] if len(todos_participantes) >= 5 else todos_participantes,
            help="Puedes seleccionar múltiples participantes para ver su evolución"
        )

        if len(participantes_seleccionados) > 0:
            # Obtener evolución de puntos
            evolucion = get_evolucion_puntos()

            if len(evolucion) > 0:
                # Filtrar solo los participantes seleccionados
                evolucion_filtrada = evolucion[evolucion['participante'].isin(participantes_seleccionados)]

                # Calcular puntos acumulados
                evolucion_acumulada = evolucion_filtrada.pivot(index='jornada', columns='participante', values='puntos').fillna(0).cumsum()

                # Crear gráfico de líneas
                fig = go.Figure()

                for participante in participantes_seleccionados:
                    if participante in evolucion_acumulada.columns:
                        fig.add_trace(go.Scatter(
                            x=evolucion_acumulada.index,
                            y=evolucion_acumulada[participante],
                            mode='lines+markers',
                            name=participante,
                            line=dict(width=3),
                            marker=dict(size=8)
                        ))

                fig.update_layout(
                    title=f"Evolución de Puntos Acumulados - {len(participantes_seleccionados)} Participantes",
                    xaxis_title="Jornada",
                    yaxis_title="Puntos Acumulados",
                    hovermode='x unified',
                    height=500,
                    showlegend=True
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de evolución disponibles aún")
        else:
            st.info("👆 Selecciona al menos un participante para ver su evolución")

    else:
        st.info("No hay estadísticas disponibles aún. Crea una jornada primero.")

# TAB 8: HISTÓRICO
if tab8 is not None:
  with tab8:
    st.header("📜 Histórico de Jornadas")

    jornadas = get_jornadas()

    # Filtrar jornadas según el rol
    if not is_admin:
        # Usuarios normales solo ven jornadas pasadas (excluir la jornada vigente)
        jornada_vigente = get_jornada_vigente()

        if jornada_vigente is not None:
            # Excluir la jornada vigente
            jornadas = jornadas[jornadas['id'] != jornada_vigente['id']]
            st.info("ℹ️ Solo se muestran jornadas finalizadas. La jornada en curso no es visible hasta que finalice.")

        # Si después de filtrar no hay jornadas, mostrar mensaje apropiado
        if len(jornadas) == 0:
            jornadas = pd.DataFrame()

    if len(jornadas) > 0:
        for _, jornada in jornadas.iterrows():
            with st.expander(f"{'⭐' if jornada['es_estrella'] else '📅'} {jornada['nombre']} - {jornada['fase']}"):
                st.markdown(f"**Fecha de creación:** {jornada['fecha']}")
                if jornada.get('fecha_fin'):
                    st.markdown(f"**Fecha del último partido:** {jornada['fecha_fin']}")
                st.markdown(f"**Tipo:** {'Jornada Estrella' if jornada['es_estrella'] else 'Jornada Normal'}")

                # Botón de exportar pronósticos (solo admin)
                if is_admin:
                    df_pronosticos, info_jornada = exportar_pronosticos_jornada(jornada['id'])
                    csv_pronosticos = df_pronosticos.to_csv(index=False).encode('utf-8')

                    st.download_button(
                        label="📥 Exportar Pronósticos de esta Jornada (Auditoría)",
                        data=csv_pronosticos,
                        file_name=f"pronosticos_jornada_{jornada['numero']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key=f"export_jornada_{jornada['id']}"
                    )

                st.markdown("---")

                # Mostrar clasificación de esa jornada
                clasificacion_j = get_clasificacion_jornada(jornada['id'])
                st.dataframe(clasificacion_j, use_container_width=True)

                # Mostrar detalles de partidos
                conn = get_conn()
                partidos_df = pd.read_sql_query(
                    "SELECT numero_partido, nombre, resultado_real, es_doble FROM partidos WHERE jornada_id = ?",
                    conn, params=(jornada['id'],)
                )
                conn.close()

                st.markdown("**Partidos:**")
                for _, partido in partidos_df.iterrows():
                    doble_text = " (⭐ Doble)" if partido['es_doble'] else ""
                    _res = partido['resultado_real']
                    _res = str(_res) if _res is not None and str(_res).lower() != 'nan' else None
                    resultado_text = f" - Resultado: {_res}" if _res else ""
                    st.markdown(f"- **Partido {partido['numero_partido']}:** {partido['nombre']}{doble_text}{resultado_text}")
    else:
        if is_admin:
            st.info("No hay jornadas registradas en el histórico.")
        else:
            st.info("No hay jornadas finalizadas aún para mostrar en el histórico.")

# TAB INFO (Solo visible para usuarios no autenticados o responsables)
if not is_admin and 'tab_info' in locals():
    with tab_info:
        st.header("ℹ️ Información de la Porra")

        st.markdown("""
        ### 📋 Sistema de Puntuación

        | Acierto | Puntos | Descripción |
        |---------|--------|-------------|
        | Resultado exacto (dif > 1) | **12** | Predices 3-0 y sale 3-0 |
        | Resultado exacto (dif ≤ 1) | **10** | Predices 1-0 y sale 1-0 o 1-1 y sale 1-1 |
        | Empate sin resultado exacto | **6** | Predices 1-1 y sale 2-2 |
        | Ganador + diferencia | **6** | Predices 2-0 y sale 3-1 (ambos +2 local) |
        | Solo ganador | **4** | Predices 1-0 y sale 3-1 (diferencias distintas) |
        | Fallo | **0** | Ganador incorrecto |

        ### ⭐ Jornadas Estrella

        En las **jornadas estrella**, un partido designado puntúa el **doble (x2)**.

        ### 🏆 Clasificaciones

        Puedes ver:
        - **Clasificación General**: Puntuación acumulada del torneo completo
        - **Clasificación por Jornada**: Resultados de cada jornada individual
        - **Estadísticas Detalladas**: Gráficos de evolución y análisis

        ### 📈 Estadísticas

        Consulta:
        - Evolución de puntos jornada a jornada
        - Estadísticas individuales de cada participante
        - Distribución de aciertos (12pts, 10pts, 6pts, 4pts, 0pts)
        - Comparativas entre participantes

        ### 📜 Histórico

        Revisa todas las jornadas pasadas con sus clasificaciones y resultados.

        ---

        ### 🔐 Acceso Administrador

        Si eres el administrador, ingresa tu contraseña en la barra lateral izquierda para acceder a:
        - **Gestión de Usuarios**: Añadir, editar, desactivar participantes
        - **Nueva Jornada**: Crear y configurar jornadas con partidos y pronósticos

        ---

        **¿Tienes dudas?** Contacta al administrador de la porra.
        """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "⚽ Porra Mundial 2026 | Desarrollado para los mejores pronósticos"
    "</div>",
    unsafe_allow_html=True
)
