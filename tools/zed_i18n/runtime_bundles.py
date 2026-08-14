from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import tomllib
from typing import Mapping

from .config import ProjectConfig
from .apply_universal import (
    _IMPLICIT_FORMAT_MACROS,
    _rust_macro_call_spans,
    _token_tree_arguments,
)
from .rust_ast import make_rust_parser, node_text, walk_nodes
from .rust_strings import parse_rust_string_literal, rust_format_placeholders_compatible


BUNDLE_SCHEMA_VERSION = 1
RAW_PAYLOAD_BUDGET = 12 * 1024 * 1024
_METADATA_KINDS = {
    "rust_doc_comment",
    "action_description",
    "settings_enum_variant_label",
    "settings_enum_discriminant_label",
}
_RUST_UNICODE_ESCAPE_RE = re.compile(r"\\u\{([0-9A-Fa-f_]{1,6})\}")


FormatSegment = dict[str, str]


@dataclass(frozen=True)
class LocaleMetadata:
    id: str
    english_name: str
    native_name: str
    aliases: tuple[str, ...]
    direction: str
    enabled: bool


@dataclass(frozen=True)
class LocaleConfig:
    source_locale: str
    locales: tuple[LocaleMetadata, ...]


@dataclass(frozen=True)
class RuntimeBundleReport:
    catalog_sha256: str
    locale_count: int
    message_count: int
    format_count: int
    joined_message_count: int
    raw_payload_bytes: int
    output_files: tuple[str, ...]


def load_locale_config(path: Path) -> LocaleConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    source_locale = data.get("source_locale")
    raw_locales = data.get("locale")
    if not isinstance(source_locale, str) or not source_locale:
        raise ValueError("locale config requires source_locale")
    if not isinstance(raw_locales, list) or not raw_locales:
        raise ValueError("locale config requires at least one locale")

    locales: list[LocaleMetadata] = []
    ids: set[str] = set()
    names: dict[str, str] = {}
    for raw in raw_locales:
        if not isinstance(raw, dict):
            raise ValueError("locale entries must be tables")
        locale_id = _required_string(raw, "id")
        if locale_id in ids:
            raise ValueError(f"duplicate locale id: {locale_id}")
        ids.add(locale_id)
        aliases_value = raw.get("aliases", [])
        if not isinstance(aliases_value, list) or not all(
            isinstance(alias, str) and alias for alias in aliases_value
        ):
            raise ValueError(f"locale aliases must be non-empty strings: {locale_id}")
        direction = _required_string(raw, "direction")
        if direction not in {"ltr", "rtl"}:
            raise ValueError(f"unsupported locale direction for {locale_id}: {direction}")
        enabled = raw.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError(f"locale enabled must be boolean: {locale_id}")
        locale = LocaleMetadata(
            id=locale_id,
            english_name=_required_string(raw, "english_name"),
            native_name=_required_string(raw, "native_name"),
            aliases=tuple(aliases_value),
            direction=direction,
            enabled=enabled,
        )
        locales.append(locale)
        for candidate in (locale.id, *locale.aliases):
            normalized = candidate.replace("_", "-").casefold()
            owner = names.get(normalized)
            if owner is not None and owner != locale.id:
                if candidate in locale.aliases:
                    raise ValueError(f"duplicate locale alias {candidate!r}: {owner}, {locale.id}")
                raise ValueError(f"locale id conflicts with alias {candidate!r}: {owner}, {locale.id}")
            names[normalized] = locale.id

    if source_locale not in ids:
        raise ValueError(f"source locale is not declared: {source_locale}")
    if not next(locale for locale in locales if locale.id == source_locale).enabled:
        raise ValueError("source locale must be enabled")
    return LocaleConfig(source_locale=source_locale, locales=tuple(locales))


def compile_format_plan(source: str) -> tuple[FormatSegment, ...]:
    source = _decode_rust_unicode_escapes(source)
    segments: list[FormatSegment] = []
    text: list[str] = []
    implicit_index = 0
    index = 0

    def flush_text() -> None:
        if text:
            segments.append({"text": "".join(text)})
            text.clear()

    while index < len(source):
        char = source[index]
        if char == "{" and index + 1 < len(source) and source[index + 1] == "{":
            text.append("{")
            index += 2
            continue
        if char == "}" and index + 1 < len(source) and source[index + 1] == "}":
            text.append("}")
            index += 2
            continue
        if char == "}":
            raise ValueError(f"unmatched closing brace in format string: {source!r}")
        if char != "{":
            text.append(char)
            index += 1
            continue

        end = source.find("}", index + 1)
        if end < 0 or "{" in source[index + 1 : end]:
            raise ValueError(f"invalid format placeholder in {source!r}")
        inner = source[index + 1 : end]
        argument, separator, format_spec = inner.partition(":")
        if separator and ("$" in format_spec or ".*" in format_spec):
            raise ValueError(f"dynamic width or precision is unsupported: {source!r}")
        if argument == "":
            argument = str(implicit_index)
            implicit_index += 1
        elif not argument.isdecimal() and not _is_rust_identifier(argument):
            raise ValueError(f"unsupported format argument {argument!r} in {source!r}")
        flush_text()
        segments.append({"arg": argument})
        index = end + 1

    flush_text()
    return tuple(segments)


def generate_runtime_bundles(
    root: Path,
    zed_root: Path,
    project: ProjectConfig,
) -> RuntimeBundleReport:
    locale_config = load_locale_config(root / "config" / "locales.toml")
    catalog = _read_string_map(root / "catalog" / "en-US.json", "catalog")
    manifest = _read_json_object(root / "manifest" / "ui-strings.json", "manifest")
    catalog_bytes = _canonical_json_bytes(catalog)
    catalog_sha256 = hashlib.sha256(catalog_bytes).hexdigest()

    accepted = {
        source
        for source, entry in manifest.items()
        if isinstance(source, str)
        and isinstance(entry, dict)
        and entry.get("status") == "accepted"
    }
    missing_catalog = sorted(accepted - catalog.keys())
    if missing_catalog:
        raise ValueError(f"accepted manifest keys missing from catalog: {missing_catalog[:3]!r}")

    format_sources, format_components, static_catalog_sources = _runtime_format_sources(
        zed_root, manifest, accepted
    )
    catalog_format_sources = {
        component
        for components in format_components.values()
        for component in components
        if component in accepted
    }
    runtime_source_aliases = _runtime_source_aliases(zed_root, manifest, accepted)
    indoc_sources = _indoc_sources(zed_root, manifest, accepted)
    source_formats = {
        source: list(compile_format_plan(source)) for source in sorted(format_sources)
    }
    joined_groups = _joined_metadata_groups(zed_root, manifest, accepted)

    enabled_locales = [locale for locale in locale_config.locales if locale.enabled]
    output_dir = zed_root / "assets" / "locales"
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_names = {"index.json"}
    output_files: list[Path] = []
    message_count = 0
    format_count = 0
    joined_message_count = 0

    locale_index: list[dict[str, object]] = []
    for locale in enabled_locales:
        bundle_name = None if locale.id == locale_config.source_locale else f"{locale.id}.json"
        locale_index.append(
            {
                "id": locale.id,
                "english_name": locale.english_name,
                "native_name": locale.native_name,
                "aliases": list(locale.aliases),
                "direction": locale.direction,
                "bundle": bundle_name,
            }
        )
        if bundle_name is None:
            continue
        translation_path = root / "translations" / bundle_name
        if not translation_path.exists():
            raise ValueError(f"enabled locale has no translation file: {locale.id}")
        translations = _read_string_map(translation_path, f"translation {locale.id}")
        message_sources = (accepted - catalog_format_sources) | (
            catalog_format_sources & static_catalog_sources
        )
        messages = {
            _decode_rust_unicode_escapes(source): _decode_rust_unicode_escapes(
                translations[source]
            )
            for source in sorted(message_sources)
            if source in translations
        }
        for runtime_source, catalog_source in runtime_source_aliases.items():
            translation = translations.get(catalog_source)
            if catalog_source not in catalog_format_sources and translation is not None:
                messages[_decode_rust_unicode_escapes(runtime_source)] = (
                    _decode_rust_unicode_escapes(translation)
                )
        for source in indoc_sources:
            translation = translations.get(source)
            if translation is not None:
                messages[_normalize_indoc(source)] = _normalize_indoc(translation)
        formats: dict[str, list[FormatSegment]] = {}
        for source in sorted(format_sources):
            components = format_components[source]
            translation = translations.get(components[0]) if len(components) == 1 else None
            if translation is None and len(components) > 1 and all(
                component in translations for component in components
            ):
                translation = "".join(translations[component] for component in components)
            if translation is None:
                continue
            catalog_source = (
                components[0] if len(components) == 1 else "".join(components)
            )
            if not _runtime_format_translation_compatible(
                source, catalog_source, translation
            ):
                raise ValueError(f"placeholder mismatch for {locale.id}: {source!r}")
            formats[_decode_rust_unicode_escapes(source)] = list(
                compile_format_plan(translation)
            )
        for group in joined_groups:
            keys = [key for _, key in group if key]
            if not all(key in translations for key in keys):
                continue
            translated_lines: list[str] = []
            for consumer_value, key in group:
                if not key:
                    translated_lines.append("")
                    continue
                prefix = consumer_value[: len(consumer_value) - len(consumer_value.lstrip())]
                suffix = consumer_value[len(consumer_value.rstrip()) :]
                translated_lines.append(prefix + translations[key] + suffix)
            joined_source = _decode_rust_unicode_escapes(
                "\n".join(value for value, _ in group)
            )
            joined_translation = _decode_rust_unicode_escapes("\n".join(translated_lines))
            if joined_source and joined_source not in messages:
                messages[joined_source] = joined_translation
                joined_message_count += 1

        bundle = {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "locale": locale.id,
            "catalog_sha256": catalog_sha256,
            "messages": messages,
            "formats": formats,
        }
        bundle_path = output_dir / bundle_name
        _write_canonical_json(bundle_path, bundle)
        expected_names.add(bundle_name)
        output_files.append(bundle_path)
        message_count += len(messages)
        format_count += len(formats)

    index = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "source_locale": locale_config.source_locale,
        "zed_version": project.zed_version,
        "zed_commit": project.zed_commit,
        "catalog_sha256": catalog_sha256,
        "locales": locale_index,
        "source_formats": source_formats,
    }
    index_path = output_dir / "index.json"
    _write_canonical_json(index_path, index)
    output_files.insert(0, index_path)

    unexpected = [path for path in output_dir.glob("*.json") if path.name not in expected_names]
    if unexpected:
        names = ", ".join(path.name for path in sorted(unexpected))
        raise ValueError(f"unexpected locale bundles in output directory: {names}")

    raw_payload_bytes = sum(path.stat().st_size for path in output_files)
    if raw_payload_bytes > RAW_PAYLOAD_BUDGET:
        raise ValueError(
            f"runtime locale payload exceeds {RAW_PAYLOAD_BUDGET} bytes: {raw_payload_bytes}"
        )
    report = RuntimeBundleReport(
        catalog_sha256=catalog_sha256,
        locale_count=len(enabled_locales),
        message_count=message_count,
        format_count=format_count,
        joined_message_count=joined_message_count,
        raw_payload_bytes=raw_payload_bytes,
        output_files=tuple(path.relative_to(zed_root).as_posix() for path in output_files),
    )
    report_dir = root / "reports" / "runtime-feasibility"
    _write_canonical_json(report_dir / "bundle-metrics.json", asdict(report))
    _write_canonical_json(
        report_dir / "format-inventory.json",
        {
            "format_key_count": len(format_sources),
            "format_keys": sorted(format_sources),
            "joined_metadata_group_count": len(joined_groups),
        },
    )
    return report


def _runtime_format_sources(
    zed_root: Path,
    manifest: Mapping[str, object],
    accepted: set[str],
) -> tuple[set[str], dict[str, tuple[str, ...]], set[str]]:
    occurrences_by_file: dict[str, list[tuple[str, dict[str, object]]]] = defaultdict(list)
    for source in accepted:
        entry = manifest[source]
        if not isinstance(entry, dict):
            continue
        for occurrence in entry.get("occurrences", []):
            if not isinstance(occurrence, dict):
                continue
            relative = occurrence.get("file")
            if isinstance(relative, str) and not relative.startswith("runtime-overlay/"):
                occurrences_by_file[relative].append((source, occurrence))

    format_sources: set[str] = set()
    format_components: dict[str, tuple[str, ...]] = {}
    static_catalog_sources: set[str] = set()

    def add_format(runtime_source: str, catalog_components: tuple[str, ...]) -> None:
        previous = format_components.get(runtime_source)
        if previous is not None and previous != catalog_components:
            raise ValueError(
                f"runtime format source maps to multiple catalog keys: {runtime_source!r}"
            )
        format_sources.add(runtime_source)
        format_components[runtime_source] = catalog_components

    for source in accepted:
        entry = manifest[source]
        if not isinstance(entry, dict):
            continue
        for occurrence in entry.get("occurrences", []):
            if not isinstance(occurrence, dict) or not str(
                occurrence.get("file", "")
            ).startswith("runtime-overlay/"):
                continue
            if occurrence.get("call") == "localization::format_message":
                add_format(source, (source,))
            else:
                static_catalog_sources.add(source)

    parser = make_rust_parser()
    for relative, occurrences in occurrences_by_file.items():
        path = zed_root / relative
        if not path.exists():
            raise ValueError(f"manifest source file does not exist: {relative}")
        source_bytes = path.read_text(encoding="utf-8").encode("utf-8")
        tree = parser.parse(source_bytes)
        nodes = {(node.start_byte, node.end_byte): node for node in walk_nodes(tree.root_node)}
        for source, occurrence in occurrences:
            if occurrence.get("kind") in _METADATA_KINDS:
                static_catalog_sources.add(source)
                continue
            start = occurrence.get("start_byte")
            end = occurrence.get("end_byte")
            if not isinstance(start, int) or not isinstance(end, int):
                raise ValueError(f"occurrence is missing byte span: {relative}:{occurrence.get('line')}")
            node = nodes.get((start, end))
            if node is None:
                raise ValueError(f"occurrence byte span is stale: {relative}:{occurrence.get('line')}")
            is_runtime_format = False
            parent = node.parent
            while parent is not None:
                if parent.type == "macro_invocation":
                    macro_name = node_text(source_bytes, parent).split("!", 1)[0].strip()
                    if macro_name in {"format", "format_args", "write"}:
                        components = _format_source_components(source_bytes, parent)
                        bounds = _format_source_bounds(source_bytes, parent)
                        if bounds is not None and bounds[0] <= node.start_byte and node.end_byte <= bounds[1]:
                            runtime_components = _runtime_format_source_components(
                                source_bytes, parent
                            )
                            format_source = _decode_rust_unicode_escapes(
                                "".join(runtime_components)
                            )
                            catalog_components = (source,) if len(components) == 1 else components
                            add_format(format_source, catalog_components)
                            is_runtime_format = True
                        break
                if parent.type == "attribute_item" and re.match(
                    r"#\s*\[\s*error\s*\(", node_text(source_bytes, parent).lstrip()
                ):
                    if any(
                        "arg" in segment for segment in compile_format_plan(source)
                    ):
                        add_format(source, (source,))
                        is_runtime_format = True
                    break
                if parent.end_byte - parent.start_byte > 100_000:
                    break
                parent = parent.parent
            if not is_runtime_format:
                static_catalog_sources.add(source)
        source_text = source_bytes.decode("utf-8")
        for call_start, call_end in _rust_macro_call_spans(source_text, "format"):
            call = source_text[call_start:call_end]
            fixture = f"fn __zed_i18n_fixture() {{ let _ = {call}; }}"
            fixture_bytes = fixture.encode("utf-8")
            fixture_tree = parser.parse(fixture_bytes)
            macro = next(
                (
                    candidate
                    for candidate in walk_nodes(fixture_tree.root_node)
                    if candidate.type == "macro_invocation"
                    and node_text(fixture_bytes, candidate).lstrip().startswith("format!")
                ),
                None,
            )
            if macro is None:
                continue
            try:
                components = _format_source_components(fixture_bytes, macro)
            except ValueError:
                continue
            if not any(component in accepted for component in components):
                continue
            runtime_components = _runtime_format_source_components(fixture_bytes, macro)
            format_source = _decode_rust_unicode_escapes("".join(runtime_components))
            catalog_components = (
                (format_source,)
                if len(components) == 1 and format_source in accepted
                else components
            )
            add_format(format_source, catalog_components)
        for macro_name, source_index in _IMPLICIT_FORMAT_MACROS:
            for call_start, call_end in _rust_macro_call_spans(source_text, macro_name):
                call = source_text[call_start:call_end]
                fixture = f"fn __zed_i18n_fixture() {{ let _ = {call}; }}"
                fixture_bytes = fixture.encode("utf-8")
                fixture_tree = parser.parse(fixture_bytes)
                macro = next(
                    (
                        candidate
                        for candidate in walk_nodes(fixture_tree.root_node)
                        if candidate.type == "macro_invocation"
                        and node_text(fixture_bytes, candidate).lstrip().startswith(
                            f"{macro_name}!"
                        )
                    ),
                    None,
                )
                if macro is None:
                    continue
                token_tree = next(
                    (
                        child
                        for child in macro.children
                        if child.type == "token_tree"
                    ),
                    None,
                )
                if token_tree is None:
                    continue
                arguments = _token_tree_arguments(fixture_bytes, token_tree)
                if source_index >= len(arguments):
                    continue
                literal = arguments[source_index].strip()
                if not literal.startswith('"') or not literal.endswith('"'):
                    continue
                normalized = re.sub(r"\\\r?\n[ \t]*", "", literal)
                format_source = _decode_rust_unicode_escapes(
                    parse_rust_string_literal(normalized)
                )
                if format_source in accepted and "{" in format_source:
                    add_format(format_source, (format_source,))
    return format_sources, format_components, static_catalog_sources


def _decode_rust_unicode_escapes(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        codepoint = int(match.group(1).replace("_", ""), 16)
        if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
            return match.group(0)
        return chr(codepoint)

    return _RUST_UNICODE_ESCAPE_RE.sub(replace, value)


def _runtime_format_translation_compatible(
    source: str,
    catalog_source: str,
    translation: str,
) -> bool:
    # Both sides must compile into runtime render plans, and the translation
    # must keep exactly its catalog key's placeholders (count, name, and
    # format spec), sharing the validator's rules so a new locale cannot
    # silently drop a placeholder from an embedded bundle.
    try:
        source_segments = compile_format_plan(source)
        translation_segments = compile_format_plan(translation)
    except ValueError:
        return False
    if not rust_format_placeholders_compatible(
        _decode_rust_unicode_escapes(catalog_source),
        _decode_rust_unicode_escapes(translation),
    ):
        return False
    if catalog_source == source:
        return True
    # Composite rules deliberately catalog a reshaped source (for example
    # "{} {}" cataloged as "{} project rules"), so additionally require that
    # the translated plan only renders arguments the macro actually provides.
    source_args = {
        segment["arg"] for segment in source_segments if "arg" in segment
    }
    translation_args = {
        segment["arg"] for segment in translation_segments if "arg" in segment
    }
    return translation_args <= source_args


def _normalize_indoc(value: str) -> str:
    return re.sub(r"\s+", " ", _decode_rust_unicode_escapes(value)).strip()


def _indoc_sources(
    zed_root: Path,
    manifest: Mapping[str, object],
    accepted: set[str],
) -> set[str]:
    sources: set[str] = set()
    parser = make_rust_parser()
    by_file: dict[str, list[tuple[str, dict[str, object]]]] = defaultdict(list)
    for source in accepted:
        entry = manifest.get(source)
        if not isinstance(entry, dict):
            continue
        for occurrence in entry.get("occurrences", []):
            if isinstance(occurrence, dict) and isinstance(occurrence.get("file"), str):
                by_file[occurrence["file"]].append((source, occurrence))
    for relative, occurrences in by_file.items():
        if relative.startswith("runtime-overlay/"):
            continue
        source_bytes = (zed_root / relative).read_text(encoding="utf-8").encode("utf-8")
        tree = parser.parse(source_bytes)
        nodes = {(node.start_byte, node.end_byte): node for node in walk_nodes(tree.root_node)}
        for source, occurrence in occurrences:
            start = occurrence.get("start_byte")
            end = occurrence.get("end_byte")
            node = nodes.get((start, end))
            parent = node.parent if node is not None else None
            while parent is not None:
                if parent.type == "macro_invocation":
                    name = node_text(source_bytes, parent).split("!", 1)[0].strip()
                    if name == "indoc":
                        raw = source_bytes[start:end].decode("utf-8")
                        runtime_value = _indoc_dedent(
                            parse_rust_string_literal(
                                re.sub(r"\\\r?\n[ \t]*", "", raw)
                            )
                        )
                        if runtime_value != _normalize_indoc(source):
                            raise ValueError(
                                "indoc! runtime value diverges from its whitespace-"
                                f"collapsed bundle key: {relative}:{occurrence.get('line')}"
                            )
                        sources.add(source)
                    break
                parent = parent.parent
    return sources


def _indoc_dedent(value: str) -> str:
    """Mirror the indoc/unindent dedent rules for the guard above.

    The first line is ignored when computing the common indentation, every
    following line loses that indentation, and a leading blank line is
    removed. Newlines are preserved, which is exactly what makes a diverging
    multi-line indoc! literal fail closed instead of silently missing at
    runtime lookup.
    """
    lines = value.split("\n")
    if len(lines) == 1:
        return value
    body = lines[1:]
    indents = [
        len(line) - len(line.lstrip(" \t")) for line in body if line.strip()
    ]
    indent = min(indents, default=0)
    dedented = [lines[0]] + [
        line[indent:] if line.strip() else "" for line in body
    ]
    if not dedented[0].strip():
        dedented = dedented[1:]
    return "\n".join(dedented)


def _runtime_source_aliases(
    zed_root: Path,
    manifest: Mapping[str, object],
    accepted: set[str],
) -> dict[str, str]:
    by_file: dict[str, list[tuple[str, dict[str, object]]]] = defaultdict(list)
    for source in accepted:
        entry = manifest[source]
        if not isinstance(entry, dict):
            continue
        for occurrence in entry.get("occurrences", []):
            if not isinstance(occurrence, dict):
                continue
            relative = occurrence.get("file")
            if (
                isinstance(relative, str)
                and not relative.startswith("runtime-overlay/")
                and occurrence.get("kind") not in _METADATA_KINDS
            ):
                by_file[relative].append((source, occurrence))

    aliases: dict[str, str] = {}
    for relative, occurrences in by_file.items():
        source_bytes = (zed_root / relative).read_text(encoding="utf-8").encode("utf-8")
        for catalog_source, occurrence in occurrences:
            start = occurrence.get("start_byte")
            end = occurrence.get("end_byte")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            raw = source_bytes[start:end].decode("utf-8")
            if "\\\n" not in raw:
                continue
            runtime_source = parse_rust_string_literal(
                re.sub(r"\\\r?\n[ \t]*", "", raw)
            )
            if runtime_source == catalog_source:
                continue
            previous = aliases.get(runtime_source)
            if previous is not None and previous != catalog_source:
                raise ValueError(
                    f"runtime source maps to multiple catalog keys: {runtime_source!r}"
                )
            aliases[runtime_source] = catalog_source
    return aliases


def _format_source_bounds(source_bytes: bytes, macro) -> tuple[int, int] | None:
    token_tree = next((child for child in macro.children if child.type == "token_tree"), None)
    if token_tree is None:
        return None
    macro_name = node_text(source_bytes, macro).split("!", 1)[0].strip()
    argument_index = 1 if macro_name == "write" else 0
    commas = [child.start_byte for child in token_tree.children if child.type == ","]
    if argument_index > len(commas):
        return None
    return (
        token_tree.start_byte + 1
        if argument_index == 0
        else commas[argument_index - 1] + 1,
        commas[argument_index]
        if len(commas) > argument_index
        else token_tree.end_byte - 1,
    )


def _format_source_components(source_bytes: bytes, macro) -> tuple[str, ...]:
    token_tree = next((child for child in macro.children if child.type == "token_tree"), None)
    bounds = _format_source_bounds(source_bytes, macro)
    if token_tree is None or bounds is None:
        raise ValueError("format macro has no token tree")
    literals = [
        node
        for node in walk_nodes(token_tree)
        if node.type == "string_literal"
        and bounds[0] <= node.start_byte
        and node.end_byte <= bounds[1]
    ]
    if not literals:
        raise ValueError("format source is not a string literal or concat of literals")
    return tuple(
        parse_rust_string_literal(node_text(source_bytes, literal)) for literal in literals
    )


def _runtime_format_source_components(source_bytes: bytes, macro) -> tuple[str, ...]:
    token_tree = next((child for child in macro.children if child.type == "token_tree"), None)
    bounds = _format_source_bounds(source_bytes, macro)
    if token_tree is None or bounds is None:
        raise ValueError("format macro has no token tree")
    literals = [
        node
        for node in walk_nodes(token_tree)
        if node.type == "string_literal"
        and bounds[0] <= node.start_byte
        and node.end_byte <= bounds[1]
    ]
    if not literals:
        raise ValueError("format source is not a string literal or concat of literals")
    return tuple(
        parse_rust_string_literal(
            re.sub(
                r"\\\r?\n[ \t]*",
                "",
                node_text(source_bytes, literal),
            )
        )
        for literal in literals
    )


def _joined_metadata_groups(
    zed_root: Path,
    manifest: Mapping[str, object],
    accepted: set[str],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    """Reconstruct doc blocks exactly as their Rust consumers join them.

    schemars_derive 1.0.4 keeps every `///` line after stripping at most one
    leading space and joins the lines with "\\n", keeping blank doc lines as
    empty strings, so paragraphs become "first\\n\\nsecond". gpui's
    `derive_action` trims every line instead and joins the same way. Each
    returned group is a tuple of (consumer_line, catalog_key) pairs where
    blank doc lines carry an empty consumer line and an empty catalog key.
    """
    by_file: dict[tuple[str, str], dict[int, str]] = defaultdict(dict)
    for source in sorted(accepted):
        entry = manifest[source]
        if not isinstance(entry, dict):
            continue
        for occurrence in entry.get("occurrences", []):
            if not isinstance(occurrence, dict):
                continue
            kind = occurrence.get("kind")
            relative = occurrence.get("file")
            line = occurrence.get("line")
            if kind in {"rust_doc_comment", "action_description"} and isinstance(
                relative, str
            ) and not relative.startswith("runtime-overlay/") and isinstance(line, int):
                by_file[(relative, str(kind))][line] = source

    groups: list[tuple[tuple[str, str], ...]] = []
    for (relative, kind), line_map in sorted(by_file.items()):
        path = zed_root / relative
        if not path.exists():
            raise ValueError(f"manifest source file does not exist: {relative}")
        lines = path.read_text(encoding="utf-8").splitlines()
        blocks: list[list[tuple[str, str]]] = []
        current: list[tuple[str, str]] = []
        previous_line: int | None = None
        for line_no in sorted(line_map):
            consumer_value = _doc_line_consumer_value(lines, line_no, kind)
            if consumer_value is None or consumer_value.strip() != line_map[line_no]:
                blocks.append(current)
                current = []
                previous_line = None
                continue
            if previous_line is not None and not all(
                _is_blank_doc_line(lines, gap_line)
                for gap_line in range(previous_line + 1, line_no)
            ):
                blocks.append(current)
                current = []
                previous_line = None
            if previous_line is not None:
                current.extend(("", "") for _ in range(previous_line + 1, line_no))
            current.append((consumer_value, line_map[line_no]))
            previous_line = line_no
        blocks.append(current)
        for block in blocks:
            if sum(1 for _, key in block if key) > 1:
                groups.append(tuple(block))
    return tuple(groups)


def _doc_line_consumer_value(lines: list[str], line_no: int, kind: str) -> str | None:
    if not 1 <= line_no <= len(lines):
        return None
    left = lines[line_no - 1].lstrip()
    if not left.startswith("///"):
        return None
    content = left[3:]
    if kind == "action_description":
        return content.strip()
    return content.removeprefix(" ")


def _is_blank_doc_line(lines: list[str], line_no: int) -> bool:
    if not 1 <= line_no <= len(lines):
        return False
    left = lines[line_no - 1].lstrip()
    return left.startswith("///") and not left[3:].strip()


def _required_string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"locale entry requires non-empty {key}")
    return value


def _is_rust_identifier(value: str) -> bool:
    return bool(value) and (value[0] == "_" or value[0].isalpha()) and all(
        char == "_" or char.isalnum() for char in value[1:]
    )


def _read_json_object(path: Path, description: str) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a JSON object")
    return value


def _read_string_map(path: Path, description: str) -> dict[str, str]:
    value = _read_json_object(path, description)
    if not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
        raise ValueError(f"{description} must map strings to strings")
    return value  # type: ignore[return-value]


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_canonical_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(value))
