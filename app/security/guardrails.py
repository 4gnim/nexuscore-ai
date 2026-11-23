import re
from dataclasses import dataclass
from app.core.config import get_settings

settings = get_settings()

ALLOWED_ROLES = {"Viewer", "Analyst", "SupplyChainDirector", "Admin"}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "Viewer": {"read_dashboard", "view_audit"},
    "Analyst": {"read_dashboard", "view_audit", "run_investigation", "run_simulation"},
    "SupplyChainDirector": {
        "read_dashboard",
        "view_audit",
        "run_investigation",
        "run_simulation",
        "approve_hitl",
    },
    "Admin": {
        "read_dashboard",
        "view_audit",
        "run_investigation",
        "run_simulation",
        "approve_hitl",
        "manage_tenant",
    },
}

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "SYSTEM_PROMPT_OVERRIDE",
        re.compile(
            r"\b(ignore\s+(all\s+)?(previous|prior|above)\s+instructions|disregard\s+system\s+prompt|jailbreak|developer\s+mode)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "SQL_DDL_DML_INJECTION",
        re.compile(
            r"\b(drop\s+table|truncate\s+table|delete\s+from|alter\s+table|union\s+select|;\s*--)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "CROSS_TENANT_EXFILTRATION",
        re.compile(
            r"\b(bypass\s+tenant|all\s+tenants|other\s+tenant|dump\s+database|export\s+\.env|reveal\s+api\s+key)\b",
            re.IGNORECASE,
        ),
    ),
]

PII_REDACTION_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "[REDACTED_API_KEY]",
        re.compile(
            r"\b(gsk_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z\-_]{20,}|sk-[A-Za-z0-9]{20,})\b"
        ),
    ),
    ("[REDACTED_CARD]", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("[REDACTED_SSN]", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]


@dataclass
class SecurityInspectionResult:
    allowed: bool
    sanitized_text: str
    blocked_reason: str | None = None
    matched_rule: str | None = None
    pii_redacted_count: int = 0


def redact_sensitive_pii(text: str) -> tuple[str, int]:
    """Menyensor API key, nomor kartu kredit, dan identitas sensitif dari teks."""
    sanitized = text
    total_redactions = 0
    for replacement, pattern in PII_REDACTION_RULES:
        sanitized, count = pattern.subn(replacement, sanitized)
        total_redactions += count
    return sanitized, total_redactions


def inspect_prompt_security(raw_query: str) -> SecurityInspectionResult:
    """Memvalidasi kueri pengguna terhadap ancaman Prompt Injection & kebocoran PII."""
    if not raw_query or not raw_query.strip():
        return SecurityInspectionResult(
            allowed=False,
            sanitized_text="",
            blocked_reason="Kueri tidak boleh kosong.",
            matched_rule="EMPTY_INPUT",
        )

    if len(raw_query) > 4000:
        return SecurityInspectionResult(
            allowed=False,
            sanitized_text=raw_query[:200],
            blocked_reason="Panjang kueri melebihi batas maksimum 4.000 karakter.",
            matched_rule="MAX_LENGTH_EXCEEDED",
        )

    for rule_name, pattern in INJECTION_PATTERNS:
        if pattern.search(raw_query):
            return SecurityInspectionResult(
                allowed=False,
                sanitized_text=raw_query,
                blocked_reason=f"Permintaan diblokir oleh OWASP GenAI Guardrail ({rule_name}).",
                matched_rule=rule_name,
            )

    sanitized, redaction_count = redact_sensitive_pii(raw_query.strip())
    return SecurityInspectionResult(
        allowed=True,
        sanitized_text=sanitized,
        pii_redacted_count=redaction_count,
    )


def enforce_rbac_and_tenant(
    user_role: str,
    required_permission: str,
    requested_tenant_id: str,
    session_tenant_id: str | None = None,
) -> None:
    """Menegakkan kebijakan akses RBAC (GOV-SEC-01) dan isolasi ketat antar-tenant."""
    expected_tenant = session_tenant_id or settings.default_tenant_id
    if requested_tenant_id != expected_tenant:
        raise PermissionError(
            f"Akses lintas-tenant ditolak (GOV-SEC-01): '{requested_tenant_id}' tidak cocok dengan konteks sesi '{expected_tenant}'."
        )

    if user_role not in ALLOWED_ROLES:
        raise PermissionError(f"Peran pengguna tidak valid: '{user_role}'.")

    perms = ROLE_PERMISSIONS.get(user_role, set())
    if required_permission not in perms:
        raise PermissionError(
            f"Otorisasi ditolak (GOV-SEC-01): Peran '{user_role}' tidak memiliki izin '{required_permission}'."
        )
