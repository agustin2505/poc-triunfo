# Guía Rectora para Creación de Specs

> Este documento define el formato, estructura y reglas para crear especificaciones de infraestructura en este repositorio. Toda spec nueva DEBE seguir esta guía.

---

## Principios

1. **Una spec = una unidad de trabajo desplegable.** No mezclar recursos de stages distintos.
2. **Spec antes que código.** No escribir Terraform ni Helm sin spec aprobada.
3. **Sin código en la spec.** La spec define QUÉ y POR QUÉ, nunca CÓMO. No incluir bloques HCL, YAML, ni snippets de implementación. Si hay valores específicos (nombres, CIDRs, sizing), usar tablas.
4. **Directa y precisa.** Sin introducciones innecesarias, sin repetir información del contexto general. Ir al grano.
5. **Idempotente.** La spec debe poder leerse en cualquier momento y ser suficiente para implementar o validar.

---

## Estructura de directorios

```
specs/
├── SPEC-GUIDE.md          ← este archivo
├── dev/                   ← ambiente desarrollo
│   ├── INDEX.md
│   ├── workloads-dev/     ← specs de infraestructura Terraform
│   └── deploy-dev/        ← specs de deploy Helm
├── qas/                   ← ambiente QA
├── prod/                  ← ambiente producción
└── shared/                ← specs cross-environment
```

Cada ambiente organiza sus specs por stage de infraestructura, alineado con `fast/tenants/macro/`:

| Stage | Carpeta | Scope |
|-------|---------|-------|
| 1 | `1-networking/` | VPC, subnets, firewall, NAT, DNS |
| 2 | `2-security/` | KMS, audit logging, VPC-SC |
| 3 | `3-project-factory/` | Proyectos workload |
| 4 | `4-workloads-ecm/` | VMs OpenText ECM |
| 5 | `5-workloads-ai/` | GKE, Cloud SQL, GCS, IAM, WIF |
| 6 | `6-deploy-airflow/` | Helm Airflow |
| 7 | `7-deploy-langfuse/` | Helm Langfuse |

---

## Naming

```
{ID}_{slug}.md
```

| Ambiente | Prefijo | Ejemplo |
|----------|---------|---------|
| Dev | `P-`, `E-`, `A-`, `D-`, `V-` (por track) | `A-02_ai-gke-cluster.md` |
| QA | `Q-{NN}` | `Q-05_workloads-ai-qa.md` |
| Prod | `P-{NN}` | `P-01_production-workloads-stage.md` |
| Shared | `INFRA-{slug}` | `INFRA-S8-01_cd-pipeline-trigger.md` |

Slug en kebab-case, descriptivo, sin palabras genéricas ("new", "add", "update").

---

## Plantilla

```markdown
# {ID}: {Título conciso}

## Meta

| Campo | Valor |
|-------|-------|
| Track | {stage o track} |
| Prioridad | {Crítica / Alta / Media} |
| Estado | {pending / in-progress / done / blocked} |
| Bloqueante para | {IDs de specs que dependen de esta} |
| Depende de | {IDs de specs prerequisito} |
| Stage Terraform | {path al stage, ej: `fast/tenants/macro/5-workloads-ai/`} |
| Estimación | {S (1-2h) / M (2-4h) / L (4-8h)} |

## Contexto

{2-4 párrafos máximo. Describir:}
- {Qué existe hoy (estado actual)}
- {Qué falta y por qué se necesita}
- {Decisiones relevantes ya tomadas}

## Pre-requisitos

- [ ] {Spec ID} done: {descripción breve de lo que debe existir}
- [ ] {recurso/permiso/API que debe estar disponible}

## Spec

{Sección principal. Describir los recursos/acciones a nivel declarativo:}
- {Qué recursos crear/modificar/eliminar}
- {Configuración clave en tablas (nombres, sizing, flags)}
- {Relaciones entre recursos}

{Usar tablas para valores concretos:}

| Recurso | Nombre | Configuración clave |
|---------|--------|---------------------|
| ... | ... | ... |

## Out of Scope

- {Qué NO se debe implementar en esta spec}
- {Qué se deja para otra spec (referenciar ID)}

## Acceptance Criteria

- [ ] {Criterio verificable: recurso existe, estado esperado}
- [ ] {Criterio verificable: permiso funciona}
- [ ] {Criterio verificable: `terraform validate` pasa}
```

---

## Reglas para el contenido

### Spec section

- Describir recursos de forma declarativa: "Crear un bucket GCS con lifecycle 90d→Nearline" en vez de copiar el bloque Terraform.
- Usar tablas para valores específicos (nombres, CIDRs, machine types, sizing).
- Si un recurso tiene configuración compleja, desglosar en sub-tablas.
- No referenciar archivos `.tf` específicos — el agente decide dónde implementar.

### Out of Scope

Obligatorio. Debe listar explícitamente:
- Recursos que podrían confundirse como parte de esta spec pero pertenecen a otra.
- Configuraciones que se dejan para una fase posterior.

### Acceptance Criteria

- Cada criterio debe ser verificable con un comando o inspección visual.
- Formato checklist (`- [ ]`). El agente marca cada item al implementar.
- Mínimo: `terraform validate` pasa, recursos existen en el estado esperado.
- Para deploys Helm: pods running, health checks passing.

### Qué NO incluir

- Bloques de código (HCL, YAML, Bash, JSON).
- Instrucciones paso a paso de ejecución (`terraform init`, `helm install`).
- Screenshots o logs.
- Historial de cambios o decisiones anteriores (eso va en ADRs o commit history).
- Información duplicada de otras specs — referenciar por ID.

---

## Estados y ciclo de vida

```
pending → in-progress → done
            ↓
          blocked → in-progress → done
```

| Estado | Significado | Quién cambia |
|--------|-------------|-------------|
| `pending` | Spec aprobada, esperando dependencias o turno | Humano |
| `in-progress` | Implementación activa | Agente al iniciar |
| `done` | Implementada, acceptance criteria cumplidos | Agente al completar |
| `blocked` | Dependencia externa no resuelta | Agente o humano |
| `superseded` | Reemplazada por otra spec (referenciar nueva) | Humano |

---

## Reglas para agentes

1. **Leer esta guía y la spec completa** antes de implementar.
2. **Verificar pre-requisitos.** No arrancar si las dependencias no están `done`.
3. **Respetar Out of Scope.** No implementar más de lo especificado.
4. **No inventar recursos** que la spec no menciona.
5. **Validar antes de marcar done:** `terraform validate` para IaC, `helm template` dry-run para deploys.
6. **No hacer `terraform apply` ni `helm install`** sin aprobación explícita del humano.
7. **Marcar acceptance criteria** conforme se cumplen.
8. **Si hay ambigüedad, preguntar.** No asumir — usar AskUserQuestion.

---

## Ejecución de una spec

### Prompt maestro

Copiar y pegar el siguiente prompt, reemplazando `{ID}`, `{path}` y las reglas específicas de la spec:

```
Implementa la spec {ID} ubicada en {path/a/la/spec.md}

Reglas de ejecución:
1. Lee primero la guía rectora en specs/SPEC-GUIDE.md y la spec completa antes de escribir código.
2. Verifica que los pre-requisitos estén cumplidos. Si no lo están, avísame antes de continuar.
3. Implementa siguiendo la spec. NO ejecutes terraform apply ni helm install sin mi aprobación explícita.
4. Completa datos faltantes con placeholders claros (ej. "COMPLETAR_TELEFONO") donde no tengas datos reales.
5. Ejecuta terraform validate (o helm template --dry-run) para verificar que compila.
6. Marca los acceptance criteria cumplidos conforme avances.
7. Al finalizar (spec marcada como done), genera el archivo {spec-name}.log.md junto a la spec documentando el proceso de implementación según la plantilla de log definida en esta guía.

{Reglas adicionales específicas de la spec, si las hay}
```

### Log de implementación

Al completar una spec (estado → `done`), el agente DEBE crear un archivo `.log.md` junto a la spec:

```
specs/shared/INFRA-domain-registration-groupitmind-cloud.md       ← spec (QUÉ)
specs/shared/INFRA-domain-registration-groupitmind-cloud.log.md   ← log (CÓMO)
```

### Plantilla del log

```markdown
# {ID}: Log de implementación

| Campo | Valor |
|-------|-------|
| Fecha | {YYYY-MM-DD} |
| Duración estimada | {tiempo real de ejecución} |
| Agente | {modelo usado} |

## Secuencia de pasos

1. {Paso ejecutado y resultado}
2. {Paso ejecutado y resultado}
...

## Decisiones tomadas

| Decisión | Motivo |
|----------|--------|
| {Qué se decidió} | {Por qué} |

## Errores y resoluciones

| Error | Causa | Resolución |
|-------|-------|------------|
| {Descripción del error} | {Causa raíz} | {Cómo se resolvió} |

Si no hubo errores, escribir "Ninguno".

## Diferencias vs spec

| Aspecto | Spec decía | Realidad |
|---------|-----------|----------|
| {Qué cambió} | {Valor original} | {Valor real} |

Si no hubo diferencias, escribir "Ninguna".

## Pre-requisitos descubiertos

- {Pre-requisitos que la spec no mencionaba pero fueron necesarios}

Si no hubo pre-requisitos adicionales, escribir "Ninguno".
```

---

## Cómo crear una spec nueva

1. Identificar el stage y ambiente.
2. Asignar ID según convención de naming del ambiente.
3. Copiar la plantilla de arriba.
4. Completar todas las secciones. Si una sección no aplica, escribir "N/A" — no eliminarla.
5. Agregar la spec al `README.md` o `INDEX.md` del ambiente correspondiente.
6. Estado inicial: `pending`.
