from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .extract import (
    extract_ui_strings_from_source,
    should_skip_path,
)
from .rust_ast import iter_rust_files, make_rust_parser, node_text, walk_nodes
from .rust_strings import parse_rust_string_literal


@dataclass(frozen=True)
class StringCandidate:
    source: str
    file: str
    line: int
    call: str
    matched_by_rule: bool
    start_byte: int
    end_byte: int

    def to_json(self) -> dict[str, object]:
        return asdict(self)


def audit_string_candidates_from_source(source: str, relative_path: str) -> list[StringCandidate]:
    if should_skip_path(relative_path):
        return []

    source_bytes = source.encode("utf-8")
    matched_ranges = {
        (occurrence.start_byte, occurrence.end_byte)
        for occurrence in extract_ui_strings_from_source(source, relative_path)
    }

    parser = make_rust_parser()
    tree = parser.parse(source_bytes)
    if tree is None:
        return []

    candidates: list[StringCandidate] = []
    for node in walk_nodes(tree.root_node):
        if node.type != "string_literal":
            continue

        literal = node_text(source_bytes, node)
        candidates.append(
            StringCandidate(
                source=parse_rust_string_literal(literal),
                file=relative_path,
                line=node.start_point[0] + 1,
                call=_nearest_call(source_bytes, node),
                matched_by_rule=(node.start_byte, node.end_byte) in matched_ranges,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
            )
        )

    return candidates


def audit_repository(zed_root: Path) -> dict[str, object]:
    candidates = []
    for rust_file in iter_rust_files(zed_root):
        relative_path = rust_file.relative_to(zed_root).as_posix()
        source = rust_file.read_text(encoding="utf-8")
        candidates.extend(
            candidate.to_json()
            for candidate in audit_string_candidates_from_source(source, relative_path)
        )

    matched_count = sum(1 for candidate in candidates if candidate["matched_by_rule"])
    unmatched_count = len(candidates) - matched_count
    return {
        "summary": {
            "candidate_count": len(candidates),
            "matched_by_rule_count": matched_count,
            "unmatched_count": unmatched_count,
            "unmatched_top_calls": _top_calls(
                candidate["call"]
                for candidate in candidates
                if not candidate["matched_by_rule"]
            ),
        },
        "candidates": candidates,
    }


def _nearest_call(source_bytes: bytes, node) -> str:
    current = node.parent
    while current is not None:
        if current.type == "call_expression":
            function_node = current.child_by_field_name("function")
            if function_node is not None:
                return node_text(source_bytes, function_node).strip()
        if current.type == "macro_invocation":
            name_node = current.child_by_field_name("macro")
            if name_node is not None:
                return f"{node_text(source_bytes, name_node).strip()}!"
        current = current.parent
    return ""


def _top_calls(calls: Iterable[object]) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for call in calls:
        call_name = call if isinstance(call, str) else ""
        counts[call_name] = counts.get(call_name, 0) + 1
    return [
        {"call": call, "count": count}
        for call, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:50]
    ]
