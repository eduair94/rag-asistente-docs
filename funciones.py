import time 
import streamlit as st




#*funciones................................................................................................./

def responder_pregunta_mock(pregunta):
    time.sleep(2.0)#!alteramos el tiempo en que responde la funcion para realizar pruebas visuales de espera    
    return {
        "respuesta": (
            "Para crear un customer con metadata en Stripe, hacés un POST a "
            "/v1/customers incluyendo el parámetro 'metadata' como un diccionario "
            "de pares clave-valor (por ejemplo: metadata={'plan': 'premium'})."
        ),
       "fuentes": {
            "1": "Stripe API docs: POST /v1/customers",
            "2": "Stripe API docs: Metadata Overview"
       }
    }
#*........................................................................................................./

def cargar_css(ruta_archivo="estilo.css"):
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True) #!funcion que invoca el estilo.css para el codigo fuente