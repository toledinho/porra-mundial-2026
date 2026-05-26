"""
Módulo de conexión a base de datos
Soporta SQLite local y Turso (SQLite en la nube)
"""
import os

# Variable global para caché
_USE_TURSO = None
_turso_module_loaded = False
_sqlite_module_loaded = False

def _check_use_turso():
    """Determina si usar Turso o SQLite local (evaluación lazy)"""
    global _USE_TURSO
    if _USE_TURSO is None:
        try:
            import streamlit as st
            _USE_TURSO = st.secrets.get("USE_TURSO", os.getenv("USE_TURSO", "false")).lower() == "true"
        except:
            _USE_TURSO = os.getenv("USE_TURSO", "false").lower() == "true"
    return _USE_TURSO

# Exponer para compatibilidad
class _UseTursoProxy:
    def __bool__(self):
        return _check_use_turso()
    def __repr__(self):
        return str(_check_use_turso())

USE_TURSO = _UseTursoProxy()

def get_conn():
    """Retorna una conexión a la base de datos (Turso o SQLite según configuración)"""
    if _check_use_turso():
        return _get_turso_conn()
    else:
        return _get_sqlite_conn()

def _get_turso_conn():
    """Retorna conexión a Turso"""
    global _turso_module_loaded

    if not _turso_module_loaded:
        try:
            global libsql_client
            import libsql_client
            _turso_module_loaded = True
            print("✅ Usando Turso (base de datos en la nube)")
        except Exception as e:
            print(f"⚠️ Error importando libsql_client: {e}")
            print("Fallback a SQLite local")
            return _get_sqlite_conn()

    try:
        import streamlit as st
        TURSO_URL = st.secrets.get("TURSO_URL", os.getenv("TURSO_URL"))
        TURSO_TOKEN = st.secrets.get("TURSO_TOKEN", os.getenv("TURSO_TOKEN"))

        if not TURSO_URL or not TURSO_TOKEN:
            raise ValueError("TURSO_URL y TURSO_TOKEN deben estar configurados")

        # Convertir libsql:// a https:// para usar HTTP en lugar de WebSocket
        http_url = TURSO_URL.replace("libsql://", "https://")

        client = libsql_client.create_client_sync(
            url=http_url,
            auth_token=TURSO_TOKEN
        )

        return TursoConnection(client)
    except Exception as e:
        print(f"⚠️ Error conectando a Turso: {e}")
        print("Fallback a SQLite local")
        return _get_sqlite_conn()

def _get_sqlite_conn():
    """Retorna conexión a SQLite local"""
    global _sqlite_module_loaded, sqlite3

    if not _sqlite_module_loaded:
        import sqlite3
        _sqlite_module_loaded = True
        print("✅ Usando SQLite local")

    DB_PATH = "porra_mundial_2026.db"
    return sqlite3.connect(DB_PATH)


# Clases wrapper para Turso
class TursoConnection:
    """Wrapper para hacer que Turso funcione como sqlite3.Connection"""
    def __init__(self, client):
        self.client = client

    def cursor(self):
        return TursoCursor(self.client)

    def commit(self):
        # Turso auto-commit por defecto
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class TursoCursor:
    """Wrapper para hacer que Turso funcione como sqlite3.Cursor"""
    def __init__(self, client):
        self.client = client
        self.lastrowid = None
        self._results = None
        self.description = None

    def execute(self, query, params=None):
        if params is None:
            params = []

        # Convertir tuplas a listas para Turso
        if isinstance(params, tuple):
            params = list(params)

        try:
            result = self.client.execute(query, params)

            # Manejar resultados
            if hasattr(result, 'rows'):
                self._results = result.rows
            else:
                self._results = []

            # Construir description para pandas (SIEMPRE necesario)
            # Turso devuelve cols como lista de dicts: [{"name": "id", "decltype": "INTEGER"}, ...]

            # DEBUG
            import streamlit as st
            st.write("🔍 DEBUG execute - type(result):", type(result))
            st.write("🔍 DEBUG execute - dir(result):", dir(result))
            st.write("🔍 DEBUG execute - hasattr cols:", hasattr(result, 'cols'))
            st.write("🔍 DEBUG execute - hasattr columns:", hasattr(result, 'columns'))

            # Intentar acceder a diferentes atributos
            for attr in ['cols', 'columns', 'column_names', 'fields', '_cols', '_columns']:
                if hasattr(result, attr):
                    st.write(f"🔍 DEBUG execute - result.{attr}:", getattr(result, attr))

            if hasattr(result, 'cols') and result.cols:
                # cols es una lista de objetos/dicts con atributo 'name'
                columns = []
                for col in result.cols:
                    if isinstance(col, dict):
                        # Si es un dict, acceder por clave
                        columns.append(col.get('name', 'unknown'))
                    elif hasattr(col, 'name'):
                        # Si es un objeto, acceder por atributo
                        columns.append(col.name)
                    else:
                        # Fallback
                        columns.append(str(col))
                st.write("🔍 DEBUG execute - columns extraídas:", columns)
                self.description = [(col, None, None, None, None, None, None) for col in columns]
            # Si no hay cols, intentar extraer de rows (menos confiable)
            elif self._results and len(self._results) > 0:
                if hasattr(self._results[0], 'keys'):
                    columns = list(self._results[0].keys())
                elif isinstance(self._results[0], dict):
                    columns = list(self._results[0].keys())
                else:
                    columns = [f"column_{i}" for i in range(len(self._results[0]))]
                self.description = [(col, None, None, None, None, None, None) for col in columns]
            # Si no hay ni cols ni rows, description vacía
            else:
                self.description = []

            # Obtener lastrowid si es un INSERT
            if query.strip().upper().startswith('INSERT'):
                if hasattr(result, 'last_insert_rowid'):
                    self.lastrowid = result.last_insert_rowid
        except Exception as e:
            print(f"Error ejecutando query: {e}")
            raise

        return self

    def fetchone(self):
        if self._results and len(self._results) > 0:
            row = self._results[0]
            # Turso rows son listas de objetos {"type": "...", "value": "..."}
            if isinstance(row, list):
                return tuple(cell['value'] if isinstance(cell, dict) and 'value' in cell else cell for cell in row)
            elif hasattr(row, 'values'):
                return tuple(row.values())
            else:
                return row
        return None

    def fetchall(self):
        if not self._results:
            return []
        results = []
        for row in self._results:
            # Turso rows son listas de objetos {"type": "...", "value": "..."}
            if isinstance(row, list):
                results.append(tuple(cell['value'] if isinstance(cell, dict) and 'value' in cell else cell for cell in row))
            elif hasattr(row, 'values'):
                results.append(tuple(row.values()))
            else:
                results.append(row)
        return results

    def close(self):
        pass
