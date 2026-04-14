# 🔍 Guía de Diagnóstico — Triunfo MVP

Si la app no funciona, usa los **logs para diagnosticar** qué está fallando.

## Ver logs en tiempo real

### 1. Arracar el servidor con logs en terminal

```bash
python run.py
```

Verás logs como estos:

```
[2026-04-14 10:43:33] INFO     [triunfo.api] === Triunfo API iniciando ===
[2026-04-14 10:43:35] INFO     [triunfo.api] Upload iniciado: factura.jpg (image/jpeg)
[2026-04-14 10:43:35] INFO     [triunfo.api] Archivo leído: 245623 bytes
[2026-04-14 10:43:35] INFO     [triunfo.pipeline] [a3d4e2f1] Pipeline iniciado | factura.jpg | provider=edenor-001 | quality=good
[2026-04-14 10:43:36] INFO     [triunfo.pipeline] [a3d4e2f1] Clasificación: Edenor (SERVICIOS) | confidence=0.97
[2026-04-14 10:43:36] INFO     [triunfo.pipeline] [a3d4e2f1] Pipeline completado: AUTO_APPROVE | confidence=0.95 | duration=1245ms | models=docai,tesseract
```

### 2. Ver logs en la API

Mientras la app corre, abre en otra terminal:

```bash
curl http://localhost:8000/logs | python -m json.tool
```

O en el navegador: http://localhost:8000/logs

Verás los últimos 50 logs en JSON:

```json
{
  "total": 12,
  "returned": 12,
  "logs": [
    {
      "timestamp": "2026-04-14T10:43:33.123456",
      "level": "INFO",
      "logger": "triunfo.api",
      "message": "Upload iniciado: factura.jpg (image/jpeg)"
    },
    ...
  ]
}
```

## Problemas comunes y soluciones

### ❌ "Archivo vacío"

```
[ERROR] Archivo vacío
```

**Causa:** El archivo que subiste no tiene contenido.

**Solución:** 
- Verifica que el archivo pese algo (> 1 KB)
- Intenta subir otro archivo

---

### ❌ "Tipo de archivo no soportado"

```
[ERROR] Tipo no soportado: image/bmp
```

**Causa:** Subiste un formato no soportado (BMP, GIF, etc).

**Solución:**
- Soportados: **JPEG, PNG, PDF**
- Convierte tu imagen a JPEG/PNG

---

### ❌ "Clasificación fallida"

```
[WARNING] [doc-id] Clasificación fallida (confidence 0.35)
[ERROR] Upload completado: documento routed to AUTO_REJECT
```

**Causa:** El sistema no reconoce el proveedor.

**Solución:**
- Especifica el proveedor manualmente en "Proveedor (hint demo)"
- O asegúrate que el documento tenga keywords de Edenor/Metrogas

---

### ❌ "Error no manejado"

```
[ERROR] Error no manejado: division by zero
[ERROR] Traceback (most recent call last):
  File "/src/pipeline/processor.py", line 185, in process
    ...
```

**Causa:** Bug en el código.

**Solución:**
- Mira el traceback en los logs para ver exactamente dónde falló
- Contacta para reportar el issue

---

### ❌ "HTTP 500 - Error procesando documento"

```json
{
  "detail": "Error procesando documento: module 'src.pdf_handler' has no attribute 'extract_from_pdf'"
}
```

**Causa:** Módulo PDF no está disponible.

**Solución:**
```bash
pip install pdfplumber reportlab
```

---

## Niveles de log

Los logs tienen 4 niveles:

| Nivel | Significa | Ejemplo |
|-------|-----------|---------|
| **DEBUG** | Detalles internos (muy verbose) | Entrada/salida de funciones |
| **INFO** | Info normal | Upload iniciado, pipeline completado |
| **WARNING** | Algo raro (pero no fatal) | Clasificación fallida, confidence baja |
| **ERROR** | Error que detiene el flujo | Archivo vacío, tipo no soportado |

---

## Dónde se guardan los logs

### Terminal
Aparecen en vivo cuando corres `python run.py`

### Archivo
Se guardan en: `logs/triunfo.log`

Puedes verlos:
```bash
tail -f logs/triunfo.log
```

### API
Endpoint: GET `http://localhost:8000/logs`

Los últimos 100 logs están en memoria

---

## Interpretando un flujo típico

```
1. [INFO] Upload iniciado: factura.jpg (image/jpeg)
   └─ El archivo se subió

2. [INFO] Archivo leído: 245623 bytes
   └─ Se leyó correctamente

3. [INFO] Pipeline iniciado | factura.jpg | provider=edenor-001 | quality=good
   └─ Comienza el procesamiento con Edenor y calidad "buena"

4. [DEBUG] Iniciando clasificación...
   └─ Agente D empieza

5. [INFO] Clasificación: Edenor (SERVICIOS) | confidence=0.97
   └─ Clasificación fue exitosa con 97% confianza

6. [INFO] Pipeline completado: AUTO_APPROVE | confidence=0.95 | duration=1245ms | models=docai,tesseract
   └─ Finalizó exitosamente, se aprobó automáticamente
   └─ Tardó 1.2 segundos
   └─ Usó 2 modelos: DocumentAI y Tesseract
```

---

## Tips de debugging

### Aumentar verbosidad

En `src/logging_setup.py`, cambia:
```python
logger.setLevel(logging.DEBUG)  # Ya está en DEBUG
console_handler.setLevel(logging.DEBUG)  # Ya está en DEBUG
```

Para ver TODO:
```python
# En api/main.py o pipeline/processor.py
logger.debug(f"Variable importante: {variable}")
```

### Usar ID corto del documento

Los logs usan `[doc-id[:8]]` para identificar documentos:
```
[a3d4e2f1] Pipeline iniciado
[a3d4e2f1] Clasificación completada
[a3d4e2f1] Pipeline completado
```

Así puedes seguir un documento a lo largo del pipeline.

### Checar archivo de log

```bash
grep "ERROR" logs/triunfo.log
grep "\[a3d4e2f1\]" logs/triunfo.log  # Un documento específico
tail -20 logs/triunfo.log
```

---

## ¿Todavía no funciona?

1. **Checa los logs** (terminal + `/logs` endpoint)
2. **Busca el ERROR** — dibuja exactamente dónde falla
3. **Mira el traceback** — eso te dice la causa
4. **Prueba con un documento diferente** — puede ser específico del archivo
5. **Reinstala dependencias:**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

---

**Generated:** 2026-04-14 | Triunfo MVP
