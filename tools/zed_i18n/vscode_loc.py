from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Iterable


LANGUAGE_PACK_ALIASES = {
    "cs-cz": "cs",
    "de-de": "de",
    "es-es": "es",
    "fr-fr": "fr",
    "it-it": "it",
    "ja-jp": "ja",
    "ko-kr": "ko",
    "pl-pl": "pl",
    "pt-br": "pt-BR",
    "ru-ru": "ru",
    "tr-tr": "tr",
    "zh-cn": "zh-hans",
    "zh-hans": "zh-hans",
    "zh-tw": "zh-hant",
    "zh-hant": "zh-hant",
}
PSEUDO_LOCALIZATION_LANGUAGE_IDS = {"qps-ploc"}

_CAMEL_CASE_RE = re.compile(r"^[a-z]+(?:[A-Z][a-z0-9]+)+$")
_SOURCE_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 &'’(),:;!?+\-/]*$")
_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class VscodeTranslationEntry:
    source: str
    translation: str
    language: str
    extension_id: str
    resource: str
    key: str


class VscodeTranslationIndex:
    def __init__(self, entries: Iterable[VscodeTranslationEntry]) -> None:
        self.entries = list(entries)
        self.by_normalized_source: dict[str, list[int]] = {}
        self.by_token: dict[str, set[int]] = {}
        for index, entry in enumerate(self.entries):
            normalized = _normalize_source(entry.source)
            if not normalized:
                continue
            self.by_normalized_source.setdefault(normalized, []).append(index)
            for token in set(normalized.split()):
                self.by_token.setdefault(token, set()).add(index)

    def find_references(
        self,
        source: str,
        limit: int = 3,
        min_score: float = 0.72,
    ) -> list[dict[str, object]]:
        if limit <= 0:
            return []

        normalized_source = _normalize_source(source)
        if not normalized_source:
            return []

        exact_indices = self.by_normalized_source.get(normalized_source, [])
        if exact_indices:
            return self._references_from_scored_indices(
                [(1.0, index) for index in exact_indices],
                source,
                limit,
            )

        tokens = set(normalized_source.split())
        if len(tokens) < 2:
            return []

        token_sets = sorted(
            (
                self.by_token[token]
                for token in tokens
                if token in self.by_token
            ),
            key=len,
        )
        if not token_sets:
            return []

        candidate_indices = set(token_sets[0])
        for token_set in token_sets[1:]:
            intersection = candidate_indices & token_set
            if intersection:
                candidate_indices = intersection
            if len(candidate_indices) <= 500:
                break
        if len(candidate_indices) > 1000:
            candidate_indices = set(
                sorted(
                    candidate_indices,
                    key=lambda index: abs(len(self.entries[index].source) - len(source)),
                )[:1000]
            )

        scored: list[tuple[float, int]] = []
        for index in candidate_indices:
            entry = self.entries[index]
            entry_tokens = set(_normalize_source(entry.source).split())
            if len(tokens & entry_tokens) < max(1, min(2, len(tokens))):
                continue
            score = _similarity(source, entry.source)
            if score >= min_score:
                scored.append((score, index))

        return self._references_from_scored_indices(scored, source, limit)

    def _references_from_scored_indices(
        self,
        scored: list[tuple[float, int]],
        source: str,
        limit: int,
    ) -> list[dict[str, object]]:
        scored.sort(
            key=lambda item: (
                -item[0],
                abs(len(self.entries[item[1]].source) - len(source)),
                _is_vscode_menu_item_key(self.entries[item[1]].key),
                self.entries[item[1]].source.lower(),
                self.entries[item[1]].resource,
            )
        )

        references: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for score, index in scored:
            entry = self.entries[index]
            dedupe_key = (_normalize_source(entry.source), entry.translation)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            references.append(
                {
                    "source": entry.source,
                    "translation": entry.translation,
                    "score": round(score, 3),
                    "extension": entry.extension_id,
                    "resource": entry.resource,
                    "key": entry.key,
                }
            )
            if len(references) >= limit:
                break
        return references


def is_vscode_pseudo_language(language: str) -> bool:
    return language.strip().lower() in PSEUDO_LOCALIZATION_LANGUAGE_IDS


def load_vscode_translation_memory(
    vscode_loc_root: Path,
    language: str,
    vscode_source_root: Path | None = None,
) -> list[VscodeTranslationEntry]:
    if is_vscode_pseudo_language(language):
        return []
    pack_root = _find_language_pack(vscode_loc_root, language)
    if pack_root is None:
        return []
    source_messages = (
        load_vscode_source_messages(vscode_source_root)
        if vscode_source_root is not None and vscode_source_root.exists()
        else {}
    )

    package = _read_json(pack_root / "package.json")
    localizations = package.get("contributes", {}).get("localizations", [])
    if not localizations:
        return []

    localization = localizations[0]
    language_id = str(localization.get("languageId", language))
    entries: list[VscodeTranslationEntry] = []
    seen: set[tuple[str, str, str, str]] = set()

    for translation_ref in localization.get("translations", []):
        if not isinstance(translation_ref, dict):
            continue
        extension_id = str(translation_ref.get("id", ""))
        relative_path = translation_ref.get("path")
        if not isinstance(relative_path, str):
            continue
        translation_path = (pack_root / relative_path).resolve()
        if not translation_path.exists():
            continue
        payload = _read_json(translation_path)
        contents = payload.get("contents", {})
        if not isinstance(contents, dict):
            continue
        for resource, key, value in _iter_translation_values(contents):
            if not isinstance(value, str):
                continue
            source = _clean_vscode_text(source_messages.get((extension_id, resource, key), key))
            if source == key and not _looks_like_source_key(key):
                continue
            translation = _clean_vscode_text(value)
            if not source or not translation:
                continue
            dedupe_key = (key, value, extension_id, resource)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            entries.append(
                VscodeTranslationEntry(
                    source=source,
                    translation=translation,
                    language=language_id,
                    extension_id=extension_id,
                    resource=resource,
                    key=key,
                )
            )
    return entries


def find_vscode_references(
    source: str,
    memory: Iterable[VscodeTranslationEntry] | VscodeTranslationIndex,
    limit: int = 3,
    min_score: float = 0.72,
) -> list[dict[str, object]]:
    index = memory if isinstance(memory, VscodeTranslationIndex) else VscodeTranslationIndex(memory)
    return index.find_references(source, limit, min_score)


@lru_cache(maxsize=4)
def load_vscode_source_messages(vscode_source_root: Path) -> dict[tuple[str, str, str], str]:
    messages: dict[tuple[str, str, str], str] = {}
    messages.update(_load_extension_package_messages(vscode_source_root))
    messages.update(_load_core_localize_messages(vscode_source_root))
    return messages


def _is_vscode_menu_item_key(key: str) -> bool:
    # VS Code `mi*` keys are menu-item aliases; rank them after source/package keys.
    return key.lower().startswith("mi")


def _find_language_pack(vscode_loc_root: Path, language: str) -> Path | None:
    i18n_root = vscode_loc_root / "i18n"
    if not i18n_root.exists():
        return None

    wanted = language.lower()
    aliases = {wanted}
    if wanted in LANGUAGE_PACK_ALIASES:
        aliases.add(LANGUAGE_PACK_ALIASES[wanted].lower())
    if "-" in wanted:
        aliases.add(wanted.split("-", 1)[0])

    for pack_root in sorted(i18n_root.glob("vscode-language-pack-*")):
        suffix = pack_root.name.removeprefix("vscode-language-pack-").lower()
        language_id = (_language_id_from_pack(pack_root) or "").lower()
        if suffix in aliases or language_id in aliases:
            return pack_root
    return None


def _load_extension_package_messages(
    vscode_source_root: Path,
) -> dict[tuple[str, str, str], str]:
    messages: dict[tuple[str, str, str], str] = {}
    extensions_root = vscode_source_root / "extensions"
    if not extensions_root.exists():
        return messages

    for package_nls_path in sorted(extensions_root.glob("*/package.nls.json")):
        extension_root = package_nls_path.parent
        extension_ids = _extension_ids(extension_root)
        package_messages = _read_json(package_nls_path)
        for key, value in package_messages.items():
            message = _nls_message_text(value)
            if message is None:
                continue
            for extension_id in extension_ids:
                messages[(extension_id, "package", key)] = message
    return messages


def _load_core_localize_messages(
    vscode_source_root: Path,
) -> dict[tuple[str, str, str], str]:
    messages: dict[tuple[str, str, str], str] = {}
    src_root = vscode_source_root / "src"
    if not src_root.exists():
        return messages

    for source_path in sorted(src_root.rglob("*.ts")):
        resource = source_path.relative_to(src_root).with_suffix("").as_posix()
        text = source_path.read_text(encoding="utf-8")
        for key, message in _iter_localize_calls(text):
            messages[("vscode", resource, key)] = message
    return messages


def _extension_ids(extension_root: Path) -> set[str]:
    ids = {f"vscode.{extension_root.name}"}
    package_path = extension_root / "package.json"
    if not package_path.exists():
        return ids
    package = _read_json(package_path)
    publisher = package.get("publisher")
    name = package.get("name")
    if isinstance(publisher, str) and isinstance(name, str):
        ids.add(f"{publisher}.{name}")
    return ids


def _nls_message_text(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        message = value.get("message")
        if isinstance(message, str):
            return message
    return None


def _iter_localize_calls(text: str) -> Iterable[tuple[str, str]]:
    string_pattern = r"(?P<quote>['\"])(?P<value>(?:\\.|(?! (?P=quote)).)*?)(?P=quote)"
    simple_pattern = re.compile(
        r"localize(?:2)?\(\s*"
        + string_pattern.replace("value", "key").replace("quote", "key_quote")
        + r"\s*,\s*"
        + string_pattern.replace("value", "message").replace("quote", "message_quote"),
        re.DOTALL | re.VERBOSE,
    )
    object_pattern = re.compile(
        r"localize(?:2)?\(\s*\{\s*key\s*:\s*"
        + string_pattern.replace("value", "key").replace("quote", "key_quote")
        + r".*?\}\s*,\s*"
        + string_pattern.replace("value", "message").replace("quote", "message_quote"),
        re.DOTALL | re.VERBOSE,
    )
    for pattern in (simple_pattern, object_pattern):
        for match in pattern.finditer(text):
            key = _decode_js_string(match.group("key"))
            message = _decode_js_string(match.group("message"))
            if key and message:
                yield key, message


def _language_id_from_pack(pack_root: Path) -> str:
    package_path = pack_root / "package.json"
    if not package_path.exists():
        return ""
    package = _read_json(package_path)
    localizations = package.get("contributes", {}).get("localizations", [])
    if not localizations:
        return ""
    language_id = localizations[0].get("languageId", "")
    return str(language_id)


def _iter_translation_values(contents: dict[str, Any]) -> Iterable[tuple[str, str, object]]:
    for resource, messages in contents.items():
        if not isinstance(resource, str) or not isinstance(messages, dict):
            continue
        for key, value in messages.items():
            if isinstance(key, str):
                yield resource, key, value


def _looks_like_source_key(key: str) -> bool:
    stripped = key.strip()
    if not stripped or "." in stripped or "_" in stripped or "/" in stripped or "\\" in stripped:
        return False
    if _CAMEL_CASE_RE.match(stripped):
        return False
    return bool(_SOURCE_KEY_RE.match(stripped)) and any(char.isalpha() for char in stripped)


def _similarity(left: str, right: str) -> float:
    normalized_left = _normalize_source(left)
    normalized_right = _normalize_source(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _normalize_source(value: str) -> str:
    return " ".join(_WORD_RE.findall(value.lower().replace("&&", "")))


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _decode_js_string(value: str) -> str:
    return (
        value.replace(r"\\", "\\")
        .replace(r"\'", "'")
        .replace(r"\"", '"')
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
    )


def _clean_vscode_text(value: str) -> str:
    return re.sub(r"\(&&.\)", "", value).replace("&&", "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
