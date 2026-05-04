from __future__ import annotations

import re
from typing import Any


MARKDOWN_REPLACEMENTS = [
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE), ""),
    (re.compile(r"\*\*(.*?)\*\*", re.DOTALL), r"\1"),
    (re.compile(r"__(.*?)__", re.DOTALL), r"\1"),
    (re.compile(r"(?<!\*)\*(?!\*)([^\n*]+?)(?<!\*)\*(?!\*)"), r"\1"),
    (re.compile(r"(?<!_)_(?!_)([^\n_]+?)(?<!_)_(?!_)"), r"\1"),
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),
    (re.compile(r"^\s*>\s*", re.MULTILINE), ""),
    (re.compile(r"```(?:\w+)?\s*|```"), ""),
]

FORBIDDEN_CLIENT_MARKERS = [
    "section_evidence_pack",
    "evidence_pack",
    "JSON",
    "payload",
    "debug",
    "confirmation_matrix",
    "hard_event",
    "allowed_theme_blocks",
    "score",
]


def clean_client_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = str(text).replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in MARKDOWN_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def clean_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    cleaned = dict(payload)
    if isinstance(cleaned.get("full_text"), str):
        cleaned["full_text"] = clean_client_text(cleaned["full_text"])
    sections = cleaned.get("sections")
    if isinstance(sections, dict):
        cleaned["sections"] = {
            key: clean_client_text(value) if isinstance(value, str) else value
            for key, value in sections.items()
        }
        if not cleaned.get("full_text"):
            requested = (cleaned.get("qa") or {}).get("requested_sections") or list(cleaned["sections"].keys())
            cleaned["full_text"] = "\n\n".join(
                cleaned["sections"].get(key, "") for key in requested if cleaned["sections"].get(key)
            ).strip()
    qa = dict(cleaned.get("qa") or {})
    qa["client_text_cleaned"] = True
    qa["client_text_cleaning_rule"] = "Removed Markdown markers (#, ##, **, bullets/code fences) from client-facing full_text and sections."
    cleaned["qa"] = qa
    return cleaned


def has_client_markdown_traces(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.search(r"(^\s{0,3}#{1,6}\s+|\*\*|```)", text, flags=re.MULTILINE))
