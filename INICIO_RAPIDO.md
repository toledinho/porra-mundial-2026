# 🚀 Inicio Rápido - Porra Mundial 2026

## Primer Uso

### 1. Instalar dependencias
```bash
pip3 install -r requirements.txt
```

### 2. Iniciar la aplicación
```bash
streamlit run porra_mundial_2026.py
```

O simplemente:
```bash
./iniciar_porra.sh
```

### 3. Primer paso: Registrar usuarios

1. Abre la pestaña **"👥 Usuarios"**
2. Puedes:
   - Añadir usuarios uno por uno con el formulario
   - Cargar el archivo `ejemplo_usuarios.csv` para empezar rápido

### 4. Segundo paso: Crear tu primera jornada

1. Ve a **"➕ Nueva Jornada"**
2. Completa los datos básicos
3. Sube un archivo con los pronósticos (puedes usar `ejemplo_jornada.csv` como referencia)
4. ¡Listo! Ya puedes ver clasificaciones y estadísticas

---

## Uso Semanal

### Cada semana deberás:

1. **Actualizar usuarios** (si hay cambios):
   - Ve a "👥 Usuarios"
   - Añade nuevos participantes
   - Desactiva usuarios que no juegan esta semana

2. **Crear nueva jornada**:
   - Prepara un archivo Excel/CSV con:
     - Columna 1: Participante (nombres exactos)
     - Columnas siguientes: Pred1, Pred2, Pred3... (formato X-X)
   - Ve a "➕ Nueva Jornada"
   - Completa el formulario
   - Si es jornada estrella, marca la casilla y selecciona qué partido puntúa doble
   - Sube el archivo

3. **Ver resultados**:
   - "📊 Inicio": Resumen rápido
   - "🏆 Clasificaciones": Rankings completos
   - "📈 Estadísticas": Gráficos y análisis
   - "📜 Histórico": Todas las jornadas anteriores

---

## Formato de Archivo de Jornada

### Ejemplo CSV:
```
Participante,Pred1,Pred2,Pred3,Pred4,Pred5
Juan Pérez,2-1,0-0,1-1,3-0,2-2
María García,1-1,1-0,2-1,2-1,1-1
Carlos López,2-0,1-1,0-0,1-0,3-1
```

### Ejemplo Excel:
| Participante  | Pred1 | Pred2 | Pred3 | Pred4 | Pred5 |
|---------------|-------|-------|-------|-------|-------|
| Juan Pérez    | 2-1   | 0-0   | 1-1   | 3-0   | 2-2   |
| María García  | 1-1   | 1-0   | 2-1   | 2-1   | 1-1   |
| Carlos López  | 2-0   | 1-1   | 0-0   | 1-0   | 3-1   |

**Importante:**
- Los nombres deben coincidir exactamente con los usuarios registrados
- Formato de predicciones: `X-X` (ej: `2-1`, `0-0`)
- Puedes tener cualquier número de partidos (no solo 5)

---

## Sistema de Puntuación

- **12 puntos**: Resultado exacto con diferencia > 1 gol
- **10 puntos**: Resultado exacto con diferencia de 1 gol o empate
- **6 puntos**: Acertaste empate (pero no el resultado exacto) O ganador + diferencia correcta
- **4 puntos**: Solo acertaste el ganador
- **0 puntos**: Ganador incorrecto

### Jornadas Estrella
Un partido puntúa el doble (x2). Tú eliges cuál al crear la jornada.

---

## Tips

✅ Haz backup del archivo `porra_mundial_2026.db` regularmente
✅ Usa nombres consistentes en los archivos
✅ Revisa los nombres en "👥 Usuarios" antes de subir una jornada
✅ Los archivos de ejemplo te ayudan a entender el formato correcto

---

## ¿Problemas?

- **"Usuario no registrado"**: El nombre no coincide. Revisa en la pestaña Usuarios.
- **Error al cargar archivo**: Verifica el formato (CSV o Excel, primera columna "Participante").
- **La app no abre**: Asegúrate de instalar las dependencias con `pip3 install -r requirements.txt`.

---

**¡Disfruta de la Porra Mundial 2026! ⚽🏆**
