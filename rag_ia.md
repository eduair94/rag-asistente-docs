# Documentación de la API RAG (rag_ia.py)

Este documento detalla la estructura y el uso del motor de Inteligencia Artificial con soporte RAG (Retrieval-Augmented Generation) implementado en `rag_ia.py`. Este módulo está diseñado para ser consultado tanto directamente por consola como importado por scripts externos.

---

## 1. Estructura de Entrada

La función principal `generar_respuesta` espera un único diccionario que contiene los datos de la consulta, el historial conversacional y la configuración del modelo de IA deseado.

### Formato JSON/Diccionario de Entrada:
```json
{
  "pregunta": {
    "texto": "Aquí va la pregunta que hace el usuario",
    "historial": [
      {
        "rol": "user",
        "contenido": "Mensaje anterior enviado por el usuario"
      },
      {
        "rol": "model",
        "contenido": "Respuesta anterior generada por el modelo"
      }
    ],
    "modelo_de_ia": {
      "tipo": "gemini",
      "modelo": "gemini-2.5-flash"
    }
  }
}
```

### Descripción de Campos:
*   **`pregunta`** *(Diccionario, Obligatorio)*: Contenedor principal de los datos.
    *   **`texto`** *(String, Obligatorio)*: La pregunta real que se desea responder.
    *   **`historial`** *(Lista de diccionarios, Obligatorio)*: El contexto conversacional previo. Cada elemento debe ser un diccionario con las claves `"rol"` (`"user"` o `"model"`) y `"contenido"` *(String)*.
    *   **`modelo_de_ia`** *(Diccionario, Opcional)*: Permite forzar el uso de un modelo específico.
        *   **`tipo`** *(String)*: El proveedor del servicio (actualmente `"gemini"`).
        *   **`modelo`** *(String)*: El nombre del modelo técnico exacto que se desea invocar.

---

## 2. Estructura de Salida

La función `generar_respuesta` devuelve siempre un objeto consistente de respuesta. Toda la información, tanto el resultado exitoso como los fallos o errores de ejecución, se encapsula dentro del campo principal `"respuesta"`.

### Caso 1: Respuesta Exitosa
Si la consulta se completa correctamente, se obtiene la respuesta, la lista de fuentes enumeradas consultadas mediante RAG, y el modelo que finalmente procesó la consulta.

```json
{
  "respuesta": {
    "texto": "Aquí se incluye la respuesta generada por el modelo de IA.",
    "fuentes": {
      "1": "fuente_documento_A.json",
      "2": "fuente_documento_B.json"
    },
    "modelo_de_ia": {
      "tipo": "gemini",
      "modelo": "gemini-2.5-flash"
    }
  }
}
```

### Caso 2: Sin Fuentes Encontradas (RAG no recuperó datos)
Si no existen documentos relevantes en la base de datos PostgreSQL/pgvector para la pregunta dada, el campo `"fuentes"` devolverá el entero `0`.

```json
{
  "respuesta": {
    "texto": "Aquí se incluye la respuesta generada por el modelo de IA usando su conocimiento general.",
    "fuentes": 0,
    "modelo_de_ia": {
      "tipo": "gemini",
      "modelo": "gemini-2.5-flash"
    }
  }
}
```

### Caso 3: Error de Modelo Inexistente (HTTP 404)
Si el modelo especificado en `"modelo_de_ia"` no existe o no es reconocido por la API de Gemini, se interrumpe el flujo y se devuelve el código de error `"MODELO_INEXISTANTE"`.

```json
{
  "respuesta": {
    "texto": 0,
    "fuentes": 0,
    "modelo_de_ia": {
      "tipo": "gemini",
      "modelo": "modelo-no-existente"
    },
    "errores": {
      "MODELO_INEXISTANTE": "El modelo modelo-no-existente no existe."
    }
  }
}
```

### Caso 4: Límite de Tokens Alcanzado (HTTP 429)
Si se ha superado la cuota de peticiones permitidas por la API para todos los modelos disponibles, se devuelve el error `"TOKENS_ALCANZADO"`.

```json
{
  "respuesta": {
    "texto": 0,
    "fuentes": 0,
    "modelo_de_ia": {
      "tipo": "gemini",
      "modelo": "gemini-3.5-flash"
    },
    "errores": {
      "TOKENS_ALCANZADO": "Has alcanzado el límite de tokens de este modelo. Inténtalo de nuevo más tarde o utiliza otro modelo."
    }
  }
}
```

---

## 3. Comportamiento y Flujo de Selección de Modelos

El script gestiona la selección de modelos de forma inteligente siguiendo estas directrices:

1.  **Modelo Preferido**: Si se especifica un modelo en `"modelo_de_ia"`, la API intentará utilizar **exclusivamente** ese modelo. Si este falla (por ejemplo, con error 404 o 429), el script no intentará usar otros y devolverá el error de inmediato.
2.  **Lista de Respaldo (Fallback)**: Si no se define ningún modelo en la entrada, el script recorrerá secuencialmente la lista predefinida:
    `["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"]`
    Si un modelo de la lista devuelve un error de tipo `429` (Saturación), pasará automáticamente al siguiente hasta encontrar uno disponible.

---

## 4. Ejemplos Prácticos de Integración

A continuación, se presentan ejemplos de cómo interactuar con `rag_ia.py` mediante scripts externos de Python.

### Ejemplo A: Consulta básica sin historial
```python
from rag_ia import generar_respuesta

# Preparar los datos mínimos para realizar la consulta
paquete_consulta = {
    "pregunta": {
        "texto": "¿Cómo puedo realizar un reembolso con Stripe?",
        "historial": []
    }
}

# Obtener respuesta
resultado = generar_respuesta(paquete_consulta)

# Procesar los datos devueltos
respuesta_datos = resultado["respuesta"]
if "errores" in respuesta_datos:
    print(f"Ocurrió un error: {respuesta_datos['errores']}")
else:
    print(f"Respuesta de la IA: {respuesta_datos['texto']}")
    print(f"Fuentes de soporte: {respuesta_datos['fuentes']}")
    print(f"Modelo utilizado: {respuesta_datos['modelo_de_ia']['modelo']}")
```

### Ejemplo B: Consulta con un modelo específico e historial
```python
import json
from rag_ia import generar_respuesta

paquete_consulta = {
    "pregunta": {
        "texto": "¿Hay un límite diario de transacciones?",
        "historial": [
            {"rol": "user", "contenido": "Hola, ¿Stripe acepta pagos en euros?"},
            {"rol": "model", "contenido": "Sí, Stripe permite procesar cargos en euros directamente."}
        ],
        "modelo_de_ia": {
            "tipo": "gemini",
            "modelo": "gemini-2.5-pro"
        }
    }
}

resultado = generar_respuesta(paquete_consulta)
print(json.dumps(resultado, indent=4, ensure_ascii=False))
```
