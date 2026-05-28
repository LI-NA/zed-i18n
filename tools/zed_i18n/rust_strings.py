from __future__ import annotations

import ast
import re
import warnings

_RUST_UNICODE_ESCAPE_RE = re.compile(r"\\u\{([0-9A-Fa-f_]{1,6})\}")


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
