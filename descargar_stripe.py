"""
Script para descargar la especificación OpenAPI de Stripe y convertirla
en chunks de texto listos para generar embeddings.

Uso:
		python descargar_stripe_docs.py
"""

import json
import os
import requests

# URL oficial de la especificación de Stripe (mantenida por Stripe en GitHub)
stripe_spec_url = "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json"

# Carpeta donde se van a guardar los datos descargados y procesados
ruta_datos = "datos"
raw_spec_ruta = os.path.join(ruta_datos, "stripe_spec3.json")
ruta_salida_trozo = os.path.join(ruta_datos, "chunks.json")

# Palabras clave para filtrar solo los endpoints que nos interesan.
# Se buscan estas palabras dentro de la ruta de cada endpoint.
palabras_filtro = [
	"payment_intent",
	"charge",
	"customer",
	"webhook_endpoint",
]


def leer_version_local():
	"""Devuelve la versión (info.version) del spec3.json local, o None si no hay uno válido."""
	if not os.path.exists(raw_spec_ruta):
		return None
	try:
		with open(raw_spec_ruta, "r", encoding="utf-8") as f:
			return json.load(f)["info"]["version"]
	except (ValueError, KeyError):
		return None


def descargar_spec():
	"""
	Descarga el spec3.json de Stripe y reemplaza el archivo local solo si la versión
	publicada (info.version) es distinta. Si la descarga falla pero hay una copia
	local, se sigue con esa copia.
	"""
	os.makedirs(ruta_datos, exist_ok=True)
	version_local = leer_version_local()

	print("Descargando especificación de Stripe (puede tardar un momento, pesa ~8 MB)...")
	try:
		response = requests.get(stripe_spec_url, timeout=120)
		response.raise_for_status()
		version_remota = response.json()["info"]["version"]
	except (requests.RequestException, ValueError, KeyError) as error:
		if version_local is None:
			raise
		print(f"No se pudo descargar la especificación ({error}). Se usa la copia local (versión {version_local}).")
		return

	if version_remota == version_local:
		print(f"La especificación local ya está al día (versión {version_local}).")
		return

	with open(raw_spec_ruta, "w", encoding="utf-8") as f:
		f.write(response.text)

	if version_local:
		print(f"Especificación actualizada de la versión {version_local} a la {version_remota}. Guardada en {raw_spec_ruta}")
	else:
		print(f"Descarga completa (versión {version_remota}). Guardada en {raw_spec_ruta}")


def endpoint_es_relevante(ruta):
	"""Chequea si la ruta del endpoint contiene alguna palabra clave de interés."""
	ruta_lower = ruta.lower()
	return any(palabra in ruta_lower for palabra in palabras_filtro)


def construir_texto_chunk(ruta, metodo, operacion):
	"""
	Arma el texto de un chunk a partir de un endpoint de la especificación.
	Incluye: método HTTP, ruta, resumen, descripción y parámetros principales.
	"""
	partes = [f"Endpoint: {metodo.upper()} {ruta}"]
	resumen = operacion.get("summary", "")

	if resumen:
		partes.append(f"Resumen: {resumen}")
	descripcion = operacion.get("description", "")

	if descripcion:
		partes.append(f"Descripción: {descripcion}")

	# Parámetros del endpoint (si los tiene)
	parametros = operacion.get("parameters", [])
	if parametros:
		nombres_parametros = [param.get("name", "") for param in parametros if param.get("name")]
		if nombres_parametros:
			partes.append(f"Parámetros: {', '.join(nombres_parametros)}")

	# Parámetros del body (ej. metadata, email en POST /v1/customers): Stripe los define en requestBody
	esquema_body = operacion.get("requestBody", {}).get("content", {}).get("application/x-www-form-urlencoded", {}).get("schema", {})
	nombres_body = list(esquema_body.get("properties", {}).keys())
	if nombres_body:
		partes.append(f"Parámetros del body: {', '.join(nombres_body)}")
	return "\n".join(partes)


def procesar_spec():
	"""Lee el spec descargado, filtra los endpoints relevantes y arma los chunks(trozos)."""
	print("Leyendo y procesando la especificación...")

	with open(raw_spec_ruta, "r", encoding="utf-8") as f:
		spec = json.load(f)

		rutas = spec.get("paths", {})
		trozos = []

		for ruta, metodos in rutas.items():
			if not endpoint_es_relevante(ruta):
				continue

			for metodo, operacion in metodos.items():
				# Nos aseguramos de que sea un método HTTP válido (get, post, delete, etc.)
				if metodo.lower() not in ["get", "post", "put", "delete", "patch"]:
					continue

				texto = construir_texto_chunk(ruta, metodo, operacion)

				chunk = {
					"id": f"{metodo.upper()}_{ruta}",
					"texto": texto,
					"fuente": f"Stripe API docs: {metodo.upper()} {ruta}",
					"seccion": clasificar_seccion(ruta),
				}
				trozos.append(chunk)

				print(f"Se generaron {len(trozos)} trozos.")

		with open(ruta_salida_trozo, "w", encoding="utf-8") as f:
			json.dump(trozos, f, ensure_ascii=False, indent=2)

			print(f"Chunks guardados en {ruta_salida_trozo}")


def clasificar_seccion(ruta):
	"""Clasifica el endpoint en una sección general, útil para filtros después."""
	ruta_lower = ruta.lower()
	if "payment_intent" in ruta_lower or "charge" in ruta_lower:
		return "Payments"
	if "customer" in ruta_lower:
		return "Customers"
	if "webhook" in ruta_lower:
		return "Webhooks"
	return "Otro"


if __name__ == "__main__":
	descargar_spec()
	procesar_spec()
