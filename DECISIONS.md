# Decisiones técnicas del proyecto

Este documento registra las decisiones técnicas tomadas durante el desarrollo, el porqué de cada una, y los problemas que fuimos encontrando. Es parte clave del portafolio: muestra el proceso de pensamiento, no solo el resultado final.

---

## 1. Por qué Python

Se eligió Python como lenguaje principal del backend porque:
- Es el estándar de facto para proyectos de IA/RAG
- Tiene el ecosistema más maduro de librerías (LangChain, LlamaIndex, embeddings, etc.)
- Facilita la colaboración en equipo sobre un stack estandarizado en la industria de IA

## 2. Por qué Gemini API (+ Groq como fallback)

Alternativas evaluadas:
- Groq: se consideró primero por su velocidad de inferencia y nivel gratuito
- Gemini API: elegida como proveedor principal
- Ollama (local): gratis y sin límites, pero más lento y requiere buena RAM

Motivo del cambio: se evaluó Groq inicialmente por su velocidad, pero se decidió pasar a Gemini por consistencia de conocimiento dentro del equipo (uno de los integrantes ya tenía experiencia previa con esta API) y para reducir la fricción de arranque conjunto del proyecto.

Decisión de equipo: en vez de elegir uno solo, se decidió usar ambos proveedores:
- Fase 1 (arranque): implementar el flujo completo del RAG usando solo Gemini, para tener algo funcional rápido
- Fase 2 (mejora): agregar Groq como opción adicional, con un campo en la respuesta del backend que identifica qué modelo generó cada respuesta, y un selector en el frontend para que el usuario elija entre Gemini y Groq

Esto permite documentar una evolución real del proyecto y demuestra manejo de resiliencia entre proveedores de IA, algo valorado en sistemas de producción.

Estado: la Fase 1 está completa y en producción. La Fase 2 (integración de Groq) está en desarrollo activo.

## 3. Dominio de datos

Se eligió la documentación pública de la API de Stripe (https://docs.stripe.com) como fuente de conocimiento del asistente.

Motivo de la elección:
- Es un dominio inmediatamente reconocible para reclutadores y devs (a diferencia de un dominio muy nicho)
- Documentación pública, bien estructurada y de volumen suficiente para justificar chunking real
- Permite demos en vivo con preguntas técnicas concretas (ej. "cómo creo un customer con metadata")
- Refuerza el mensaje del proyecto: un asistente que ahorra tiempo de lectura de documentación técnica

Alcance inicial: (completar cuando se decida qué secciones específicas de la doc se van a indexar, ej. Payments, Customers, Webhooks, etc.)

## 4. Base de datos vectorial

Alternativas evaluadas:
- pgvector: elegida
- ChromaDB: más simple de levantar, pero menos alineada con stack de producción

Motivo de la elección: se optó por pgvector (extensión de PostgreSQL) por razones técnicas concretas:
- Menos infraestructura: no requiere un servicio de base de datos separado; los embeddings viven en el mismo PostgreSQL donde se guardan los demás datos del proyecto
- Consistencia transaccional: los chunks de texto, sus embeddings y su metadata (ej. de qué sección de la doc de Stripe provienen) se guardan en la misma transacción, evitando desincronización entre datos relacionales y vectoriales
- Búsquedas híbridas: permite combinar filtros SQL tradicionales (ej. WHERE seccion = 'Payments') con búsqueda por similitud vectorial en una sola query

Setup necesario: inicialmente se planeó usar Docker (imagen pgvector/pgvector) para levantar PostgreSQL + pgvector rápidamente. Sin embargo, Docker Desktop requiere soporte de virtualización habilitado en el BIOS, que no estaba disponible en el equipo de desarrollo. Se optó entonces por una alternativa igual de simple: Conda, que permite instalar PostgreSQL y pgvector ya compilados juntos con un solo comando (conda install -c conda-forge postgresql pgvector), sin depender de virtualización ni de compilar la extensión manualmente. Este cambio se documenta en la sección de Problemas encontrados.

## 5. Estrategia de chunking (troceo de documentos)

Se decidió trocear la documentación por endpoint de la API (cada combinación de ruta + método HTTP genera un chunk), en vez de usar un tamaño fijo de caracteres o tokens. Esto es posible porque la especificación OpenAPI de Stripe ya viene naturalmente segmentada por endpoint, y cada uno constituye una unidad de información autocontenida (ideal para RAG, ya que cada chunk responde a una pregunta concreta sobre un endpoint específico).

## 6. Frontend

Se eligió Streamlit como framework de frontend.

Motivo de la elección:
- Se escribe 100% en Python, sin necesidad de HTML/CSS/JS, lo que permite enfocar el esfuerzo de desarrollo en la lógica del RAG (retrieval + generación) en vez de en la interfaz
- Es el estándar de facto para demos de proyectos de IA/ML, fácilmente reconocible por reclutadores técnicos
- Permite armar rápidamente una interfaz de chat funcional, con historial de mensajes y visualización de la fuente citada debajo de cada respuesta
- Deploy simple y gratuito (Streamlit Community Cloud, o junto al backend en Railway/Render)



## 7. Deploy

Se eligió Render (plan Free, runtime Docker) para alojar la demo en vivo.

Motivo de la elección:
- Plan gratuito suficiente para una demo de portafolio (se duerme tras 15 minutos sin tráfico, tarda alrededor de 1 minuto en reactivarse)
- Permite levantar todo el stack (Streamlit + PostgreSQL con pgvector) en un solo contenedor Docker, sin necesitar servicios separados
- La base de datos vectorial se genera automáticamente durante el build del contenedor, corriendo el mismo pipeline del repo (descargar_stripe.py -> generar_embeddings.py), usando un secret para la API key que nunca queda expuesto dentro de la imagen

Demo en vivo: https://rag-asistente-docs.onrender.com

La guía completa para levantar una instancia propia está en DEPLOY.md.

## 8. Problemas encontrados

- Docker Desktop no pudo levantarse por falta de soporte de virtualización en el BIOS del equipo. Se resolvió instalando PostgreSQL + pgvector vía Conda en su lugar, evitando la dependencia de virtualización.
- Las claves de API de Gemini generadas después de mediados de 2026 vienen en un nuevo formato (empiezan con "AQ." en vez de "AIzaSy..."). El SDK oficial (google-genai) las soporta sin problema; el error inicial fue simplemente no haber guardado la clave real en el archivo .env (había quedado el texto de ejemplo).
- Estrategia de chunking: en vez de definir un tamaño de chunk fijo (caracteres/tokens), se optó por trocear por endpoint de la API (cada ruta + método HTTP = un chunk), ya que la especificación OpenAPI de Stripe ya viene naturalmente segmentada de esa forma y cada endpoint es una unidad de información autocontenida.
- La documentación de Stripe quedaba desactualizada: descargar_stripe.py no volvía a bajar la spec si ya existía, la demo solo la bajaba en el build (y Docker reutilizaba esa capa cacheada) y el upsert de generar_embeddings.py nunca borraba endpoints eliminados. Se resolvió comparando la versión de la spec (info.version) contra la publicada por Stripe, borrando los chunks que ya no existen y agregando un workflow diario que actualiza version_stripe.txt para disparar el rebuild de la demo.
