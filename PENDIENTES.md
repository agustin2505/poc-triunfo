# Pendientes para que el MVP funcione con imágenes reales

Estado actual: el pipeline corre 100% con mocks. Los agentes reales (Claude + Gemini) están implementados pero no activos. Esta es la lista ordenada de lo que falta para activarlos.

---

## 1. Instalar dependencias nuevas

Las dos librerías agregadas en `requirements.txt` en Spec-19/20 todavía no están instaladas.

```bash
pip install anthropic>=0.40.0 google-cloud-aiplatform>=1.60.0
```

O instalar todo desde el archivo actualizado:

```bash
pip install -r requirements.txt
```

---

## 2. Configurar autenticación GCP

Vertex AI necesita credenciales activas. Hay dos opciones:

### Opción A — Application Default Credentials (desarrollo local, recomendado)

```bash
gcloud auth application-default login
```

Esto abre el browser, loguea con la cuenta que tiene acceso al proyecto, y guarda las credenciales localmente. No requiere ninguna variable extra.

### Opción B — Service Account Key (CI, servidores, producción)

1. En GCP Console → IAM → Service Accounts → crear cuenta con rol **Vertex AI User**
2. Crear key JSON → descargar
3. Agregar al `.env`:

```
GOOGLE_APPLICATION_CREDENTIALS=C:\ruta\al\key.json
```

---

## 3. Habilitar la API de Vertex AI en GCP

Si el proyecto es nuevo, la API puede no estar habilitada.

```bash
gcloud services enable aiplatform.googleapis.com --project=TU_PROYECTO_ID
```

O desde GCP Console → APIs & Services → habilitar "Vertex AI API".

---

## 4. Completar el `.env` y cargarlo al arrancar

El archivo `.env` tiene los dos valores críticos a completar:

```
ANTHROPIC_API_KEY=COMPLETAR
GOOGLE_CLOUD_PROJECT=COMPLETAR
```

**Problema actual**: `run.py` no carga el `.env` automáticamente. Hay dos formas de resolverlo:

### Opción A — Agregar `python-dotenv` (recomendado)

Agregar a `requirements.txt`:
```
python-dotenv>=1.0.0
```

Agregar al inicio de `run.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Opción B — Setear manualmente en PowerShell antes de arrancar

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:GOOGLE_CLOUD_PROJECT = "mi-proyecto"
$env:USE_IMAGE_ORCHESTRATOR = "true"
python run.py
```

---

## 5. Pasar `mime_type` desde la API al pipeline

**Archivo**: `api/main.py` línea ~132

El endpoint `/upload` ya tiene el `content_type` del archivo pero no lo pasa a `_pipeline.process()`. El pipeline lo necesita para saber si usar `ImageOrchestrator` o el flujo PDF.

**Cambio necesario** en `api/main.py`:

```python
# Antes:
result = _pipeline.process(
    image_bytes=image_bytes,
    file_name=file.filename or "documento",
    ...
)

# Después — agregar mime_type:
result = _pipeline.process(
    image_bytes=image_bytes,
    file_name=file.filename or "documento",
    mime_type=content_type,   # <-- agregar esta línea
    ...
)
```

Sin este cambio, `USE_IMAGE_ORCHESTRATOR=true` no tiene efecto porque el pipeline infiere el mime_type desde la extensión del nombre de archivo, lo cual puede fallar si el nombre no tiene extensión.

---

## 6. Integrar `ImagePreprocessor` en el pipeline de imágenes

**Archivo**: `src/agents/image_orchestrator.py`

El `ImagePreprocessor` (Spec-17) está implementado pero nunca se llama. El `ImageOrchestrator` recibe `image_bytes` crudos y los pasa directamente a los modelos. Pueden llegar archivos > 4MB, con rotación incorrecta o en formato TIFF.

**Cambio necesario** en `ImageOrchestrator.run_sync()`:

```python
from src.utils.image_preprocessor import ImagePreprocessor, ImagePreprocessorError

# Al inicio de run_sync(), antes del ThreadPoolExecutor:
try:
    preprocessor = ImagePreprocessor()
    processed = preprocessor.process(image_bytes, mime_type="image/jpeg")
    image_bytes = processed.image_bytes   # reemplazar con imagen normalizada
    if processed.quality_score < 0.15:
        advertencias.append(f"Calidad de imagen baja (score={processed.quality_score})")
except ImagePreprocessorError as e:
    return OrchestratorResult(
        document_id=document_id,
        status="FAILED",
        routing=RoutingDecision.AUTO_REJECT.value,
        advertencias=[str(e)],
        ...
    )
```

---

## 7. Activar el flag en `.env`

Una vez completados los puntos 1-6, activar:

```
USE_IMAGE_ORCHESTRATOR=true
```

Sin esto el pipeline sigue usando los mocks aunque las credenciales estén configuradas.

---

## 8. Test de humo con una factura real

Con el servidor corriendo con credenciales reales:

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@factura_edenor.jpg" \
  -F "provider_hint=edenor-001" \
  -F "quality_hint=good"
```

Verificar en la respuesta:
- `processing_summary.models_used` contiene `claude-vision`, `gemini-flash`, etc.
- `confidence_score > 0.0`
- `extracted_fields.total_amount.value` no es null
- `routing` no es `AUTO_REJECT`

---

## Pendientes opcionales / mejoras

| Item | Archivo | Por qué importa |
|------|---------|-----------------|
| **Spec-12**: logs estructurados con Cloud Logging | pendiente | Observabilidad en producción |
| Tests de integración para agentes reales | `tests/test_agents_real.py` | Validar que Claude y Gemini extraen correctamente con facturas reales |
| Frontend: mostrar qué modelos respondieron | `frontend/app.js` | El panel B no muestra aún los 4 modelos del ImageOrchestrator |
| Manejo de imágenes multi-página | `src/agents/image_orchestrator.py` | Facturas con más de una página (hoy solo se procesa la primera) |
| Fase 2 activable desde la UI | `api/main.py` + `frontend/app.js` | El mapeo SAP (Fase 2) hoy es `run_fase2=False`; debería activarse al aprobar un documento |
| Few-shot examples por proveedor en prompts | `src/agents/prompts_imagen.py` | Mejora precisión especialmente en facturas de servicios con layouts no estándar |
| Timeout configurable por agente individual desde `.env` | `src/agents/vertex/*.py` | Hoy los timeouts están hardcodeados como constantes de clase |

---

## Orden recomendado de ejecución

```
1. pip install -r requirements.txt          ← 2 min
2. gcloud auth application-default login    ← 2 min (con browser)
3. Completar .env (API keys)                ← 1 min
4. Agregar python-dotenv + load_dotenv()    ← 5 min (código)
5. Pasar mime_type en api/main.py           ← 2 min (código)
6. Integrar ImagePreprocessor              ← 10 min (código)
7. USE_IMAGE_ORCHESTRATOR=true en .env     ← 1 min
8. python run.py + test de humo            ← 5 min
```

**Total estimado: ~30 minutos** para tener el pipeline real funcionando.
