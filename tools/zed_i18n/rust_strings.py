from __future__ import annotations

import ast
import warnings


def rust_format_placeholders(text: str) -> list[str]:
    placeholders: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if text.startswith("\\u{", index):
            end = text.find("}", index + 3)
            if end != -1:
                index = end + 1
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
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'
