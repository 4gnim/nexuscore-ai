import re
from typing import Any, Literal, TypeVar
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import BaseModel
from app.core.config import get_settings

settings = get_settings()
T = TypeVar("T", bound=BaseModel)


def _extract_text_from_content(content: Any) -> str:
    """Mengekstrak string teks bersih baik dari str biasa maupun list content blocks (Gemini 3.x)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if "text" in block:
                    parts.append(str(block["text"]))
        return "\n".join(parts)
    return str(content)


def _strip_thinking_and_fences(raw_text: str) -> str:
    """Membersihkan tag <think>...</think> (Qwen3) dan markdown code fences."""
    cleaned = re.sub(
        r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE
    ).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_json_object(text: str) -> str:
    """Mengambil substring JSON object {...} terluar."""
    cleaned = _strip_thinking_and_fences(text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _build_compact_schema_hint(schema: type[BaseModel]) -> str:
    """Membentuk ringkasan field Pydantic yang hemat token untuk mencegah Groq TPM limit."""
    lines: list[str] = ["{"]
    for field_name, field_info in schema.model_fields.items():
        desc = field_info.description or ""
        lines.append(f'  "{field_name}": <{field_info.annotation}> // {desc}')
    lines.append("}")
    return "\n".join(lines)


def _build_provider_chain(
    task_tier: Literal["fast", "reasoning"] = "fast",
    temperature: float = 0.0,
) -> list[tuple[str, object]]:
    """Menyusun urutan model aktif dengan max_retries=0 untuk instant failover."""
    chain: list[tuple[str, object]] = []

    groq_models = (
        [settings.groq_fast_model, settings.groq_primary_model]
        if task_tier == "fast"
        else [settings.groq_primary_model, settings.groq_fast_model]
    )

    if settings.groq_api_key and "isi_api_key" not in settings.groq_api_key:
        for model_id in groq_models:
            chain.append(
                (
                    f"groq:{model_id}",
                    ChatGroq(
                        api_key=settings.groq_api_key,
                        model=model_id,
                        temperature=temperature,
                        max_retries=0,
                        timeout=45,
                    ),
                )
            )

    if settings.gemini_api_key and "isi_api_key" not in settings.gemini_api_key:
        for model_id in settings.fallback_model_cascade:
            chain.append(
                (
                    f"gemini:{model_id}",
                    ChatGoogleGenerativeAI(
                        google_api_key=settings.gemini_api_key,
                        model=model_id,
                        temperature=temperature,
                        max_retries=0,
                        timeout=45,
                    ),
                )
            )

    if not chain:
        raise RuntimeError(
            "Tidak ada API key LLM aktif di .env (GROQ_API_KEY atau GEMINI_API_KEY kosong)."
        )
    return chain


def invoke_text_with_failover(
    system_prompt: str,
    user_prompt: str,
    task_tier: Literal["fast", "reasoning"] = "reasoning",
    temperature: float = 0.1,
) -> tuple[str, str]:
    """Menjalankan inferensi teks dengan instant failover lintas Groq & Gemini."""
    chain = _build_provider_chain(task_tier=task_tier, temperature=temperature)
    errors: list[str] = []

    for label, llm in chain:
        try:
            response = llm.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            raw_text = _extract_text_from_content(response.content)
            cleaned = _strip_thinking_and_fences(raw_text)
            if cleaned:
                return cleaned, label
        except Exception as exc:
            errors.append(f"{label} -> {type(exc).__name__}: {str(exc)[:140]}")
            continue

    raise RuntimeError("Seluruh provider LLM gagal merespons:\n" + "\n".join(errors))


def invoke_structured_with_failover(
    system_prompt: str,
    user_prompt: str,
    schema: type[T],
    task_tier: Literal["fast", "reasoning"] = "fast",
    temperature: float = 0.0,
    schema_example: str | None = None,
) -> tuple[T, str]:
    """Menjalankan ekstraksi JSON terstruktur tervalidasi Pydantic dengan instant failover."""
    format_guide = schema_example or _build_compact_schema_hint(schema)
    enforced_system = (
        f"{system_prompt}\n\n"
        "ATURAN OUTPUT WAJIB:\n"
        "- Kembalikan HANYA satu objek JSON valid tanpa narasi atau markdown.\n"
        f"- Format JSON:\n{format_guide}"
    )

    chain = _build_provider_chain(task_tier=task_tier, temperature=temperature)
    errors: list[str] = []

    for label, llm in chain:
        try:
            response = llm.invoke(
                [
                    SystemMessage(content=enforced_system),
                    HumanMessage(content=user_prompt),
                ]
            )
            raw_text = _extract_text_from_content(response.content)
            json_str = _extract_json_object(raw_text)
            parsed = schema.model_validate_json(json_str)
            return parsed, label
        except Exception as exc:
            errors.append(f"{label} -> {type(exc).__name__}: {str(exc)[:160]}")
            continue

    raise RuntimeError(
        "Ekstraksi terstruktur gagal pada semua provider LLM:\n" + "\n".join(errors)
    )
