"""Lógica de conciliación multi-agente — Spec-04."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.models.document import (
    AgentOutput, AgentStatus, ConciliationField,
    DocumentCategory, FieldValue, RoutingDecision, SourceDetail,
)

try:
    from Levenshtein import ratio as levenshtein_ratio
except ImportError:
    def levenshtein_ratio(a: str, b: str) -> float:  # type: ignore[misc]
        """Fallback simple si python-Levenshtein no está instalado."""
        if a == b:
            return 1.0
        shorter, longer = sorted([a, b], key=len)
        if not longer:
            return 1.0
        return len(shorter) / len(longer)

CRITICAL_FIELDS = {"provider_name", "issue_date", "total_amount"}
NUMERIC_FIELDS = {"total_amount", "subtotal", "tax_amount", "consumption"}
DATE_FIELDS = {"issue_date", "due_date", "period_start", "period_end"}
NUMERIC_TOLERANCE = 0.05  # 5%
FUZZY_THRESHOLD = 0.90    # similitud mínima para fuzzy match en strings


class Conciliator:
    """
    Implementa el algoritmo de conciliación del Spec-04:
    - Strings: mayoría simple + fuzzy match
    - Numéricos: promedio ponderado si desviación ≤5%, mayoría si no
    - Fechas: parsing flexible + mayoría
    - Confidence final + penalizaciones
    """

    def conciliate(
        self,
        agent_outputs: Dict[str, AgentOutput],
    ) -> Tuple[Dict[str, ConciliationField], float, RoutingDecision, str]:
        """
        Devuelve (extracted_fields, confidence_score, routing, routing_reason).
        Usa outputs de docai, tesseract y vertex (si disponibles).
        """
        # Recopilar todos los campos de agentes válidos
        valid_outputs = {
            aid: out for aid, out in agent_outputs.items()
            if out.status == AgentStatus.SUCCESS
            and aid in ("docai", "tesseract", "vertex")
        }

        if not valid_outputs:
            return {}, 0.0, RoutingDecision.AUTO_REJECT, "Todos los agentes fallaron"

        # Unión de campos disponibles
        all_field_names = set()
        for out in valid_outputs.values():
            all_field_names.update(out.fields.keys())

        conciliated: Dict[str, ConciliationField] = {}
        for field_name in all_field_names:
            agent_values = {
                aid: out.fields[field_name]
                for aid, out in valid_outputs.items()
                if field_name in out.fields and out.fields[field_name].value is not None
            }
            if not agent_values:
                conciliated[field_name] = ConciliationField(
                    value=None, confidence=0.0, source="missing"
                )
            elif field_name in NUMERIC_FIELDS:
                conciliated[field_name] = self._conciliate_numeric(field_name, agent_values)
            elif field_name in DATE_FIELDS:
                conciliated[field_name] = self._conciliate_date(field_name, agent_values)
            else:
                conciliated[field_name] = self._conciliate_string(field_name, agent_values)

        confidence_score, routing, reason = self._compute_routing(conciliated)
        return conciliated, confidence_score, routing, reason

    # ------------------------------------------------------------------
    # Conciliación por tipo de campo
    # ------------------------------------------------------------------

    def _conciliate_string(
        self, field_name: str, values: Dict[str, FieldValue]
    ) -> ConciliationField:
        sources_detail = {
            aid: SourceDetail(value=fv.value, confidence=fv.confidence)
            for aid, fv in values.items()
        }

        if len(values) == 1:
            aid, fv = next(iter(values.items()))
            return ConciliationField(
                value=fv.value, confidence=fv.confidence,
                source=aid, sources_detail=sources_detail,
            )

        # Normalizar a string para comparar
        str_values = {aid: (str(fv.value).lower().strip(), fv.confidence)
                      for aid, fv in values.items()}

        # Contar grupos por mayoría (con fuzzy match)
        groups: List[List[str]] = []
        for aid, (val, _) in str_values.items():
            placed = False
            for group in groups:
                rep_aid = group[0]
                rep_val = str_values[rep_aid][0]
                if levenshtein_ratio(val, rep_val) >= FUZZY_THRESHOLD:
                    group.append(aid)
                    placed = True
                    break
            if not placed:
                groups.append([aid])

        # Grupo mayoritario (≥2 agentes) o fallback a mayor confidence
        majority_group = next(
            (g for g in sorted(groups, key=len, reverse=True) if len(g) >= 2), None
        )

        has_conflict = len(groups) > 1

        if majority_group:
            # Usar el valor del agente con mayor confidence en el grupo
            best_aid = max(majority_group, key=lambda a: values[a].confidence)
            conf = sum(values[a].confidence for a in majority_group) / len(majority_group)
            if has_conflict:
                conf *= 0.90  # penalización por conflicto
            return ConciliationField(
                value=values[best_aid].value,
                confidence=round(min(1.0, conf), 3),
                source="majority",
                sources_detail=sources_detail,
            )

        # Empate o todos discrepan → usar mayor confidence (fallback docai si disponible)
        if "docai" in values:
            best_aid = "docai"
        else:
            best_aid = max(values, key=lambda a: values[a].confidence)

        conf = values[best_aid].confidence * 0.90  # penalización por no mayoría
        return ConciliationField(
            value=values[best_aid].value,
            confidence=round(conf, 3),
            source=f"fallback_{best_aid}",
            sources_detail=sources_detail,
        )

    def _conciliate_numeric(
        self, field_name: str, values: Dict[str, FieldValue]
    ) -> ConciliationField:
        sources_detail = {
            aid: SourceDetail(value=fv.value, confidence=fv.confidence)
            for aid, fv in values.items()
        }

        if len(values) == 1:
            aid, fv = next(iter(values.items()))
            return ConciliationField(
                value=fv.value, confidence=fv.confidence,
                source=aid, sources_detail=sources_detail,
            )

        floats = {}
        for aid, fv in values.items():
            try:
                floats[aid] = float(fv.value)
            except (TypeError, ValueError):
                continue

        if not floats:
            return ConciliationField(value=None, confidence=0.0, source="failed")

        numeric_vals = list(floats.values())
        max_v, min_v = max(numeric_vals), min(numeric_vals)

        # Calcular desviación relativa
        deviation = (max_v - min_v) / max_v if max_v != 0 else 0.0

        if deviation <= NUMERIC_TOLERANCE:
            # Promedio ponderado por confidence
            total_conf = sum(values[aid].confidence for aid in floats)
            weighted = sum(
                floats[aid] * values[aid].confidence for aid in floats
            ) / total_conf if total_conf > 0 else sum(numeric_vals) / len(numeric_vals)
            conf = sum(values[aid].confidence for aid in floats) / len(floats)
            return ConciliationField(
                value=round(weighted, 2),
                confidence=round(conf, 3),
                source="weighted_avg",
                sources_detail=sources_detail,
            )
        else:
            # Desviación > 5% → mayoría exacta o max confidence
            exact_groups: Dict[float, List[str]] = {}
            for aid, v in floats.items():
                placed = False
                for key in exact_groups:
                    if abs(key - v) < 0.01:
                        exact_groups[key].append(aid)
                        placed = True
                        break
                if not placed:
                    exact_groups[v] = [aid]

            majority = max(exact_groups.items(), key=lambda kv: len(kv[1]))
            majority_val, majority_agents = majority

            if len(majority_agents) >= 2:
                conf = sum(values[a].confidence for a in majority_agents) / len(majority_agents)
                conf -= 0.05  # penalización por desviación
            else:
                best_aid = max(floats, key=lambda a: values[a].confidence)
                majority_val = floats[best_aid]
                conf = values[best_aid].confidence - 0.05

            return ConciliationField(
                value=round(majority_val, 2),
                confidence=round(max(0.0, conf), 3),
                source="majority_exact",
                sources_detail=sources_detail,
            )

    def _conciliate_date(
        self, field_name: str, values: Dict[str, FieldValue]
    ) -> ConciliationField:
        sources_detail = {
            aid: SourceDetail(value=fv.value, confidence=fv.confidence)
            for aid, fv in values.items()
        }
        if len(values) == 1:
            aid, fv = next(iter(values.items()))
            return ConciliationField(
                value=fv.value, confidence=fv.confidence,
                source=aid, sources_detail=sources_detail,
            )

        # Normalizar fechas a ISO
        iso_vals: Dict[str, str] = {}
        for aid, fv in values.items():
            if fv.value:
                iso_vals[aid] = str(fv.value)[:10]  # ya normalizadas por Agente E

        # Mayoría simple
        from collections import Counter
        counts = Counter(iso_vals.values())
        most_common_val, most_common_count = counts.most_common(1)[0]

        if most_common_count >= 2:
            conf_sources = [values[aid].confidence for aid, v in iso_vals.items()
                            if v == most_common_val]
            conf = sum(conf_sources) / len(conf_sources)
            return ConciliationField(
                value=most_common_val,
                confidence=round(conf, 3),
                source="majority",
                sources_detail=sources_detail,
            )

        # Sin mayoría → mayor confidence
        if "docai" in values:
            best_aid = "docai"
        else:
            best_aid = max(iso_vals, key=lambda a: values[a].confidence)

        return ConciliationField(
            value=iso_vals.get(best_aid),
            confidence=round(values[best_aid].confidence * 0.90, 3),
            source=f"fallback_{best_aid}",
            sources_detail=sources_detail,
        )

    # ------------------------------------------------------------------
    # Scoring y routing
    # ------------------------------------------------------------------

    def _compute_routing(
        self, fields: Dict[str, ConciliationField]
    ) -> Tuple[float, RoutingDecision, str]:
        # Confidence de campos críticos
        critical_confs = []
        has_critical_missing = False

        for fname in CRITICAL_FIELDS:
            cf = fields.get(fname)
            if cf is None or cf.value is None:
                has_critical_missing = True
                critical_confs.append(0.0)
            else:
                critical_confs.append(cf.confidence)

        if has_critical_missing:
            return 0.3, RoutingDecision.HITL_PRIORITY, "Campo crítico faltante"

        if not critical_confs:
            return 0.0, RoutingDecision.AUTO_REJECT, "Sin campos extraídos"

        score = sum(critical_confs) / len(critical_confs)
        score = round(score, 3)

        if score >= 0.88:
            return score, RoutingDecision.AUTO_APPROVE, f"Confidence {score:.2f} ≥ 0.88"
        elif score >= 0.70:
            return score, RoutingDecision.HITL_STANDARD, f"Confidence {score:.2f} en rango 0.70-0.88"
        elif score >= 0.40:
            return score, RoutingDecision.HITL_PRIORITY, f"Confidence {score:.2f} < 0.70"
        else:
            return score, RoutingDecision.AUTO_REJECT, f"Confidence {score:.2f} < 0.40"
