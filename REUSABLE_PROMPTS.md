# Prompts Reutilizables para Extracción Multimodal

Estos prompts pueden adaptarse a cualquier dominio de extracción de datos de documentos. Cada uno está diseñado para ejecutarse en paralelo con múltiples modelos.

---

## 1. Patrón General: Extracción → Mapeo → Validación

### Fase 1: Extracción Textual (Genérica)

**Objetivo**: Extraer datos del documento SIN clasificar ni interpretar.

```markdown
## ROLE

Sos un experto en análisis de {DOMINIO} especializado en documentos {TIPO_DOCUMENTO}.

Tu objetivo es EXTRAER datos de {TIPO_DOCUMENTO} con precisión absoluta.

## CRITICAL INSTRUCTIONS

1. **OBSERVA**: Analiza tanto texto como imágenes. Las imágenes son la "fuente de verdad".

2. **ESCALA**: 
   - Identifica si los valores están en "{UNIDAD_1}" o "{UNIDAD_2}"
   - Reporta los montos tal cual aparecen en el documento

3. **FORMATO NUMÉRICO**:
   - Devuelve ÚNICAMENTE números (float/int)
   - Sin separadores de miles
   - Usa punto (.) para decimales
   - Ejemplo: "1.234.567,89" → 1234567.89
   - Si datos falta → usa `null` (NO 0.0 a menos que explícitamente esté)

4. **SIGNOS**:
   - Costos/Gastos: números POSITIVOS
   - Pérdidas/Deducciones: números NEGATIVOS
   - {OTRAS_REGLAS_DE_SIGNO}

5. **NO HAGAS**:
   - Clasificaciones
   - Interpretaciones
   - Completar datos faltantes
   - Suposiciones sobre estructura

6. **EXTRAE TODOS LOS PERÍODOS**: Si hay datos de múltiples años/meses → trae todos.

## FORMATO DE SALIDA

Responde ÚNICAMENTE con JSON válido (sin markdown, sin explicaciones):

\`\`\`json
{
  "metadata": {
    "titulo": "...",
    "fecha_documento": "YYYY-MM-DD",
    "periodo_reportado": "YYYY-MM-DD",
    "unidad_monetaria": "...",
    "{OTROS_CAMPOS_META}": null
  },
  "secciones": {
    "{SECCION_1}": {
      "campo_a": 0.0,
      "campo_b": 0.0,
      "{SUBSECCIONES}": {}
    },
    "{SECCION_2}": {...}
  },
  "periodos": [
    {
      "numero_periodo": 1,
      "fecha_inicio": "YYYY-MM-DD",
      "fecha_fin": "YYYY-MM-DD",
      "datos": {}
    }
  ]
}
\`\`\`
```

### Fase 2: Mapeo a Schema Estándar

**Objetivo**: Mapear campos extraídos a esquema unificado usando reglas de agregación.

```markdown
## ROLE

Sos un experto en normalización de datos de {DOMINIO}.

## INSTRUCCIONES

1. **RECIBISTE**:
   - JSON de extracción textual (Fase 1)
   - Schema estándar de {N} campos
   - Reglas de mapeo y agregación

2. **MAPEA** cada campo extraído al schema usando estas reglas:

   \`\`\`
   {REGLAS_DE_MAPEO}
   \`\`\`

   Ejemplos:
   - Si "Campo Origen A" + "Campo Origen B" → "Campo Estándar X"
   - Si "Campo Origen C" está vacío → busca equivalente "Campo Origen D"
   - Si múltiples valores → suma/promedia según regla

3. **VALIDA**:
   - Todos los campos estén presentes en output
   - Tipos de datos sean correctos (número, string, fecha)
   - Valores sean razonables (no NaN, no infinito)

4. **OUTPUT**:

   \`\`\`json
   {
     "empresa": {
       "nombre": "...",
       "id_interno": "..."
     },
     "periodos": [
       {
         "numero": 1,
         "campo_estandar_1": 0.0,
         "campo_estandar_2": 0.0,
         "{RESTO_CAMPOS_ESQUEMA}": null
       }
     ],
     "trazabilidad": {
       "campos_mapeados": 92,
       "campos_con_valor": 85,
       "campos_con_null": 7,
       "advertencias": []
     }
   }
   \`\`\`

## FORMATO

Responde ÚNICAMENTE con JSON válido.
```

---

## 2. Ejemplo Completo: Estados Contables (Proyecto Actual)

### Prompt Fase 1: Extracción Textual

```markdown
## ROLE

Sos un experto contable argentino especializado en análisis de balances y 
estados contables. Tu tarea es EXTRAER datos financieros de las páginas de 
un balance que te envían. Debes ser extremadamente preciso con los números.

## INSTRUCTIONS

1. **ANALIZAR**: Revisá tanto el texto extraído como las imágenes del balance 
   adjuntas. Las imágenes son la "fuente de verdad" si hay discrepancias con el texto.

2. **ESCALA**: Identificá si los valores están expresados en "Pesos" o 
   "Miles de Pesos". Reportá los montos tal cual aparecen en el documento.

3. **FORMATO**: 
   - Devolvé ÚNICAMENTE un objeto JSON
   - Los montos deben ser números (float), sin separadores de miles, 
     usando punto (.) para decimales
   - Si un dato no está presente, usá `null`. No completes con 0.0 a menos 
     que el balance indique explícitamente cero

4. **SIGNOS**: 
   - Costos y Gastos (CMV, Gastos Adm, etc.) se reportan como números POSITIVOS
   - Resultados netos o parciales que representen PÉRDIDA se reportan 
     con signo NEGATIVO

5. **ANALIZAR**:
   - Estado de Situación Patrimonial (ESP) – Activo y Pasivo
   - Estado de Resultados (ER)
   - Datos de la empresa y del ejercicio (caratula / encabezados)
   - Ambos ejercicios si aparecen (actual y comparativo)

## OUTPUT STRUCTURE

\`\`\`json
{
  "metadatos": {
    "cuit": "XX-XXXXXXXX-X",
    "razon_social": "...",
    "actividad": "...",
    "cifras_en": "Pesos/Miles de Pesos",
    "ejercicio_numero": 0,
    "duracion_meses": 12,
    "fecha_cierre": "YYYY-MM-DD",
    "dictamen": "Sin Salvedad/Con Salvedades/Abstencion"
  },
  "estado_situacion_patrimonial": {
    "activo_corriente": {
      "caja_e_inversiones": 0.0,
      "creditos_por_ventas": 0.0,
      "bienes_de_cambio": 0.0,
      "total_activo_corriente": 0.0
    },
    "pasivo_corriente": {
      "deuda_bancaria_cp": 0.0,
      "total_pasivo_corriente": 0.0
    },
    "patrimonio_neto": {
      "capital_social": 0.0,
      "resultado_ejercicio": 0.0,
      "total_patrimonio_neto": 0.0
    }
  },
  "estado_de_resultados": {
    "ventas": 0.0,
    "costo_de_ventas": 0.0,
    "resultado_bruto": 0.0,
    "gastos_administracion": 0.0,
    "resultado_operativo": 0.0,
    "resultado_neto": 0.0
  }
}
\`\`\`

Responde ÚNICAMENTE con JSON válido.
```

### Prompt Fase 2: Mapeo a Plan Estándar CRM

```markdown
## ROLE

Sos un experto contable senior especializado en normalización de balances 
hacia un plan de cuentas estándar CRM.

## INSTRUCCIONES

Recibiste un JSON de extracción textual (Fase 1) + el plan de cuentas 
estándar CRM (92 campos). 

Mapea cada campo extraído siguiendo estas reglas:

### Reglas de Agregación

**Otros Activos CP** = 
  Créditos Fiscales + Otros Créditos + Cuentas Vinculadas CP + Otros Activos Corrientes

**Otros Activos NC** = 
  Inversiones Vinculadas + Intangibles + Créditos Ventas LP + Otros Activos NC

**Otros Pasivos CP** = 
  Deudas Vinculadas CP + Previsiones CP + Otros Pasivos Corrientes

**Gastos Operativos** = 
  Gastos de Administración + Gastos de Comercialización 
  (sin incluir depreciaciones si están separadas)

**Resultados Extraordinarios** = 
  RECPAM + Diferencias de Cambio + Resultados por Tenencia 
  (si no tienen campo específico)

### Validaciones Matemáticas

1. Activo Total = Activo Corriente + Activo No Corriente
2. Pasivo Total = Pasivo Corriente + Pasivo No Corriente
3. Patrimonio Neto = Capital + Reservas + Resultados
4. Ecuación Fundamental: Activo = Pasivo + Patrimonio Neto (tolerancia 0.5%)
5. ER Verificación: Ventas - Costos - Gastos = Resultado Operativo

### OUTPUT

\`\`\`json
{
  "metadatos": {
    "cuit": "XX-XXXXXXXX-X",
    "razon_social": "...",
    "actividad": "...",
    "cifras_en": "Miles/Unidades",
    "ejercicio_numero": 0,
    "duracion_meses": 12,
    "fecha_cierre": "YYYY-MM-DD",
    "dictamen": "Sin Salvedad/Con Salvedades/Abstencion"
  },
  "estado_situacion_patrimonial": {
    "activo_corriente": {
      "caja_e_inversiones": 0.0,
      "creditos_por_ventas": 0.0,
      "bienes_de_cambio": 0.0,
      "creditos_fiscales": 0.0,
      "otros_creditos": 0.0,
      "creditos_vinculadas_cp": 0.0,
      "anticipos_accionistas": 0.0,
      "otros_activos_corrientes": 0.0,
      "total_activo_corriente": 0.0
    },
    "activo_no_corriente": {
      "bienes_de_uso": 0.0,
      "inversiones_vinculadas": 0.0,
      "activos_intangibles": 0.0,
      "creditos_vinculadas_lp": 0.0,
      "creditos_ventas_lp": 0.0,
      "bienes_cambio_nc": 0.0,
      "creditos_fiscales_lp": 0.0,
      "otros_activos_nc": 0.0,
      "total_activo_no_corriente": 0.0
    },
    "pasivo_corriente": {
      "deuda_bancaria_cp": 0.0,
      "ctas_pagar_comerciales_cp": 0.0,
      "anticipos_clientes": 0.0,
      "sueldos_cargas_sociales_cp": 0.0,
      "impuestos_pagar_cp": 0.0,
      "deuda_vinculadas_cp": 0.0,
      "previsiones_cp": 0.0,
      "otros_pasivos_cp": 0.0,
      "total_pasivo_corriente": 0.0
    },
    "pasivo_no_corriente": {
      "deuda_bancaria_lp": 0.0,
      "ctas_pagar_comerciales_lp": 0.0,
      "deuda_vinculadas_lp": 0.0,
      "deudas_sociales_lp": 0.0,
      "pasivos_impositivos_lp": 0.0,
      "previsiones_lp": 0.0,
      "otros_pasivos_lp": 0.0,
      "total_pasivo_no_corriente": 0.0
    },
    "patrimonio_neto": {
      "capital_social": 0.0,
      "aportes_irrevocables": 0.0,
      "reserva_legal": 0.0,
      "reserva_facultativa": 0.0,
      "revaluo_tecnico": 0.0,
      "resultados_anteriores": 0.0,
      "resultado_ejercicio": 0.0,
      "otras_ctas_patrimoniales": 0.0,
      "total_patrimonio_neto": 0.0
    }
  },
  "estado_de_resultados": {
    "ventas": 0.0,
    "costo_de_ventas": 0.0,
    "resultado_bruto": 0.0,
    "depreciacion_bdu": 0.0,
    "gastos_administracion": 0.0,
    "gastos_comercializacion": 0.0,
    "resultado_operativo": 0.0,
    "reintegros_exportaciones": 0.0,
    "beneficios_promocionales": 0.0,
    "resultado_tenencia_bc": 0.0,
    "otros_gastos_ingresos": 0.0,
    "ebit": 0.0,
    "resultado_vinculadas": 0.0,
    "intereses_ganados": 0.0,
    "intereses_pagados": 0.0,
    "diferencias_cambio": 0.0,
    "recpam": 0.0,
    "util_antes_impuestos": 0.0,
    "impuesto_ganancias": 0.0,
    "resultado_neto": 0.0,
    "resultado_impositivo_ddjj": 0.0
  }
}
\`\`\`

Responde ÚNICAMENTE con JSON válido.
```

---

## 3. Adaptaciones para Otros Dominios

### 3.1 Facturas / Comprobantes

```markdown
## ROLE

Sos un experto en procesamiento de facturas y comprobantes de compra/venta.

## EXTRAE

{
  "metadatos": {
    "numero_comprobante": "...",
    "tipo_comprobante": "Factura/Nota Crédito/Nota Débito",
    "fecha_emision": "YYYY-MM-DD",
    "fecha_vencimiento": "YYYY-MM-DD",
    "moneda": "ARS/USD",
    "cotizacion": 0.0
  },
  "emisor": {
    "razon_social": "...",
    "cuit": "...",
    "domicilio": "..."
  },
  "receptor": {
    "razon_social": "...",
    "cuit": "..."
  },
  "renglones": [
    {
      "numero": 1,
      "descripcion": "...",
      "cantidad": 0.0,
      "precio_unitario": 0.0,
      "subtotal": 0.0,
      "alicuota_iva": 0.0,
      "monto_iva": 0.0
    }
  ],
  "totales": {
    "subtotal": 0.0,
    "descuentos": 0.0,
    "monto_iva": 0.0,
    "monto_otros_impuestos": 0.0,
    "total": 0.0
  }
}
```

### 3.2 Reportes de Auditoría

```markdown
## ROLE

Sos un experto en análisis de reportes de auditoría y opiniones de auditores.

## EXTRAE

{
  "metadatos": {
    "fecha_reporte": "YYYY-MM-DD",
    "periodo_auditado": "YYYY-MM-DD a YYYY-MM-DD",
    "empresa_auditada": "...",
    "firma_auditora": "..."
  },
  "opinion": {
    "tipo": "Sin salvedad / Con salvedad / Abstencion / Adversa",
    "parrafos": [
      {
        "numero": 1,
        "contenido": "...",
        "relevancia": "alto/medio/bajo"
      }
    ]
  },
  "hallazgos": [
    {
      "numero": 1,
      "categoria": "...",
      "descripcion": "...",
      "impacto": "alto/medio/bajo",
      "recomendacion": "..."
    }
  ],
  "calificaciones": {
    "riesgo_global": "alto/medio/bajo",
    "confiabilidad_informacion": 0.0,
    "cumplimiento_normativo": 0.0
  }
}
```

---

## 4. Configuración en Python

### Template para Orquestador Genérico

```python
# orquestador_generico.py

from typing import TypedDict, Callable, Awaitable
import asyncio

class ExtractionConfig(TypedDict):
    """Configuración de extracción."""
    system_prompt: str
    user_prompt_template: str
    output_schema: dict
    extraction_timeout: float
    max_retries: int

class ExtractorInterface:
    """Interfaz base para extractores."""
    
    def __init__(self, name: str, model_id: str, config: ExtractionConfig):
        self.name = name
        self.model_id = model_id
        self.config = config
    
    async def extract(self, document_path: str, **kwargs):
        """Ejecuta extracción con el modelo."""
        raise NotImplementedError

async def orchestrate_extraction(
    document_paths: list[str],
    extractors: list[ExtractorInterface],
    reconcile_func: Callable,
    timeout: float = 1200,
):
    """
    Orquesta múltiples extractores en paralelo.
    
    1. Lanza todos los extractores en paralelo
    2. Reconcilia resultados (voto mayoritario)
    3. Retorna resultados individuales + conciliados
    """
    
    tasks = []
    for doc_path in document_paths:
        for extractor in extractors:
            task = asyncio.wait_for(
                extractor.extract(doc_path),
                timeout=timeout
            )
            tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Reconciliar
    reconciled = reconcile_func(results)
    
    return {
        "individual": results,
        "reconciled": reconciled,
    }
```

---

## 5. Plantilla de Prompt Dinámico

```python
# prompt_builder.py

class PromptBuilder:
    """Construye prompts dinámicos según dominio."""
    
    EXTRACTION_TEMPLATE = """
    ## ROLE
    {role}
    
    ## INSTRUCTIONS
    {instructions}
    
    ## FORMAT
    {format_spec}
    
    Responde ÚNICAMENTE con JSON válido.
    """
    
    @classmethod
    def build_extraction_prompt(
        cls,
        role: str,
        instructions: list[str],
        output_schema: dict,
        examples: list[dict] = None,
    ) -> str:
        """Construye prompt de extracción."""
        
        instructions_text = "\n".join(
            f"{i+1}. {inst}" for i, inst in enumerate(instructions)
        )
        
        format_spec = f"""Expected JSON structure:
        {json.dumps(output_schema, indent=2)}"""
        
        prompt = cls.EXTRACTION_TEMPLATE.format(
            role=role,
            instructions=instructions_text,
            format_spec=format_spec,
        )
        
        if examples:
            prompt += "\n## EXAMPLES\n"
            for ex in examples:
                prompt += f"Input: {ex['input']}\nOutput: {ex['output']}\n---\n"
        
        return prompt
```

---

## 6. Checklist de Adaptación

Para adaptar estos prompts a tu dominio:

- [ ] Definir ROLE (experto en tu dominio)
- [ ] Listar secciones/campos a extraer
- [ ] Definir reglas de formato numérico
- [ ] Definir reglas de signos/valores especiales
- [ ] Crear schema JSON esperado (Pydantic)
- [ ] Definir reglas de mapeo (si es multi-fase)
- [ ] Definir validaciones matemáticas internas
- [ ] Crear ejemplos (few-shot examples)
- [ ] Testear con 3+ modelos diferentes
- [ ] Medir precisión vs ground truth
- [ ] Iterar prompts basado en resultados

---

**Última actualización**: 2026-04-16  
**Versión**: 1.0
