from __future__ import annotations

from collections import Counter
import ast
import re
import warnings

_RUST_UNICODE_ESCAPE_RE = re.compile(r"\\u\{([0-9A-Fa-f_]{1,6})\}")
_ZERO_PRECISION_SUFFIX_PLACEHOLDER = "{:.0}"
_ZERO_PRECISION_SUFFIX_SOURCES = {
    "Resolve Merge Conflict{} with Agent": frozenset({0}),
    "Show {} warning{}": frozenset({1}),
    "{} Comment{}": frozenset({1}),
}


def rust_format_placeholders(text: str) -> list[str]:
    placeholders: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        unicode_escape = _RUST_UNICODE_ESCAPE_RE.match(text, index)
        if unicode_escape is not None and _valid_rust_unicode_escape(unicode_escape.group(1)):
            index = unicode_escape.end()
            continue
        if char == "{" and index + 1 < len(text) and text[index + 1] == "{":
            index += 2
            continue
        if char == "}" and index + 1 < len(text) and text[index + 1] == "}":
            index += 2
            continue
        if char == "{":
            end = text.find("}", index + 1)
            if end == -1:
                index += 1
                continue
            placeholders.append(text[index : end + 1])
            index = end + 1
            continue
        index += 1
    return placeholders


def rust_format_placeholders_compatible(source: str, translation: str) -> bool:
    source_implicit, source_explicit = _rust_format_placeholder_profile(source)
    translation_implicit, translation_explicit = _rust_format_placeholder_profile(translation)
    return (
        _implicit_placeholders_compatible(source, source_implicit, translation_implicit)
        and source_explicit == translation_explicit
    )


def _implicit_placeholders_compatible(
    source: str,
    source_placeholders: list[str],
    translation_placeholders: list[str],
) -> bool:
    if source_placeholders == translation_placeholders:
        return True
    if len(source_placeholders) != len(translation_placeholders):
        return False

    zero_precision_indices = _ZERO_PRECISION_SUFFIX_SOURCES.get(source, frozenset())
    for index, (source_placeholder, translation_placeholder) in enumerate(
        zip(source_placeholders, translation_placeholders, strict=True)
    ):
        if source_placeholder == translation_placeholder:
            continue
        if (
            index in zero_precision_indices
            and source_placeholder == "{}"
            and translation_placeholder == _ZERO_PRECISION_SUFFIX_PLACEHOLDER
        ):
            continue
        return False
    return True


def _rust_format_placeholder_profile(text: str) -> tuple[list[str], Counter[str]]:
    implicit: list[str] = []
    explicit: Counter[str] = Counter()
    for placeholder in rust_format_placeholders(text):
        if _is_implicit_rust_format_placeholder(placeholder):
            implicit.append(placeholder)
        else:
            explicit[placeholder] += 1
    return implicit, explicit


def _is_implicit_rust_format_placeholder(placeholder: str) -> bool:
    inner = placeholder[1:-1]
    return inner == "" or inner.startswith(":")


def parse_rust_string_literal(literal: str) -> str:
    if literal.startswith('"') and literal.endswith('"'):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                return ast.literal_eval(literal)
        except (SyntaxError, ValueError):
            return literal[1:-1]
    return literal


def rust_string_literal(value: str) -> str:
    escaped: list[str] = ['"']
    index = 0
    while index < len(value):
        unicode_escape = _RUST_UNICODE_ESCAPE_RE.match(value, index)
        if unicode_escape is not None and _valid_rust_unicode_escape(unicode_escape.group(1)):
            escaped.append(unicode_escape.group(0))
            index = unicode_escape.end()
            continue

        char = value[index]
        if char == "\\":
            escaped.append("\\\\")
        elif char == '"':
            escaped.append('\\"')
        elif char == "\n":
            escaped.append("\\n")
        elif char == "\r":
            escaped.append("\\r")
        elif char == "\t":
            escaped.append("\\t")
        else:
            escaped.append(char)
        index += 1
    escaped.append('"')
    return "".join(escaped)


def _valid_rust_unicode_escape(digits: str) -> bool:
    try:
        codepoint = int(digits.replace("_", ""), 16)
    except ValueError:
        return False
    return codepoint <= 0x10FFFF and not 0xD800 <= codepoint <= 0xDFFF
