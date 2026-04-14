"""Agente E: Validador y Normalizador — Spec-02."""
from __future__ import annotations

import re
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from src.models.document import AgentMetadata, AgentOutput, AgentStatus, FieldValue


class ValidatorNormalizerAgent:
    """
    Normaliza fechas, montos y moneda. Aplica validaciones genéricas.
    Timeout: 2s. No es bloqueante — produce warnings, no reclasifica.
    """

    agent_id = "validator"
    timeout_ms = 2000

    DATE_FORMATS = [
        r"(\d{2})/(\d{2})/(\d{4})",   # DD/MM/YYYY
        r"(\d{4})-(\d{2})-(\d{2})",    # YYYY-MM-DD
        r"(\d{2})-(\d{2})-(\d{4})",    # DD-MM-YYYY
    ]

    def normalize(
        self,
        document_id: str,
        fields: Dict[str, FieldValue],
    ) -> AgentOutput:
        start = time.monotonic()
        normalized: Dict[str, FieldValue] = {}
        warnings: List[str] = []

        for name, fv in fields.items():
            if fv.value is None:
                normalized[name] = fv
                continue

            if "date" in name or name in ("period_start", "period_end"):
                val, warn = self._normalize_date(name, fv.value)
                if warn:
                    warnings.append(warn)
                normalized[name] = FieldValue(value=val, confidence=fv.confidence)

            elif name in ("total_amount", "subtotal", "tax_amount"):
                val, warn = self._normalize_amount(name, fv.value)
                if warn:
                    warnings.append(warn)
                normalized[name] = FieldValue(value=val, confidence=fv.confidence)

            elif name == "currency":
                normalized[name] = FieldValue(
                    value=str(fv.value).upper().strip()[:3],
                    confidence=fv.confidence,
                )

            elif name == "provider_name":
                normalized[name] = FieldValue(
                    value=str(fv.value).strip().title() if fv.value else fv.value,
                    confidence=fv.confidence,
                )

            else:
                normalized[name] = fv

        elapsed = int((time.monotonic() - start) * 1000)

        return AgentOutput(
            document_id=document_id,
            agent_id=self.agent_id,
            status=AgentStatus.SUCCESS,
            duration_ms=elapsed,
            fields=normalized,
            raw_text="\n".join(warnings) if warnings else None,
            metadata=AgentMetadata(
                model_version="validator-normalizer-1.0",
                field_count=len(normalized),
                fields_with_confidence_gt_0_85=sum(
                    1 for f in normalized.values() if f.confidence >= 0.85
                ),
            ),
        )

    def _normalize_date(self, field_name: str, raw: Any) -> Tuple[Optional[str], Optional[str]]:
        if not raw:
            return None, None
        s = str(raw).strip()

        # Ya en formato ISO
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s, None

        # Intentar parsear formatos alternativos
        for pattern in self.DATE_FORMATS:
            m = re.match(pattern, s)
            if m:
                g = m.groups()
                try:
                    if len(g[0]) == 4:  # YYYY-MM-DD
                        parsed = date(int(g[0]), int(g[1]), int(g[2]))
                    else:               # DD/MM/YYYY or DD-MM-YYYY
                        parsed = date(int(g[2]), int(g[1]), int(g[0]))
                    return parsed.isoformat(), None
                except ValueError:
                    continue

        return s, f"Formato de fecha no reconocido en {field_name}: {s!r}"

    def _normalize_amount(self, field_name: str, raw: Any) -> Tuple[Optional[float], Optional[str]]:
        if raw is None:
            return None, None
        try:
            if isinstance(raw, (int, float)):
                return float(raw), None
            # Limpiar formato: quitar $ y espacios, convertir comas
            s = str(raw).strip().replace("$", "").replace(" ", "")
            # Manejar separadores de miles: 12.345,67 → 12345.67
            if "," in s and "." in s:
                if s.index(",") < s.index("."):  # coma como miles
                    s = s.replace(",", "")
                else:  # punto como miles, coma como decimal
                    s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            return round(float(s), 2), None
        except (ValueError, TypeError):
            return None, f"Monto inválido en {field_name}: {raw!r}"
