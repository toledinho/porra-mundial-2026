"""
Módulo de conexión a base de datos
Soporta SQLite local y Turso (SQLite en la nube)
"""
import os
import streamlit as st

# Determinar si usar Turso o SQLite local
USE_TURSO = os.getenv("USE_TURSO", "false").lower() == "true"

if USE_TURSO:
    # Usar Turso (en producción)
    try:
        import libsql_client
        import asyncio

        TURSO_URL = st.secrets.get("TURSO_URL", os.getenv("TURSO_URL"))
        TURSO_TOKEN = st.secrets.get("TURSO_TOKEN", os.getenv("TURSO_TOKEN"))

        if not TURSO_URL or not TURSO_TOKEN:
            raise ValueError("TURSO_URL y TURSO_TOKEN deben estar configurados")

        # Cliente de Turso global
        _turso_client = None

        def get_turso_client():
            global _turso_client
            if _turso_client is None:
                _turso_client = libsql_client.create_client_sync(
                    url=TURSO_URL,
                    auth_token=TURSO_TOKEN
                )
            return _turso_client

        def get_conn():
            """Retorna una conexión a Turso"""
            return TursoConnection(get_turso_client())

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
                    return tuple(self._results[0].values()) if hasattr(self._results[0], 'values') else self._results[0]
                return None

            def fetchall(self):
                if not self._results:
                    return []
                return [tuple(row.values()) if hasattr(row, 'values') else row for row in self._results]

            def close(self):
                pass

        print("✅ Usando Turso (base de datos en la nube)")

    except Exception as e:
        print(f"⚠️ Error al conectar con Turso: {e}")
        print("Usando SQLite local como fallback")
        USE_TURSO = False

if not USE_TURSO:
    # Usar SQLite local (en desarrollo)
    import sqlite3

    DB_PATH = "porra_mundial_2026.db"

    def get_conn():
        """Retorna una conexión a SQLite local"""
        return sqlite3.connect(DB_PATH)

    print("✅ Usando SQLite local")
