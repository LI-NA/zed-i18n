from __future__ import annotations

from collections import Counter
import re


_FILE_EXTENSIONS = (
    "json",
    "jsonc",
    "toml",
    "yaml",
    "yml",
    "rs",
    "md",
    "py",
    "js",
    "ts",
    "tsx",
    "jsx",
    "lock",
    "txt",
    "sh",
    "ps1",
    "exe",
    "dll",
    "wasm",
    "png",
    "svg",
    "ico",
    "zip",
)
_CODE_SPAN_RE = re.compile(r"`[^`\n]+`")
_CODE_SPAN_MIXED_CASE_RE = re.compile(r"[a-z][A-Z]")
_URL_RE = re.compile(r"https?://[^\s`<>)\]}\"']+")
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"(?=$|[^A-Za-z0-9_%+-])"
)
_ESCAPE_RE = re.compile(r"\\[ntr\\]")
# Dotted settings such as `session.restore_unsaved_buffers` must survive translation.
_SETTING_KEY_RE = re.compile(
    r"(?<![@/:A-Za-z0-9_.-])"
    r"[a-z][a-z0-9_]{1,}(?:\.[a-z0-9_]{2,})+"
    r"(?=$|[^A-Za-z0-9_.-])"
)
# Snake-case identifiers often name commands, options, or protocol fields.
_SNAKE_CASE_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:[a-z][a-z0-9]*_+[a-z0-9_]*[a-z0-9])"
    r"(?![A-Za-z0-9_])"
)
# Globs such as `crates/**/*.toml` are executable patterns, not prose.
_GLOB_RE = re.compile(
    r"(?<![A-Za-z0-9_.{}*?\[\]/-])"
    r"(?=[A-Za-z0-9_.{}*?\[\]/-]*\*)"
    r"[A-Za-z0-9_.{}?\[\]-]+(?:/[A-Za-z0-9_.{}*?\[\]-]+)+"
    r"|(?<![A-Za-z0-9_.{}*?\[\]/-])\*\.[A-Za-z0-9_-]+"
)
# Preserve shell-style, Unix, Windows, and hidden-directory paths.
_PATH_RE = re.compile(
    r"(?<!\S)"
    r"(?:~[/\\]|\.{1,2}[/\\]|\.[A-Za-z0-9_-]+[/\\]|[A-Za-z]:[/\\]|"
    r"/(?:etc|var|usr|tmp|home|Users|opt|bin|sbin|dev|mnt|Volumes|Applications)\b)"
    r"[A-Za-z0-9_./\\~:-]+"
)
# File names with known extensions should remain literal in translations.
_FILE_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])[A-Za-z0-9_.-]+\."
    rf"(?:{'|'.join(_FILE_EXTENSIONS)})"
    r"(?=$|\.{2,}|[^A-Za-z0-9_.-])"
)


def protected_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    tokens.extend(_protected_code_spans(text))
    tokens.extend(_normal_url(match.group(0)) for match in _URL_RE.finditer(text))
    tokens.extend(_normal_url(match.group(0)) for match in _EMAIL_RE.finditer(text))
    tokens.extend(_ESCAPE_RE.findall(text))
    tokens.extend(
        token for token in _SETTING_KEY_RE.findall(text) if not _is_file_token(token)
    )
    tokens.extend(_SNAKE_CASE_RE.findall(text))
    tokens.extend(_normal_protected_literal(token) for token in _GLOB_RE.findall(text))
    tokens.extend(
        _normal_protected_literal(token) for token in _PATH_RE.findall(text)
    )
    tokens.extend(_FILE_RE.findall(text))
    tokens.extend(_control_tokens(text))
    return tokens


def protected_tokens_match(source: str, translation: str) -> bool:
    return Counter(protected_tokens(source)) == Counter(protected_tokens(translation))


def _normal_url(url: str) -> str:
    return url.rstrip(".,;:!?")


def _normal_protected_literal(token: str) -> str:
    return token.rstrip(".,;:!?")


def _protected_code_spans(text: str) -> list[str]:
    spans: list[str] = []
    for match in _CODE_SPAN_RE.finditer(text):
        token = match.group(0)
        inner = token[1:-1].strip()
        if not _is_protected_code_span_content(inner):
            continue
        spans.append(token)
    return spans


def _is_protected_code_span_content(inner: str) -> bool:
    lower = inner.lower()
    if lower in {"a", "an", "and", "or", "the"}:
        return False
    if lower in {"true", "false", "null", "none", "default", "some", "ok", "err", "anyof"}:
        return True
    if any(char.isdigit() for char in inner):
        return True
    if _CODE_SPAN_MIXED_CASE_RE.search(inner):
        return True
    return any(char in inner for char in "/\\.:_-${}[]()#<>=*\"'")


def _is_file_token(token: str) -> bool:
    return token.lower().rsplit(".", 1)[-1] in _FILE_EXTENSIONS


def _control_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    tokens.extend("<LF>" for _ in range(text.count("\n")))
    tokens.extend("<TAB>" for _ in range(text.count("\t")))
    tokens.extend("<CR>" for _ in range(text.count("\r")))
    return tokens
