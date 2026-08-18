import json
import os
import psycopg2
from google import genai
from google.genai.types import EmbedContentConfig

# Configuración de rutas
ruta_memoria = "memoria/memoria_ia.json"
ruta_clave = ".secreto/claves_api.json"

# Lista de modelos disponibles
modelos_ia = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"]
modelo_de_embedding = "gemini-embedding-001"
dimensiones_embedding = 768

# Configuración de conexión a PostgreSQL (con pgvector)
base_dato_config = {
	"host": "localhost",
	"port": 5433,
	"dbname": "rag_stripe",
	"user": "postgres",
	"password": "rag1234",
	}

# Cargar la clave de la API
def obtener_clave_api():
	"""
	Lee la clave de la API desde un archivo JSON.
	"""
	if not os.path.isfile(ruta_clave):
		estilo_json = {
			"claves_gemini": "<tu clave API aquí>"
		}
		os.makedirs(".secreto", exist_ok=True)
		with open(".secreto/claves_api.json", "w", encoding="utf-8") as archivo:
			json.dump(estilo_json, archivo, indent=4, ensure_ascii=False)
		# Provocar un error y quitar el proceso
		raise FileNotFoundError(f"No se encontró el archivo de claves: {ruta_clave}\n>> El archivo fue creado debes ir a ponerle la clave API. <<")

	with open(ruta_clave, "r", encoding="utf-8") as archivo:
		datos = json.load(archivo)
	return datos["claves_gemini"]

# Configurar el cliente de Gemini
cliente = genai.Client(api_key=obtener_clave_api())

# Cargar la memoria local de la IA 
def cargar_memoria():
	"""
	Carga el historial de conversaciones desde el archivo JSON.
	"""
	if not os.path.isfile(ruta_memoria):
		return []
	with open(ruta_memoria, 'r', encoding='utf-8') as archivo:
		try:
			return json.load(archivo)
		except json.JSONDecodeError:
			return []

def guardar_memoria(historial):
	"""
	Guarda el historial de conversaciones en el archivo JSON.
	"""
	os.makedirs(os.path.dirname(ruta_memoria), exist_ok=True)
	with open(ruta_memoria, 'w', encoding='utf-8') as archivo:
		json.dump(historial, archivo, indent=4, ensure_ascii=False)

def generar_embedding_consulta(texto):
	"""
	Genera el embedding para la consulta del usuario.
	"""
	resultado = cliente.models.embed_content(
		model=modelo_de_embedding,
		contents=texto,
		config=EmbedContentConfig(
			task_type="RETRIEVAL_QUERY",
			output_dimensionality=dimensiones_embedding,
			),
		)
	return resultado.embeddings[0].values

def buscar_contexto_relevante(embedding, limite=3):
	"""
	Busca los fragmentos más relevantes en PostgreSQL usando distancia coseno con pgvector.
	"""
	try:
		conexion = psycopg2.connect(**base_dato_config)
		with conexion.cursor() as cur:
			# Usamos <=> para distancia coseno en pgvector
			embedding_pg = "[" + ",".join(map(str, embedding)) + "]"
			cur.execute(
			"""
			SELECT texto, fuente, seccion
			FROM stripe_chunks
			ORDER BY embedding <=> %s::vector
			LIMIT %s;
			""",
			(embedding_pg, limite)
			)
			resultados = cur.fetchall()
			conexion.close()
		return resultados
	except Exception as e:
		print(f"Error al conectar o consultar PostgreSQL: {e}")
		return []

def generar_respuesta(datos_entrada):
	"""
	Genera el embedding de la pregunta, recupera contexto relevante de PostgreSQL, construye el prompt final con RAG, y obtiene la respuesta de la IA.
	Devuelve un diccionario con la estructura de respuesta anidada.
	"""
	datos_pregunta = datos_entrada.get("pregunta", {})
	pregunta = datos_pregunta.get("texto", "")
	historial_externo = datos_pregunta.get("historial", [])
	config_modelo = datos_pregunta.get("modelo_de_ia", {})
	modelo_solicitado = config_modelo.get("modelo")

	# Generar embedding y buscar contexto relevante
	print("Buscando información de soporte...")
	embedding = generar_embedding_consulta(pregunta)
	fragmentos = buscar_contexto_relevante(embedding)

	# Construir el contexto para el prompt
	contexto = ""
	fuentes_utilizadas = []
	contexto_lista = []
	if fragmentos:
		for texto, fuente, seccion in fragmentos:
			referencia = f"(Sección: {seccion})" if seccion else ""
			contexto_lista.append(f"- [{fuente}{referencia}]: {texto}")
			if fuente not in fuentes_utilizadas:
				fuentes_utilizadas.append(fuente)
	contexto = "\n".join(contexto_lista)

	# Crear el prompt final inyectando el contexto si existe
	if contexto:
		pregunta_con_contexto = (
			f"Utiliza la siguiente información de contexto para responder la pregunta del usuario de manera precisa.\n"
			f"Si no sabes la respuesta basada en el contexto, dilo claramente.\n\n"
			f"Contexto recuperado:\n{contexto}\n\n"
			f"Pregunta del usuario: {pregunta}"
			)
	else:
		pregunta_con_contexto = pregunta

	# Preparar el historial para la API
	historial_api = []
	for mensaje in historial_externo:
		historial_api.append({
			"role": mensaje["rol"],
			"parts": [{"text": mensaje["contenido"]}]
		})
	# Agregar la nueva pregunta con el contexto inyectado al historial de la API
	historial_api.append({
		"role": "user",
		"parts": [{"text": pregunta_con_contexto}]
	})

	respuesta_final = None
	modelo_usado = 0

	# Determinar la lista de modelos a intentar
	if modelo_solicitado:
		lista_de_modelos = [modelo_solicitado]
	else:
		lista_de_modelos = modelos_ia

	# Intentar con los modelos en orden
	for nombre_modelo in lista_de_modelos:
		modelo_usado = nombre_modelo
		try:
			respuesta = cliente.models.generate_content(
				model=nombre_modelo,
				contents=historial_api,
				)
			respuesta_final = respuesta.text
			break # Si funciona salimos del bucle
		except Exception as error:
			error_str = str(error)
			if "404" in error_str or "NOT_FOUND" in error_str.upper():
				return {
					"respuesta": {
						"texto": 0,
						"fuentes": 0,
						"modelo_de_ia": {
							"tipo": "gemini",
							"modelo": nombre_modelo
						},
						"errores": {
							"MODELO_INEXISTANTE": f"El modelo {nombre_modelo} no existe."
						}
					}
				}

			if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str.upper():
				print(f"Límite de tokens alcanzado con {nombre_modelo}. Intentando con el siguiente...")
				# Si es el último modelo, retornamos el error
				if nombre_modelo == lista_de_modelos[-1]:
					return {
						"respuesta": {
							"texto": 0,
							"fuentes": 0,
							"modelo_de_ia": {
								"tipo": "gemini",
								"modelo": nombre_modelo
							},
							"errores": {
								"TOKENS_ALCANZADO": "Has alcanzado el límite de tokens de este modelo. Inténtalo de nuevo más tarde o utiliza otro modelo."
							}
						}
					}
				continue

			print(f"Error con el modelo {nombre_modelo}: {error}. Intentando con el siguiente...")
			continue

	if respuesta_final:
		# Guardamos en la memoria local el mensaje original (sin contexto)
		historial_guardar = historial_externo + [{"rol": "user", "contenido": pregunta}, {"rol": "model", "contenido": respuesta_final}]
		guardar_memoria(historial_guardar)

		# Crear diccionario de fuentes enumeradas o 0 si no hay
		diccionario_fuentes = {str(i + 1): fuente for i, fuente in enumerate(fuentes_utilizadas)} if fuentes_utilizadas else 0
		return {
			"respuesta": {
				"texto": respuesta_final,
				"fuentes": diccionario_fuentes,
				"modelo_de_ia": {
					"tipo": "gemini",
					"modelo": modelo_usado
				}
			}
		}
	else:
		return {
			"respuesta": {
				"texto": 0,
				"fuentes": 0,
				"modelo_de_ia": {
					"tipo": "gemini",
					"modelo": modelo_usado
				},
				"errores": {
					"modelo_error": "No se pudo generar una respuesta con ninguno de los modelos disponibles."
				}
			}
		}

if __name__ == "__main__":
	print("="*10, "Iniciando conversación con la IA (RAG habilitado). Escribe '.salir' para terminar.", "="*10)

	while True:
		pregunta_usuario = input("\n¿Qué onda? ⌨️>: ")
		if pregunta_usuario.lower() == '.salir':
			print('⁠(⁠ ⁠ ⁠•⁠ ⁠‿⁠ ⁠•⁠ ⁠ ⁠)' *20)
			break

		# Cargamos la memoria para enviarla al script interno
		historial_actual = cargar_memoria()
		datos_paquete = {
			"pregunta": {
				"texto": pregunta_usuario,
				"historial": historial_actual
				# Opcional: "modelo_de_ia": {"tipo": "gemini", "modelo": "gemini-2.5-pro"}
			}
		}

		resultado = generar_respuesta(datos_paquete)

		if "errores" in resultado["respuesta"]:
			print("Error:")
			print(json.dumps(resultado["respuesta"]["errores"], indent=4, ensure_ascii=False))
		else:
			print("✦Respuesta:")
			print(resultado["respuesta"]["texto"])

			print("\n🌐Fuentes:")
			if resultado["respuesta"]["fuentes"] == 0:
				print("Ninguno")
			else:
				print(json.dumps(resultado["respuesta"]["fuentes"], indent=4, ensure_ascii=False))
