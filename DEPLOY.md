# Guía de despliegue de la demo (Render, plan Free)

Cómo levantar tu propia instancia pública del asistente, gratis, a partir de un fork de este repo. Tiempo estimado: 15 minutos.

Demo de referencia: https://rag-asistente-docs.onrender.com

## Qué se despliega

Un solo contenedor Docker (ver [`Dockerfile`](Dockerfile)) con:

- **Streamlit** (`UI.py`) escuchando en el puerto 7860.
- **PostgreSQL 17 + pgvector**, con la misma configuración que la base local del README (puerto 5433, base `rag_stripe`, usuario `postgres`). Por eso `rag_ia.py` funciona sin cambios.

La base vectorial se arma **durante el build**, con el mismo pipeline que en local:

```
descargar_stripe.py  ->  datos/chunks.json (82 endpoints)  ->  generar_embeddings.py  ->  tabla stripe_chunks (pgvector)
```

Queda guardada dentro de la imagen, así que al arrancar el contenedor no se llama a la API de embeddings. En runtime, cada pregunta hace 1 embedding de la consulta y 1 llamada de generación a Gemini.

## Requisitos

- Cuenta de GitHub, para el fork.
- API key gratuita de Gemini: https://aistudio.google.com/apikey
- Cuenta en Render: https://dashboard.render.com/register. El plan Free no pide tarjeta si el servicio se crea desde el dashboard (crearlo por la API de Render sí la exige).
- Opcional, para probar local: Docker.

## Paso a paso

### 1. Hacer el fork

Con el botón **Fork** de GitHub, o con la CLI:

```bash
gh repo fork guadalupealba/rag-asistente-docs --clone
```

### 2. Crear el Web Service en Render

En dashboard.render.com: **New → Web Service**.

| Campo | Valor |
|---|---|
| Source | Pestaña **Public Git Repository** → `https://github.com/<tu-usuario>/rag-asistente-docs` (o conectá tu cuenta de GitHub) |
| Branch | `main` |
| Language / Runtime | **Docker** (Render lo detecta por el `Dockerfile`) |
| Region | La más cercana a tu audiencia (por ejemplo Virginia) |
| Instance Type | **Free** |

> **Atención:** Render preselecciona un plan pago (0.5 CPU / 512 MB, figura como `0.5c-512mb`). Elegí **Free** explícitamente. Si ya lo creaste con el plan pago: **Settings → Instance Type → Free**.

### 3. Cargar variables y secretos

En la misma pantalla de creación (sección **Environment Variables / Advanced**) o después en la pestaña **Environment**:

| Tipo | Nombre | Valor | Para qué se usa |
|---|---|---|---|
| Environment Variable | `GEMINI_API_KEY` | tu API key | la app, en runtime |
| Environment Variable | `PORT` | `7860` | el puerto donde escucha Streamlit |
| Secret File | `GEMINI_API_KEY` | tu API key (el mismo valor) | solo el build, para generar los embeddings; no queda dentro de la imagen |

En **Advanced → Health Check Path**: `/_stcore/health`.

> Si el primer deploy arrancó antes de cargar el Secret File, el build falla en el paso `RUN --mount=type=secret,id=GEMINI_API_KEY ...`. Es esperado: cargalo y hacé **Manual Deploy → Deploy latest commit**.

### 4. Deploy

El build tarda entre 3 y 5 minutos: descarga la especificación OpenAPI de Stripe (~8 MB), genera los 82 embeddings y los guarda en pgvector. En los logs del build tenés que ver:

```
Se generaron 82 trozos.
¡Listo! Todos los embeddings se generaron y guardaron en pgvector.
```

Después aparece `Your service is live` junto con la URL pública `https://<nombre-del-servicio>.onrender.com`.

### 5. Verificar

- `https://<nombre-del-servicio>.onrender.com/_stcore/health` responde `ok`.
- En la UI, el botón **"¿Como creo un customer?"** devuelve una respuesta que cita `POST /v1/customers` y `metadata`, con "Respondido por: GEMINI-..." y el desplegable "Ver fuentes consultadas".
- En los logs de runtime, cada pregunta muestra `Buscando información de soporte...`.

## Probarlo local con Docker (opcional)

Es el mismo contenedor que corre en Render. Con tu key en la variable de entorno `GEMINI_API_KEY`:

```bash
# bash
export GEMINI_API_KEY="tu_api_key"
docker build --secret id=GEMINI_API_KEY,env=GEMINI_API_KEY -t rag-demo .
docker run --rm -e GEMINI_API_KEY -p 7860:7860 rag-demo
```

```powershell
# PowerShell
$env:GEMINI_API_KEY = "tu_api_key"
docker build --secret id=GEMINI_API_KEY,env=GEMINI_API_KEY -t rag-demo .
docker run --rm -e GEMINI_API_KEY -p 7860:7860 rag-demo
```

Abrí http://localhost:7860. El `Dockerfile` copia solo `*.py`, `estilo.css` y `requisitos.txt`, así que `.secreto/` y `.venv/` nunca terminan dentro de la imagen.

## Mantenimiento

- **Cambios de código:** hacé push a `main` y lanzá **Manual Deploy → Deploy latest commit**. Si conectaste tu cuenta de GitHub en vez de usar "Public Git Repository", Render despliega solo con cada push.
- **Actualizar la documentación de Stripe:** **Manual Deploy → Clear build cache & deploy**. Sin limpiar el caché, Docker reutiliza la capa donde ya están los embeddings.
- **Cambiar la API key:** editá `GEMINI_API_KEY` en **Environment** y también el Secret File, para que el próximo build use la nueva.

## Límites del plan Free

Tenelos en cuenta antes de mostrar la demo:

- **Se duerme tras 15 minutos sin tráfico.** El primer acceso después tarda alrededor de 1 minuto. Abrí el link un rato antes de presentar.
- **0.1 CPU:** cada respuesta tarda entre 10 y 20 segundos.
- **750 horas de instancia gratis por mes** por workspace.
- **La cuota gratuita de Gemini se comparte** entre todos los visitantes. Si un modelo responde 503 (saturado), 429 (límite) o 404 (retirado), `rag_ia.py` prueba el siguiente de la lista `modelos_ia`.
- **Sin disco persistente:** `memoria/memoria_ia.json` se pierde en cada deploy. La base vectorial no, porque está dentro de la imagen.

## Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| El build falla en `RUN --mount=type=secret,id=GEMINI_API_KEY` | Falta el Secret File | Crear el Secret File `GEMINI_API_KEY` y hacer Manual Deploy |
| Build: `503 Server Error: Backend.max_conn reached` | GitHub (raw) saturado al bajar la spec de Stripe | El `Dockerfile` reintenta 5 veces; si igual falla, volvé a desplegar |
| El servicio figura con plan `0.5c-512mb` | Render preselecciona un plan pago | Settings → Instance Type → Free |
| La API de Render responde `402 Payment information is required` | Crear servicios por API exige tarjeta | Crear el servicio desde el dashboard |
| La UI muestra "Has alcanzado el límite de tokens..." | Cuota gratuita de Gemini agotada | Esperar y reintentar, o usar otra API key |
| El primer acceso tarda mucho | La instancia estaba dormida | Normal en el plan Free: esperar alrededor de 1 minuto |

## Por qué Render

- **Hugging Face Spaces:** los Spaces Docker y Gradio en CPU gratuita ahora requieren suscripción PRO.
- **Streamlit Community Cloud:** no permite correr PostgreSQL en el mismo servicio. Haría falta una base externa (Neon, Supabase) y cambiar la configuración de conexión en `rag_ia.py`.
- **Render Free + Docker:** corre PostgreSQL y Streamlit juntos sin tocar el código de la app, con costo $0.
