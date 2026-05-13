from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import shutil
from typing import Any

from .rust_strings import rust_format_placeholders
from .translation_checks import protected_tokens_match
from .vscode_loc import (
    VscodeTranslationIndex,
    find_vscode_references,
    load_vscode_translation_memory,
)


@dataclass
class PrepareTranslationReport:
    language: str
    source_count: int
    batch_count: int
    output_dir: str
    batches: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PrepareTranslationOptions:
    batch_size: int = 40
    context_lines: int = 12
    missing_only: bool = True
    output_dir: Path | None = None
    prompt_path: Path | None = None
    vscode_loc_root: Path | None = None
    vscode_source_root: Path | None = None
    vscode_reference_count: int = 3

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ValueError("batch size must be positive")
        if self.context_lines < 0:
            raise ValueError("context lines must be zero or positive")


@dataclass
class MergeTranslationReport:
    language: str
    merged: list[str] = field(default_factory=list)
    null_values: list[str] = field(default_factory=list)
    unknown_sources: list[str] = field(default_factory=list)
    invalid_values: list[str] = field(default_factory=list)
    placeholder_mismatches: list[str] = field(default_factory=list)
    protected_token_mismatches: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (
            self.unknown_sources
            or self.invalid_values
            or self.placeholder_mismatches
            or self.protected_token_mismatches
        )


@dataclass
class CleanupTranslationReport:
    language: str
    output_dir: str
    removed: bool


def prepare_translation_batches(
    root: Path,
    language: str,
    zed_root: Path,
    options: PrepareTranslationOptions | None = None,
) -> PrepareTranslationReport:
    options = options or PrepareTranslationOptions()
    manifest = _read_json(root / "manifest" / "ui-strings.json")
    translations = _read_json_if_exists(root / "translations" / f"{language}.json")
    output_dir = options.output_dir or root / "reports" / "translation" / language
    prompt_path = options.prompt_path or root / "prompts" / "translation" / f"{language}.md"
    prompt_used = prompt_path if prompt_path.exists() else root / "prompts" / "translation" / "TEMPLATE.md"
    base_prompt = prompt_used.read_text(encoding="utf-8") if prompt_used.exists() else ""
    base_prompt = base_prompt.replace("{language}", language)
    glossary_prompt = "" if _has_internal_glossary(base_prompt) else _language_glossary_prompt(root, language)
    if glossary_prompt:
        base_prompt = "\n\n".join(part for part in [base_prompt.strip(), glossary_prompt] if part)

    sources = _sources_to_translate(manifest, translations, options.missing_only)
    batches = [
        sources[index : index + options.batch_size]
        for index in range(0, len(sources), options.batch_size)
    ]
    vscode_memory = (
        VscodeTranslationIndex(
            load_vscode_translation_memory(
                options.vscode_loc_root,
                language,
                options.vscode_source_root,
            )
        )
        if options.vscode_loc_root is not None
        and options.vscode_loc_root.exists()
        and options.vscode_reference_count > 0
        else None
    )

    cleanup_translation_workspace(root, language, output_dir)
    batch_dir = output_dir / "batches"
    prompt_dir = output_dir / "prompts"
    result_dir = output_dir / "results"
    batch_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    plan_batches: list[dict[str, Any]] = []
    for batch_index, batch_sources in enumerate(batches, start=1):
        batch_file = batch_dir / f"batch-{batch_index:03d}.json"
        prompt_file = prompt_dir / f"batch-{batch_index:03d}.md"
        result_file = result_dir / f"batch-{batch_index:03d}.json"
        entries = [
            _translation_entry(
                source,
                manifest[source],
                zed_root,
                options.context_lines,
                vscode_memory,
                options.vscode_reference_count,
            )
            for source in batch_sources
        ]
        batch_payload = {
            "language": language,
            "batch_index": batch_index,
            "batch_count": len(batches),
            "entries": entries,
            "output": {
                "result_file": _relative_to_root(root, result_file),
                "format": {"source": "translation"},
                "null_means": "Skip this source and leave it untranslated for manual review.",
            },
        }
        _write_json(batch_file, batch_payload)
        prompt_file.write_text(
            _batch_prompt(base_prompt, batch_payload),
            encoding="utf-8",
        )
        plan_batches.append(
            {
                "batch_file": _relative_to_root(root, batch_file),
                "prompt_file": _relative_to_root(root, prompt_file),
                "result_file": _relative_to_root(root, result_file),
                "source_count": len(entries),
            }
        )

    plan = {
        "language": language,
        "source_count": len(sources),
        "batch_count": len(batches),
        "missing_only": options.missing_only,
        "context_lines": options.context_lines,
        "prompt_path": _relative_to_root(root, prompt_used),
        "batches": plan_batches,
        "agent_workflow": [
            "Give each prompt_file to one translation agent.",
            "Each agent returns only JSON using the original source strings as keys.",
            "Save each agent JSON response to the matching result_file.",
            f"Run zed-i18n merge-translation --language {language} "
            f"--results-dir {_relative_to_root(root, result_dir)}.",
            f"Run zed-i18n validate --language {language}.",
        ],
    }
    _write_json(output_dir / "plan.json", plan)
    return PrepareTranslationReport(
        language=language,
        source_count=len(sources),
        batch_count=len(batches),
        output_dir=_relative_to_root(root, output_dir),
        batches=[batch["batch_file"] for batch in plan_batches],
    )


def merge_translation_results(
    root: Path,
    language: str,
    results_dir: Path | None = None,
    output_path: Path | None = None,
) -> MergeTranslationReport:
    manifest = _read_json(root / "manifest" / "ui-strings.json")
    translations_path = root / "translations" / f"{language}.json"
    output_path = output_path or translations_path
    translations = _read_json_if_exists(translations_path)
    accepted_sources = {
        source for source, entry in manifest.items() if entry.get("status") == "accepted"
    }
    results_dir = results_dir or root / "reports" / "translation" / language / "results"
    report = MergeTranslationReport(language=language)
    if not results_dir.is_dir():
        raise ValueError(f"translation results directory does not exist: {results_dir}")
    result_files = sorted(results_dir.glob("*.json"))
    if not result_files:
        raise ValueError(f"no translation result JSON files found in {results_dir}")

    for result_file in result_files:
        result = _read_json(result_file)
        for source, translation in result.items():
            if source not in accepted_sources:
                report.unknown_sources.append(source)
                continue
            if translation is None:
                report.null_values.append(source)
                continue
            if not isinstance(translation, str):
                report.invalid_values.append(source)
                continue
            if rust_format_placeholders(source) != rust_format_placeholders(translation):
                report.placeholder_mismatches.append(source)
                continue
            if not protected_tokens_match(source, translation):
                report.protected_token_mismatches.append(source)
                continue
            translations[source] = translation
            report.merged.append(source)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_path, translations)
    _write_json(results_dir.parent / "merge-summary.json", asdict(report))
    return report


def cleanup_translation_workspace(
    root: Path,
    language: str,
    output_dir: Path | None = None,
) -> CleanupTranslationReport:
    output_dir = output_dir or root / "reports" / "translation" / language
    output_dir = _safe_translation_workspace(root, language, output_dir)
    removed = output_dir.exists()
    if removed:
        shutil.rmtree(output_dir)
    return CleanupTranslationReport(
        language=language,
        output_dir=_relative_to_root(root, output_dir),
        removed=removed,
    )


def _sources_to_translate(
    manifest: dict[str, dict[str, Any]],
    translations: dict[str, str],
    missing_only: bool,
) -> list[str]:
    sources: list[str] = []
    for source in sorted(manifest):
        entry = manifest[source]
        if entry.get("status") != "accepted":
            continue
        if missing_only and source in translations:
            continue
        sources.append(source)
    return sources


def _translation_entry(
    source: str,
    manifest_entry: dict[str, Any],
    zed_root: Path,
    context_lines: int,
    vscode_memory: VscodeTranslationIndex | None = None,
    vscode_reference_count: int = 3,
) -> dict[str, Any]:
    occurrences = manifest_entry.get("occurrences", [])
    first_occurrence = occurrences[0] if occurrences else {}
    entry = {
        "source": source,
        "kind": first_occurrence.get("kind", ""),
        "call": first_occurrence.get("call", ""),
        "occurrences": occurrences,
        "code_context": _code_context(zed_root, first_occurrence, context_lines),
    }
    if vscode_memory and _source_can_use_vscode_references(source):
        references = find_vscode_references(
            source,
            vscode_memory,
            limit=vscode_reference_count,
            min_score=0.86,
        )
        if references:
            entry["vscode_references"] = references
    return entry


def _source_can_use_vscode_references(source: str) -> bool:
    stripped = source.strip()
    if len(stripped) < 3:
        return False
    if stripped[0] in "\"'`#([{<" or stripped[-1] in "\"'`)]}>":
        return False
    if "/" in stripped or "\\" in stripped or "_" in stripped:
        return False
    if re.fullmatch(r"[a-z0-9]+(?:[-.][a-z0-9]+)+", stripped):
        return False
    words = re.findall(r"[A-Za-z]+", stripped)
    if not words:
        return False
    if len(words) == 1 and words[0].islower():
        return False
    return True


def _code_context(
    zed_root: Path,
    occurrence: dict[str, Any],
    context_lines: int,
) -> str:
    file = occurrence.get("file")
    line = occurrence.get("line")
    if not isinstance(file, str) or not isinstance(line, int):
        return ""
    source_path = zed_root / file
    if not source_path.exists():
        return ""
    lines = source_path.read_text(encoding="utf-8").splitlines()
    start = max(1, line - context_lines)
    end = min(len(lines), line + context_lines)
    width = len(str(end))
    return "\n".join(
        f"{line_number:>{width}}: {lines[line_number - 1]}"
        for line_number in range(start, end + 1)
    )


def _batch_prompt(base_prompt: str, batch_payload: dict[str, Any]) -> str:
    return "\n\n".join(
        part
        for part in [
            base_prompt.strip(),
            "## Agent Batch Instructions\n"
            "Translate only the entries in this batch. Return only JSON. "
            "Use each `source` value as the exact JSON key. "
            "Use `null` when the item should be left for manual review. "
            "When an entry has `vscode_references`, treat them as VS Code language-pack "
            "translation-memory hints, not mandatory replacements. "
            "Save the JSON response to the `output.result_file` path after translation.",
            "## Batch Payload\n"
            "```json\n"
            f"{json.dumps(batch_payload, ensure_ascii=False, indent=2, sort_keys=True)}\n"
            "```",
        ]
        if part
    )


def _language_glossary_prompt(root: Path, language: str) -> str:
    glossary_dir = root / "prompts" / "translation" / "glossary"
    candidates = [glossary_dir / f"{language}.md", glossary_dir / f"{language.lower()}.md"]
    if "-" in language:
        candidates.append(glossary_dir / f"{language.split('-', 1)[0]}.md")
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return ""


def _has_internal_glossary(prompt: str) -> bool:
    return any(line.strip().startswith("## GLOSSARY") for line in prompt.splitlines())


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return _read_json(path)


def _safe_translation_workspace(root: Path, language: str, output_dir: Path) -> Path:
    workspace = root.resolve()
    base = (root / "reports" / "translation").resolve()
    default = (base / language).resolve()
    target = output_dir.resolve()
    if target == workspace or workspace not in target.parents:
        raise ValueError("translation workspace cleanup target must be inside the project workspace")
    if target == base:
        raise ValueError("translation workspace cleanup cannot remove reports/translation itself")
    if target == default or base in target.parents:
        return target
    if not target.exists() or (target / "plan.json").exists():
        return target
    raise ValueError("custom translation workspace cleanup requires an existing plan.json")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
