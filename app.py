import streamlit as st
import time #!esta libreria solo esta puesta como prueba para retrasar cada mensaje y asi probar ciertos parametros

#*Configuración de la página........................................................./

st.set_page_config(page_title="Asistente Stripe RAG", page_icon="💳")

#*def_cargar_css....................................../

from funciones import cargar_css 
cargar_css() 

#*.................................................../

BACKEND_URL = "http://localhost:8000/preguntar"  
#*................................................../

if "historial" not in st.session_state:
        st.session_state.historial = []

#*................................................................................../
main_container = st.container()

with main_container:
    st.title("Documentacion de Stripe")
    st.caption("realiza alguna pregunta relacionada sobre la API de STRIFE y el asistente le respondera")

#*def responder_pregunta_mock................./

    from funciones import responder_pregunta_mock

#*for_para_los_mensajes_del_historial................................................................................./
    chat_container = st.container(height=520)
    with chat_container:
        for mensaje in st.session_state.historial:
            with st.chat_message(mensaje["rol"]):
                st.markdown(mensaje["contenido"])
                if mensaje.get("fuente"):
                    with st.expander("Ver fuente"):
                        st.write(f"**Fuente:** {mensaje['fuente']}")
                        st.write(f"**Sección:** {mensaje['seccion']}")

    spinner_placeholder = st.empty()
                    
    with st.form(key="chat_form", clear_on_submit=True):
        pregunta = st.text_input("realice su pregunta:", label_visibility="collapsed", placeholder="realice su pregunta:")
        enviado = st.form_submit_button("Enviar", use_container_width=True)

if enviado and pregunta:
    st.session_state.historial.append({"rol": "user", "contenido": pregunta})

    with spinner_placeholder:
        with st.spinner("consultando la documentacion, porfavor espere"):
            resultado = responder_pregunta_mock(pregunta)

    st.session_state.historial.append({
        "rol": "assistant",
        "contenido": resultado["respuesta"],
        "fuente": resultado["fuente"],
        "seccion": resultado["seccion"],
    })
    st.rerun()
#*.........................................................................../