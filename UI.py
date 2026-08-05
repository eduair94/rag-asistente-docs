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

                if mensaje.get("error"):
                    st.error(f"{mensaje['error']}")
                else:
                    st.markdown(mensaje["contenido"])

                    fuentes = mensaje.get("fuentes")

                    if fuentes and isinstance(fuentes,dict):
                        with st.expander("ver fuentes consultadas"):
                            for num, fuente in fuentes.items():
                                st.write(f"**[{num}]** {fuente}")

#*...................................................................................................................../

    spinner_placeholder = st.empty()
                    
    with st.form(key="chat_form", clear_on_submit=True):
        pregunta = st.text_input("realice su pregunta:", label_visibility="collapsed", placeholder="realice su pregunta:")
        enviado = st.form_submit_button("Enviar", use_container_width=True)

if enviado and pregunta:
    st.session_state.historial.append({"rol": "user", "contenido": pregunta})

    with spinner_placeholder:
        with st.spinner("consultando la documentacion, porfavor espere"):
            resultado = responder_pregunta_mock(pregunta)

    if resultado.get("respuesta") == 0 or "errores" in resultado:
        mensaje_error = resultado.get("errores", {}).get("modelo_error", "no se pudo obtener una respuesta valida de la codumentacion")

        st.session_state.historial.append({
            "rol": "assistant",
            "contenido": "",
            "error": mensaje_error    
        })
    else:
        st.session_state.historial.append({
            "rol": "assistant",
            "contenido": resultado["respuesta"],
            "fuentes": resultado.get("fuentes", {})
        })

    st.rerun()
#*.........................................................................../