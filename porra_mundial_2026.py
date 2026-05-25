import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import io
import base64
from database import get_conn

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

    # Tabla de jornadas
    c.execute('''CREATE TABLE IF NOT EXISTS jornadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER NOT NULL,
        nombre TEXT,
        es_estrella INTEGER DEFAULT 0,
        fecha TEXT,
        fase TEXT
    )''')

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

def crear_jornada(numero, nombre, es_estrella, fase="Fase de Grupos", num_partidos=None):
    """Crea una nueva jornada"""
    conn = get_conn()
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO jornadas (numero, nombre, es_estrella, fecha, fase) VALUES (?, ?, ?, ?, ?)",
              (numero, nombre, es_estrella, fecha, fase))
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
    """Actualiza los resultados reales y recalcula puntos"""
    conn = get_conn()
    c = conn.cursor()

    try:
        # Actualizar resultados de partidos
        for partido_id, resultado in resultados.items():
            c.execute("UPDATE partidos SET resultado_real = ? WHERE id = ?", (resultado, partido_id))

            # Obtener si es partido doble
            c.execute("SELECT es_doble FROM partidos WHERE id = ?", (partido_id,))
            es_doble = c.fetchone()[0]

            # Recalcular puntos de todos los pronósticos de este partido
            c.execute("SELECT id, prediccion FROM pronosticos WHERE partido_id = ?", (partido_id,))
            pronosticos = c.fetchall()

            for pron_id, prediccion in pronosticos:
                puntos = calcular_puntos(prediccion, resultado)
                if es_doble:
                    puntos *= 2
                c.execute("UPDATE pronosticos SET puntos = ? WHERE id = ?", (puntos, pron_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def get_clasificacion_jornada(jornada_id):
    """Obtiene la clasificación de una jornada específica"""
    conn = get_conn()
    query = """
        SELECT
            p.participante,
            SUM(p.puntos) as puntos_totales,
            COUNT(CASE WHEN p.puntos > 0 THEN 1 END) as aciertos,
            COUNT(p.id) as total_predicciones
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        WHERE pa.jornada_id = ?
        GROUP BY p.participante
        ORDER BY puntos_totales DESC
    """
    df = pd.read_sql_query(query, conn, params=(jornada_id,))
    conn.close()
    return df

def get_clasificacion_general():
    """Obtiene la clasificación general del torneo"""
    conn = get_conn()
    query = """
        SELECT
            p.participante,
            SUM(p.puntos) as puntos_totales,
            COUNT(CASE WHEN p.puntos > 0 THEN 1 END) as aciertos,
            COUNT(p.id) as total_predicciones,
            COUNT(DISTINCT pa.jornada_id) as jornadas_jugadas,
            ROUND(AVG(p.puntos), 2) as promedio_puntos,
            MAX(p.puntos) as mejor_pronostico
        FROM pronosticos p
        INNER JOIN partidos pa ON p.partido_id = pa.id
        GROUP BY p.participante
        ORDER BY puntos_totales DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_jornadas():
    """Obtiene todas las jornadas"""
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM jornadas ORDER BY numero DESC", conn)
    conn.close()
    return df

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
                data_export[col_resultado].append(pron.iloc[0]['resultado_real'] if pron.iloc[0]['resultado_real'] else 'Pendiente')
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

# Header
st.markdown('<div class="main-header">⚽ Porra Mundial 2026 ⚽</div>', unsafe_allow_html=True)

# Tabs principales
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Inicio",
    "👥 Usuarios",
    "➕ Nueva Jornada",
    "⚽ Resultados",
    "🏆 Clasificaciones",
    "📈 Estadísticas",
    "📜 Histórico"
])

# TAB 1: INICIO
with tab1:
    st.header("Resumen del Torneo")

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

        clasificacion = get_clasificacion_general()

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

        # Top 5
        st.subheader("🏆 Top 5 Clasificación General")
        if len(clasificacion) > 0:
            top5 = clasificacion.head(5).copy()
            top5.index = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][:len(top5)]
            st.dataframe(top5, use_container_width=True)

        # Última jornada
        st.subheader(f"📅 Última Jornada: {jornadas_df.iloc[0]['nombre']}")
        ultima_jornada_id = jornadas_df.iloc[0]['id']
        clasificacion_ultima = get_clasificacion_jornada(ultima_jornada_id)
        st.dataframe(clasificacion_ultima, use_container_width=True)
    else:
        st.info("👋 ¡Bienvenido! No hay jornadas registradas aún. Ve a la pestaña 'Nueva Jornada' para comenzar.")

# TAB 2: USUARIOS
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
                st.markdown(f"**Total usuarios activos:** {len(usuarios_df[usuarios_df['activo'] == 1])}")

            with col_export:
                # Exportar solo nombres de usuarios activos
                usuarios_export = usuarios_df[usuarios_df['activo'] == 1][['nombre']].copy()
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
            usuarios_activos = usuarios_df[usuarios_df['activo'] == 1]['nombre'].tolist()

            if usuarios_activos:
                usuario_editar = st.selectbox("Selecciona usuario a editar", usuarios_activos, key="select_editar")
                nuevo_nombre_edit = st.text_input("Nuevo nombre", value=usuario_editar, key="input_nuevo_nombre")

                if st.button("💾 Guardar Cambio", type="primary"):
                    if nuevo_nombre_edit.strip() and nuevo_nombre_edit.strip() != usuario_editar:
                        success, mensaje = actualizar_nombre_usuario(usuario_editar, nuevo_nombre_edit.strip())
                        if success:
                            st.success(mensaje)
                            st.experimental_rerun()
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
                    st.experimental_rerun()
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
                    st.experimental_rerun()
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
                        st.experimental_rerun()
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
                st.experimental_rerun()
            else:
                st.error(mensaje)

# TAB 3: NUEVA JORNADA
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
            col_nombre, col_resultado = st.columns([3, 1])

            with col_nombre:
                nombre_partido = st.text_input(
                    f"Nombre del partido {i+1}",
                    placeholder="Ej: España vs Alemania",
                    key=f"partido_nombre_{i}",
                    label_visibility="collapsed"
                )

            with col_resultado:
                resultado = st.text_input(
                    f"Resultado {i+1}",
                    placeholder="Ej: 2-1",
                    key=f"partido_resultado_{i}",
                    label_visibility="collapsed"
                )

            partidos_data.append({
                'numero': i + 1,
                'nombre': nombre_partido,
                'resultado': resultado,
                'es_doble': es_estrella and partido_doble == i + 1
            })

        st.markdown("---")
        st.markdown("### 📁 Paso 3: Cargar Pronósticos de Participantes")

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

        # Validaciones antes de crear
        if st.button("🚀 Crear Jornada", type="primary", disabled=not archivo):
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
                    # Crear jornada
                    jornada_id = crear_jornada(numero_jornada, nombre_jornada, 1 if es_estrella else 0, fase)

                    # Crear partidos manualmente
                    conn = get_conn()
                    c = conn.cursor()

                    partidos_ids = []
                    for p in partidos_validos:
                        c.execute("""INSERT INTO partidos (jornada_id, numero_partido, nombre, resultado_real, es_doble)
                                    VALUES (?, ?, ?, ?, ?)""",
                                 (jornada_id, p['numero'], p['nombre'], p['resultado'] if p['resultado'].strip() else None, 1 if p['es_doble'] else 0))
                        partidos_ids.append(c.lastrowid)

                    conn.commit()
                    conn.close()

                    # Procesar archivo de pronósticos
                    success, message = procesar_archivo_pronosticos(archivo, jornada_id, partidos_ids, partidos_validos)

                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")

# TAB 4: RESULTADOS (Actualizar resultados de jornadas existentes)
with tab4:
    st.header("⚽ Actualizar Resultados de Partidos")

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

            resultados_nuevos = {}
            for idx, partido in partidos_df.iterrows():
                col_nombre, col_resultado = st.columns([3, 1])

                with col_nombre:
                    st.markdown(f"**Partido {partido['numero_partido']}:** {partido['nombre']} {'⭐ (Doble)' if partido['es_doble'] else ''}")

                with col_resultado:
                    resultado_actual = partido['resultado_real'] if partido['resultado_real'] else ""
                    resultado_nuevo = st.text_input(
                        f"Resultado",
                        value=resultado_actual,
                        placeholder="Ej: 2-1",
                        key=f"resultado_update_{partido['id']}",
                        label_visibility="collapsed"
                    )
                    resultados_nuevos[partido['id']] = resultado_nuevo

            if st.button("💾 Guardar Resultados", type="primary"):
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
                        st.experimental_rerun()
                    else:
                        st.error("❌ Error al actualizar resultados")
        else:
            st.warning("Esta jornada no tiene partidos registrados")

# TAB 5: CLASIFICACIONES
with tab5:
    st.header("🏆 Clasificaciones")

    clasificacion_general = get_clasificacion_general()

    if len(clasificacion_general) > 0:
        # Clasificación General
        st.subheader("📊 Clasificación General del Mundial 2026")

        # Añadir posición
        clasificacion_general.insert(0, 'Posición', range(1, len(clasificacion_general) + 1))

        # Formatear columnas
        clasificacion_display = clasificacion_general.copy()
        clasificacion_display.columns = ['#', 'Participante', 'Puntos', 'Aciertos',
                                         'Total Pronósticos', 'Jornadas', 'Promedio', 'Mejor Pronóstico']

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

        # Clasificación por Jornada
        st.subheader("📅 Clasificación por Jornada")

        jornadas = get_jornadas()
        if len(jornadas) > 0:
            jornada_seleccionada = st.selectbox(
                "Selecciona una jornada",
                options=jornadas['id'].tolist(),
                format_func=lambda x: jornadas[jornadas['id'] == x]['nombre'].iloc[0]
            )

            clasificacion_jornada = get_clasificacion_jornada(jornada_seleccionada)
            clasificacion_jornada.insert(0, 'Posición', range(1, len(clasificacion_jornada) + 1))
            clasificacion_jornada.columns = ['#', 'Participante', 'Puntos Jornada', 'Aciertos', 'Total Pronósticos']

            st.dataframe(clasificacion_jornada, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos de clasificación aún. Crea una jornada primero.")

# TAB 6: ESTADÍSTICAS
with tab6:
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
        st.subheader("⚖️ Comparativa de Participantes")

        fig_compare = px.bar(clasificacion.head(10),
                            x='participante',
                            y='puntos_totales',
                            color='puntos_totales',
                            labels={'participante': 'Participante', 'puntos_totales': 'Puntos Totales'},
                            title='Top 10 Participantes')

        st.plotly_chart(fig_compare, use_container_width=True)

    else:
        st.info("No hay estadísticas disponibles aún. Crea una jornada primero.")

# TAB 7: HISTÓRICO
with tab7:
    st.header("📜 Histórico de Jornadas")

    jornadas = get_jornadas()

    if len(jornadas) > 0:
        for _, jornada in jornadas.iterrows():
            with st.expander(f"{'⭐' if jornada['es_estrella'] else '📅'} {jornada['nombre']} - {jornada['fase']}"):
                st.markdown(f"**Fecha:** {jornada['fecha']}")
                st.markdown(f"**Tipo:** {'Jornada Estrella' if jornada['es_estrella'] else 'Jornada Normal'}")

                # Botón de exportar pronósticos
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
                    resultado_text = f" - Resultado: {partido['resultado_real']}" if partido['resultado_real'] else ""
                    st.markdown(f"- **Partido {partido['numero_partido']}:** {partido['nombre']}{doble_text}{resultado_text}")
    else:
        st.info("No hay jornadas registradas en el histórico.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "⚽ Porra Mundial 2026 | Desarrollado para los mejores pronósticos"
    "</div>",
    unsafe_allow_html=True
)
