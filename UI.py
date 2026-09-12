import streamlit as st
import time #!esta libreria solo esta puesta como prueba para retrasar cada mensaje y asi probar ciertos parametros
import json

#*Configuracion_de la_pagina........................................................./

st.set_page_config(
    page_title="Asistente Stripe RAG", 
    page_icon="💳",
    initial_sidebar_state="collapsed"
)

#*def_cargar_css....................................../

from funciones import cargar_css    
cargar_css() 

#*.................................................../

BACKEND_URL = "http://localhost:8000/preguntar"  
#*................................................../

if "historial" not in st.session_state:
    st.session_state.historial = []

if "pregunta_sugerida" not in st.session_state:
    st.session_state.pregunta_sugerida = ""

#*......opciones_del_chat............................................................/

with st.sidebar:
    st.title("⚙️ Opciones")
    
    #Status del backend
    st.success("● Servidor Conectado", icon="🟢")
    
    #Selector de Modelo IA 
    modelo_seleccionado = st.selectbox(
        "🤖 Modelo de IA:",
        options=["gemini", "groq"],
        index=0,
        help="Selecciona el proveedor de IA para procesar la consulta."
    )
    
    st.divider()

    #Boton para reiniciar el chat
    if st.button("🗑️ Limpiar conversacion", use_container_width=True):
        st.session_state.historial = []
        st.rerun()

    #Boton para exportar el chat en JSON
    if st.session_state.historial:
        historial_json = json.dumps(st.session_state.historial, indent=4, ensure_ascii=False)
        
        st.download_button(
            label="📥 Descargar historial",
            data=historial_json,
            file_name="historial_chat_stripe.json",
            mime="application/json",
            use_container_width=True
        )

#*................................................................................../
main_container = st.container()

with main_container:
    st.title("Documentacion de Stripe")
    st.caption("Realiza alguna pregunta relacionada sobre la API de Stripe y el asistente te respondera")
    
#* Disclaimer visible de uso gratuito.............................................../

    st.info(" **Nota de Demo:** Esta version utiliza una API local gratuita, si se supera el limite de solicitudes por minuto, la respuesta podria tardar o mostrar un error temporal.", icon="ℹ️")

#*def_responder_pregunta (RAG real: Gemini + pgvector via rag_ia)................./

    from rag_ia import generar_respuesta

    def responder_pregunta(pregunta):
        # Historial previo (pares pregunta/respuesta sin error) en el formato de rag_ia: roles "user"/"model"
        previos = st.session_state.historial[:-1]
        historial = []
        for preg, resp in zip(previos[::2], previos[1::2]):
            if not resp.get("error"):
                historial += [{"rol": "user", "contenido": preg["contenido"]}, {"rol": "model", "contenido": resp["contenido"]}]

        r = generar_respuesta({"pregunta": {"texto": pregunta, "historial": historial}})["respuesta"]
        resultado = {"respuesta": r["texto"], "fuentes": r["fuentes"] or {}, "modelo": r["modelo_de_ia"]["modelo"]}
        if r.get("errores"):
            resultado["errores"] = {"modelo_error": next(iter(r["errores"].values()))}
        return resultado

#*for_para_los_mensajes_del_historial................................................................................./

    chat_container = st.container(height=460)
    with chat_container:
        for mensaje in st.session_state.historial:
            with st.chat_message(mensaje["rol"]):

                if mensaje.get("error"):
                    st.error(f"{mensaje['error']}")
                else:
                    st.markdown(mensaje["contenido"])

                    # Mostrar que modelo respondio si viene en la respuesta
                    if mensaje.get("modelo"):
                        st.caption(f"🤖 Respondido por: **{mensaje['modelo'].upper()}**")

                    fuentes = mensaje.get("fuentes")

                    if fuentes and isinstance(fuentes, dict):
                        with st.expander("Ver fuentes consultadas"):
                            for num, fuente in fuentes.items():
                                st.write(f"**[{num}]** {fuente}")

#*Preguntas_sugeridas_(Quick Prompts)................................................................. me               /

    st.markdown("**Sugerencias de busqueda:**")
    col1, col2, col3 = st.columns(3)

    if col1.button("💡 ¿Como creo un customer?", use_container_width=True):
        st.session_state.pregunta_sugerida = "¿Como creo un customer con metadata en Stripe?"
        st.rerun()

    if col2.button("💡 ¿Que es PaymentIntent?", use_container_width=True):
        st.session_state.pregunta_sugerida = "¿Que diferencia hay entre PaymentIntent y Charge?"
        st.rerun()

    if col3.button("💡 ¿Como uso Webhooks?", use_container_width=True):
        st.session_state.pregunta_sugerida = "¿Como manejo los eventos de webhooks en la API?"
        st.rerun()

#*Formulario_de_entrada.............................................................................................../

    spinner_placeholder = st.empty()
    
    texto_defecto = st.session_state.pregunta_sugerida
    st.session_state.pregunta_sugerida = "" 
                    
    with st.form(key="chat_form", clear_on_submit=True):
        pregunta = st.text_input(
            "realice su pregunta:", 
            value=texto_defecto, 
            label_visibility="collapsed", 
            placeholder="Realice su pregunta sobre la API..."
        )
        enviado = st.form_submit_button("Enviar", use_container_width=True)

if (enviado and pregunta) or texto_defecto:
    pregunta_a_enviar = pregunta if pregunta else texto_defecto

    st.session_state.historial.append({"rol": "user", "contenido": pregunta_a_enviar})

    with spinner_placeholder:
        with st.spinner("consultando la documentacion, porfavor espere"):
            try:
                resultado = responder_pregunta(pregunta_a_enviar)
            except Exception as e:
                resultado = {
                    "respuesta": 0,
                    "errores": {"modelo_error": f"Error de conexión con el servicio: {str(e)}"}
                }

    # Handler de errores mejorado
    if not resultado or resultado.get("respuesta") == 0 or "errores" in resultado:
        mensaje_error = "Ocurrió un error inesperado al procesar la solicitud."
        if isinstance(resultado, dict) and "errores" in resultado:
            errores = resultado.get("errores", {})
            if isinstance(errores, dict):
                mensaje_error = errores.get("modelo_error", mensaje_error)
            elif isinstance(errores, str):
                mensaje_error = errores

        st.session_state.historial.append({
            "rol": "assistant",
            "contenido": "",
            "error": f"⚠️ {mensaje_error}"    
        })
    else:
        st.session_state.historial.append({
            "rol": "assistant",
            "contenido": resultado["respuesta"],
            "fuentes": resultado.get("fuentes", {}),
            "modelo": resultado.get("modelo", modelo_seleccionado)
        })

    st.rerun()
#*.........................................................................../