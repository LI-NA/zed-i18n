from __future__ import annotations

from pathlib import Path
from typing import Iterable

from tree_sitter import Language, Parser
import tree_sitter_rust


def make_rust_parser() -> Parser:
    language = Language(tree_sitter_rust.language())
    return Parser(language)


def iter_rust_files(root: Path) -> Iterable[Path]:
    return sorted(root.glob("crates/**/*.rs"))


def walk_nodes(node):
    yield node
    for child in node.children:
        yield from walk_nodes(child)


def node_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8")
