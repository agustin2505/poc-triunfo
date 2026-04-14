# 🚀 Cómo empezar con Triunfo MVP

Guía paso a paso para arrancar la aplicación y procesar tu primera factura.

## Paso 1: Instalar dependencias (⏱️ 2 minutos)

```bash
cd D:\poc-triunfo
pip install -r requirements.txt
```

Si alguna librería falla, probá:
```bash
pip install --upgrade -r requirements.txt
```

## Paso 2: Arrancar el servidor (⏱️ 30 segundos)

En una terminal:
```bash
python run.py
```

Verás:
```
  Triunfo MVP arrancando en http://localhost:8000
  UI:   http://localhost:8000/app
  Docs: http://localhost:8000/docs
```

✅ **El servidor está listo**

## Paso 3: Abrir la aplicación

En tu navegador: **http://localhost:8000/app**

Verás una pantalla con:
- Un área para arrastrar archivo
- Opciones de proveedor (auto-detecta o elige uno)
- Botón "Procesar Documento"

## Paso 4: Subir una factura

Tienes 3 opciones:

### A) Arrastrar archivo (más fácil)
1. Arrastra tu imagen/PDF al área de drop
2. La vista muestra un preview

### B) Clickear para seleccionar
1. Clickea el área → elige archivo del explorador

### C) Probar con datos de demo
1. Selecciona un proveedor en "Proveedor (hint demo)":
   - **Edenor** (Electricidad)
   - **Metrogas** (Gas)
   - **Factura Interna** (Negocio)
2. Selecciona calidad: **good** (para mejor resultado)
3. Clickea "Procesar Documento"

## Paso 5: Ver resultados

Cuando termina (2-3 segundos), ves 4 paneles:

### Panel A: Datos Extraídos
- Tabla con todos los campos detectados
- Confidence de cada uno
- Qué agente lo detectó mejor

### Panel B: Métricas
- Timeline de duración por etapa
- Modelos usados
- Duración total

### Panel C: Validaciones
- ✓ Si pasó
- ⚠ Warnings (si hay)
- ✗ Errores (si falló)

### Panel D: Routing
- **AUTO_APPROVE** (verde) → botón "Enviar a SAP"
- **HITL_STANDARD** (amarillo) → revisar manualmente
- **HITL_PRIORITY** (naranja) → revisar urgente
- **AUTO_REJECT** (rojo) → rechazado

## Paso 6: Descargar resultados

Dos opciones:
- **⬇ JSON** → datos estructurados para procesar
- **⬇ PDF** → reporte formateado para imprimir/archiva

## 📊 Entender los resultados

### Confidence (0.0 - 1.0)

| Rango | Significa | Acción |
|-------|-----------|--------|
| 0.88+ | Excelente | Se aprueba automáticamente |
| 0.70-0.88 | Bueno | Revisar manualmente |
| 0.40-0.70 | Bajo | Revisar prioritariamente |
| <0.40 | Muy bajo | Rechazado |

### Campos

Cada campo muestra:
- **Valor**: lo que se extrajo
- **Confidence**: cuán seguro está (0-100%)
- **Fuente**: agente que lo detectó mejor
- **Por agente**: confidence de cada uno

### Validaciones

La app valida:
- **Montos**: positivos, dentro de límites
- **Fechas**: válidas, issue_date ≤ due_date
- **Referencia**: formato válido
- **Duplicados**: no se repita ref+proveedor+fecha
- **Por proveedor**: reglas específicas Edenor/Metrogas

## 🐛 Si algo falla

### 1. Checa los logs en terminal

Mientras corre `python run.py`, verás logs como:
```
[INFO] Upload iniciado: factura.jpg
[INFO] Clasificación: Edenor (SERVICIOS)
[INFO] Pipeline completado: AUTO_APPROVE
```

Si hay error, verás:
```
[ERROR] Archivo vacío
[ERROR] Tipo no soportado
```

### 2. Ver logs recientes en la app

En otra terminal:
```bash
curl http://localhost:8000/logs
```

O en navegador: http://localhost:8000/logs

### 3. Ver archivo de log

```bash
tail -f logs/triunfo.log
```

### 4. Leer DIAGNOSTICO.md

Si nada funciona, abre: **DIAGNOSTICO.md**

Tiene soluciones para:
- Archivo vacío
- Tipo no soportado
- Clasificación fallida
- Errores al procesar PDF

## 📁 Archivos principales

| Archivo | Para qué |
|---------|----------|
| `run.py` | Arranca el servidor |
| `frontend/app.js` | Lógica de la UI |
| `api/main.py` | API FastAPI |
| `src/pipeline/processor.py` | Motor de procesamiento |
| `logs/triunfo.log` | Log de errores |
| `README.md` | Documentación técnica |
| `DIAGNOSTICO.md` | Troubleshooting |

## 🎯 Recomendaciones

### Para probar rápido:
1. Usa **provider_hint** = uno de los 3 disponibles
2. Elige **quality_hint** = "good"
3. Sube una **imagen clara** (JPEG/PNG) o **PDF con texto**

### Para ver detalles:
1. Clickea en los valores de confidence para ver detalle por agente
2. Mira "Duración por etapa" en Panel B
3. Descarga JSON para ver todos los datos

### Para investigar problemas:
1. Abre otra terminal
2. Corre: `curl http://localhost:8000/logs | python -m json.tool`
3. Busca "ERROR" o "WARNING"
4. El `[doc-id]` te ayuda a seguir un documento

## ✅ Checklist de funcionamiento

- [ ] `python run.py` arranca sin errores
- [ ] Puedo abrir http://localhost:8000/app
- [ ] Sé arrastrar un archivo al drop zone
- [ ] El botón "Procesar" se habilita
- [ ] Veo los 4 paneles después de procesar
- [ ] Puedo descargar JSON
- [ ] Puedo descargar PDF
- [ ] Veo logs en terminal
- [ ] Puedo hacer curl a /logs

Si todo ✓, **felicitaciones: Triunfo MVP está funcionando!**

## 📞 Preguntas frecuentes

**P: ¿Necesito credenciales de Google Cloud?**
A: No para el MVP. Todo es mock. Para producción sí necesitarás GCP.

**P: ¿Qué formatos de archivo soporta?**
A: JPEG, PNG, PDF (con texto o escaneados).

**P: ¿Por qué se tarda 2-3 segundos?**
A: Corre 5 agentes en paralelo + conciliación + validaciones. Normal.

**P: ¿Puede procesar facturas en otros idiomas?**
A: MVP está para Spanish. Pero la arquitectura lo permite.

**P: ¿Cómo agrego más proveedores?**
A: Edita `src/config/providers.py` y agrega un nuevo proveedor.

**P: ¿Cómo cambio el proveedor de MOCK a REAL (Document AI)?**
A: En `src/agents/agent_a_docai.py`, reemplaza el mock con la API real.

---

**¡Listo! Ahora a procesar facturas! 📄✨**

Para más detalles técnicos, ver: `README.md`
Para troubleshooting: `DIAGNOSTICO.md`
