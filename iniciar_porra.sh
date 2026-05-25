#!/bin/bash

echo "🏆 Iniciando Porra Mundial 2026..."
echo ""

# Verificar si streamlit está instalado
if ! command -v streamlit &> /dev/null
then
    echo "⚠️  Streamlit no está instalado. Instalando dependencias..."
    pip3 install -r requirements.txt
    echo ""
fi

echo "🚀 Abriendo aplicación..."
streamlit run porra_mundial_2026.py
