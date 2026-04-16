"""Prompts compartidos para agentes Vertex AI — delega a prompts_imagen.py (Spec-18)."""
from src.agents.prompts_imagen import (  # noqa: F401  (re-export)
    SYSTEM_PROMPT_FASE1,
    USER_PROMPT_FASE1,
    SCHEMA_FASE1,
    build_fase1_parts_gemini as build_prompts,
    parse_json_response,
    map_fase1_to_agent_fields,
    inject_schema,
)
