# ⚽ Porra Mundial 2026

Aplicación web para gestionar una porra del Mundial de Fútbol 2026 con pronósticos y estadísticas completas.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.23+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 🌟 Características

- **Gestión de Usuarios**: Registro y administración de participantes
- **Jornadas Flexibles**: Cualquier número de partidos (1-20+)
- **Jornadas Estrella**: Partido que puntúa doble
- **Sistema de Puntuación Personalizado**:
  - 12 pts: Resultado exacto con diferencia > 1
  - 10 pts: Resultado exacto con diferencia = 1 o empate
  - 6 pts: Ganador + diferencia correcta O empate sin resultado exacto
  - 4 pts: Solo ganador correcto
  - 0 pts: Ganador incorrecto
- **Clasificaciones**: General y por jornada
- **Estadísticas Completas**: Gráficos de evolución, análisis individual
- **Exportación de Pronósticos**: Para auditoría en formato CSV
- **Base de Datos Persistente**: SQLite local o Turso en la nube

## 🚀 Demo en Vivo

[Ver aplicación desplegada](https://tu-app.streamlit.app) *(próximamente)*

## 📋 Requisitos

- Python 3.7+
- pip

## 🛠️ Instalación Local

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/porra-mundial-2026.git
cd porra-mundial-2026
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Ejecutar la aplicación**
```bash
streamlit run porra_mundial_2026.py
```

4. Abrir en el navegador: `http://localhost:8501`

## 📖 Guía de Uso

### 1. Registrar Usuarios

Ve a la pestaña **"👥 Usuarios"**:
- Añade usuarios individualmente o carga un CSV
- Edita, desactiva o reactiva usuarios
- Exporta la lista de nombres

**Formato CSV de usuarios:**
```csv
Nombre,Email
Juan Pérez,juan@mail.com
María García,maria@mail.com
```

### 2. Crear Jornada

Ve a **"➕ Nueva Jornada"**:

1. **Paso 1**: Información de la jornada (número, nombre, fase)
2. **Paso 2**: Configurar partidos
   - Define número de partidos
   - Marca si es jornada estrella
   - Ingresa nombre y resultado de cada partido
3. **Paso 3**: Carga archivo con pronósticos

**Formato CSV de pronósticos:**
```csv
Participante,Pred1,Pred2,Pred3,Pred4,Pred5
Juan Pérez,2-1,0-0,1-1,3-0,2-2
María García,1-1,1-0,2-1,2-1,1-1
```

### 3. Actualizar Resultados

Ve a **"⚽ Resultados"**:
- Selecciona una jornada
- Actualiza los resultados de los partidos
- Los puntos se recalculan automáticamente
- Exporta pronósticos para auditoría

### 4. Ver Clasificaciones y Estadísticas

- **"🏆 Clasificaciones"**: Rankings general y por jornada
- **"📈 Estadísticas"**: Gráficos de evolución, análisis individual
- **"📜 Histórico"**: Todas las jornadas pasadas con exportación

## 🌐 Despliegue en Streamlit Cloud

### Configuración

1. Haz fork del repositorio
2. Ve a [Streamlit Cloud](https://streamlit.io/cloud)
3. Conecta tu repositorio de GitHub
4. Configura los secretos (si usas Turso):

```toml
# En Streamlit Cloud: Settings > Secrets
TURSO_URL = "tu-url-de-turso"
TURSO_TOKEN = "tu-token-de-turso"
```

5. Activa Turso configurando variable de entorno:
```
USE_TURSO=true
```

### Base de Datos Persistente (Turso)

Para mantener el histórico en producción:

1. Crea cuenta gratuita en [Turso](https://turso.tech)
2. Crea una base de datos
3. Configura los secretos en Streamlit Cloud
4. La app creará las tablas automáticamente

## 📁 Estructura del Proyecto

```
porra-mundial-2026/
├── porra_mundial_2026.py    # Aplicación principal
├── database.py               # Módulo de conexión BD
├── requirements.txt          # Dependencias Python
├── README.md                # Este archivo
├── .gitignore               # Archivos a ignorar
├── ejemplo_usuarios.csv     # Plantilla de usuarios
├── ejemplo_jornada.csv      # Plantilla de pronósticos
└── .streamlit/
    └── secrets.toml         # Credenciales (no se sube a Git)
```

## 🔒 Seguridad

- Las credenciales de base de datos **NO** se suben a GitHub
- Usa `.streamlit/secrets.toml` para desarrollo local
- Configura secretos en Streamlit Cloud para producción
- Los datos de usuarios son privados por defecto

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👨‍💻 Autor

Desarrollado para la Porra Mundial 2026

## 🙏 Agradecimientos

- [Streamlit](https://streamlit.io/) - Framework de la aplicación
- [Turso](https://turso.tech/) - Base de datos en la nube
- [Plotly](https://plotly.com/) - Gráficos interactivos

---

**¡Disfruta de la Porra Mundial 2026! ⚽🏆**
