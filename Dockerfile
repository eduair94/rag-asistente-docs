# syntax=docker/dockerfile:1
# Demo en Render (plan free, runtime Docker): Streamlit + PostgreSQL/pgvector en un solo contenedor.
# La base vectorial se arma en el build con el pipeline del repo (descargar_stripe.py -> generar_embeddings.py)
# usando el secret file GEMINI_API_KEY, y queda horneada en la imagen (sin llamadas de embeddings al arrancar).
# En runtime la app lee la variable de entorno GEMINI_API_KEY.
FROM pgvector/pgvector:pg17

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root (UID 1000); PYTHONUNBUFFERED para que los print() de rag_ia lleguen a los logs de Render
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/venv/bin:$PATH" PGDATA=/home/user/pgdata PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requisitos.txt .
RUN python3 -m venv /home/user/venv \
    && pip install --no-cache-dir -r requisitos.txt streamlit==1.63.0

COPY --chown=user *.py estilo.css ./

# Misma configuración que la base local del README (puerto 5433, db rag_stripe, usuario postgres)
RUN --mount=type=secret,id=GEMINI_API_KEY,mode=0444,required=true \
    initdb -U postgres --auth=trust >/dev/null \
    && pg_ctl -o "-p 5433 -k /tmp" -w start \
    && createdb -h localhost -p 5433 -U postgres rag_stripe \
    && psql -h localhost -p 5433 -U postgres -d rag_stripe -c "CREATE EXTENSION vector;" \
    && mkdir -p .secreto && printf '{"claves_gemini": "%s"}' "$(cat /run/secrets/GEMINI_API_KEY)" > .secreto/claves_api.json \
    && for i in 1 2 3 4 5; do python descargar_stripe.py && break || sleep 10; done \
    && python generar_embeddings.py \
    && rm -rf .secreto datos \
    && pg_ctl -w stop

EXPOSE 7860
ENTRYPOINT []
# Logs de Postgres a archivo: el sondeo de puertos de Render genera "invalid length of startup packet" cada segundo
CMD pg_ctl -o "-p 5433 -k /tmp" -l /tmp/postgres.log -w start \
    && mkdir -p .secreto && printf '{"claves_gemini": "%s"}' "$GEMINI_API_KEY" > .secreto/claves_api.json \
    && exec streamlit run UI.py --server.port=7860 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
