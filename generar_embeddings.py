"""
Script para generar embeddings de los chunks de Stripe usando la API de Gemini,
y guardarlos en PostgreSQL (con la extensión pgvector).

Requisitos previos:
    - Haber corrido descargar_stripe_docs.py (genera data/chunks.json)
    - Tener PostgreSQL + pgvector corriendo (ver DECISIONS.md para el setup)

Uso:
    python generar_embeddings.py
"""

import json
import os

import psycopg2
from google import genai
from google.genai import types

# --- Configuración ---
ruta_clave = ".secreto/claves_api.json"
ruta_trozo = os.path.join("datos", "chunks.json")
modele_de_embedding = "gemini-embedding-001"
dimensiones = 768  # Recortamos de 3072 a 768 para que sea más liviano y rápido

# Configuración de conexión a PostgreSQL (base local con pgvector, vía Conda)
base_dato_config = {
	"host": "localhost",
	"port": 5433,
	"dbname": "rag_stripe",
	"user": "postgres",
	"password": "rag1234",
}

def obtener_clave_api():
    """Lee la clave de la API desde un archivo JSON."""
    with open(ruta_clave, 'r') as archivo:
        datos = json.load(archivo)
    return datos["claves_gemini"]


def cargar_chunks():
    """Carga los chunks generados por descargar_stripe.py"""
    with open(ruta_trozo, "r", encoding="utf-8") as f:
        return json.load(f)


def crear_tabla(conn):
    """Crea la tabla de chunks con su columna de embedding (vector) si no existe."""
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS stripe_chunks (
                id TEXT PRIMARY KEY,
                texto TEXT NOT NULL,
                fuente TEXT NOT NULL,
                seccion TEXT,
                embedding vector({dimensiones})
            );
        """)
    conn.commit()
    print("Tabla 'stripe_chunks' lista.")

def generar_embedding(cliente, texto):
    """Genera el embedding de un texto usando la API de Gemini."""
    resultado = cliente.models.embed_content(
        model=modele_de_embedding,
        contents=[texto],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=dimensiones,
        ),
    )
    return list(resultado.embeddings[0].values)




def guardar_chunk(conn, chunk, embedding):
    """Guarda (o actualiza) un chunk con su embedding en la base de datos."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO stripe_chunks (id, texto, fuente, seccion, embedding)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET texto = EXCLUDED.texto,
                fuente = EXCLUDED.fuente,
                seccion = EXCLUDED.seccion,
                embedding = EXCLUDED.embedding;
            """,
            (chunk["id"], chunk["texto"], chunk["fuente"], chunk["seccion"], embedding),
        )
    conn.commit()


def borrar_chunks_obsoletos(conn, ids_vigentes):
    """Borra los chunks de endpoints que ya no están en la especificación actual de Stripe."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM stripe_chunks WHERE NOT (id = ANY(%s)) RETURNING id;",
            (list(ids_vigentes),),
        )
        borrados = [fila[0] for fila in cur.fetchall()]
    conn.commit()
    return borrados


def main():
    api_key = obtener_clave_api()

    cliente = genai.Client(api_key=api_key)

    print("Cargando chunks...")
    chunks = cargar_chunks()
    print(f"Se cargaron {len(chunks)} chunks.")

    conn = psycopg2.connect(**base_dato_config)
    crear_tabla(conn)

    ids_guardados = []
    for i, chunk in enumerate(chunks, start=1):
        if not chunk.get("texto"):
            print(f"[{i}/{len(chunks)}] Saltando chunk {chunk['id']} por texto nulo o vacío.")
            continue

        print(f"[{i}/{len(chunks)}] Generando embedding para: {chunk['id']}")
        embedding = generar_embedding(cliente, [chunk["texto"]])
        guardar_chunk(conn, chunk, embedding)
        ids_guardados.append(chunk["id"])

    # Si Stripe quitó un endpoint, su chunk viejo no se pisa con el upsert: hay que borrarlo
    if ids_guardados:
        borrados = borrar_chunks_obsoletos(conn, ids_guardados)
        for id_borrado in borrados:
            print(f"Borrado chunk obsoleto: {id_borrado}")
        print(f"Se borraron {len(borrados)} chunks que ya no están en la documentación de Stripe.")

    conn.close()
    print("¡Listo! Todos los embeddings se generaron y guardaron en pgvector.")


if __name__ == "__main__":
    main()
