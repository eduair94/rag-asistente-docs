# rag-asistente-docs

Asistente conversacional basado en RAG (Retrieval-Augmented Generation) que responde preguntas sobre un conjunto de documentos reales, citando la fuente exacta en vez de inventar respuestas.

## Objetivo del proyecto

Este proyecto fue creado como pieza de portafolio para búsqueda de empleo en IT (2026). Busca demostrar:
- Comprensión práctica de RAG (no solo teoría)
- Un producto desplegado y usable, no un notebook
- Documentación clara de decisiones técnicas (ver DECISIONS.md)

## Dominio de datos

El asistente responde preguntas sobre la documentación oficial de la API de Stripe (https://docs.stripe.com), citando la página/sección exacta de la que sale cada respuesta.

Casos de uso de ejemplo:
- "¿Cómo creo un customer con metadata en Stripe?"
- "¿Qué diferencia hay entre PaymentIntent y Charge?"
- "¿Cómo manejo webhooks de Stripe en Python?"

## Stack tecnológico

| Componente | Elección | Estado |
|---|---|---|
| Backend | Python (FastAPI) | Decidido |
| API de IA | Gemini (+ Groq como fallback, fase 2) | Decidido |
| Base de datos vectorial | pgvector | Decidido |
| Frontend | Streamlit | Decidido |
| Deploy | Render (plan Free, Docker) — ver [DEPLOY.md](DEPLOY.md) | Decidido |

Ver el razonamiento completo detrás de cada elección en DECISIONS.md.

## Cómo correrlo (local)
* 1. Clonar el repo
```bash
git clone https://github.com/guadalupealba/rag-asistente-docs.git
cd rag-asistente-docs
```

* 2. Descargar Miniconda
```bash
A=$(uname -m) && F=$([ "$A" = aarch64 ] && echo aarch64 || [ "$A" = x86_64 ] && echo x86_64 || echo armv7l) && wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-$F.sh" -O miniconda.sh && bash miniconda.sh -b -p "$HOME/miniconda3" && "$HOME/miniconda3/bin/conda" init bash
 # Este comando de Linux hace la detección automática de la arquitectura del sistema y instalar la versión de miniconda adecuada
```

* 3. Instalar dependencias
```bash
pip install -r requisitos.txt
```

* 4. Guardar el API Gemini 
```bash
mkdir -p .secreto && echo '{"claves_gemini": "< el API de gemini aquí>"}' > .secreto/.claves_api.json
```

# 5. Levantar PostgreSQL + pgvector (via Conda)
```bash
conda create -n rag-db -c conda-forge postgresql pgvector -y
conda activate rag-db
initdb -D <RUTA QUE ELIJES> -U postgres -W
pg_ctl -D <ESA MISMA RUTA> -o "-p 5433" start
createdb -U postgres -p 5433 rag_stripe
psql -U postgres -p 5433 -d rag_stripe -c "CREATE EXTENSION vector;"
```

```bash
# 6. Descargar y procesar la documentacion de Stripe
python descargar_stripe_docs.py

# 7. Generar embeddings y guardarlos en pgvector
python generar_embeddings.py

# 8. Probar que la busqueda funciona
python rag_ia.py "como creo un customer con metadata"

# 9. Correr el servidor
uvicorn main:app --reload
```

## Autores

- Guadalupe Alba - [@guadalupealba](https://github.com/guadalupealba)
- Mugen - [@moneythemoney999](https://github.com/moneythemoney999)

## Demo

- Demo en vivo: https://rag-asistente-docs.onrender.com (plan Free de Render: si estuvo inactiva, tarda alrededor de 1 minuto en despertar)
- Cómo desplegar tu propia demo: ver [DEPLOY.md](DEPLOY.md)
- Pendiente: link al video demo de 2 minutos
