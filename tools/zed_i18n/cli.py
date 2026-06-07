from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable

from .apply import apply_translations
from .audit import audit_repository
from .config import load_project_config, zed_checkout_path, zed_clean_extract_checkout_path
from .context_groups import build_context_groups, write_context_group_reports
from .extract import extract_repository
from .packaging import generate_packaging_files
from .translation_pipeline import (
    PrepareTranslationOptions,
    cleanup_translation_workspace,
    merge_translation_results,
    prepare_translation_batches,
)
from .validate import validate_translations
from .vscode_loc import (
    extract_glossary_terms_from_prompt,
    generate_prompt_glossary_markdown,
    generate_vscode_glossary_markdown,
    is_vscode_pseudo_language,
    list_vscode_languages,
)
from .zed_source import build_clone_command, ensure_inside_workspace, verify_checkout_revision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zed-i18n")
    parser.add_argument("--root", default=".", help="zed-i18n repository root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("fetch-zed")

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument(
        "--zed-root",
        help="Zed source checkout to extract from. Use a clean upstream checkout.",
    )

    audit_parser = subparsers.add_parser("audit-candidates")
    audit_parser.add_argument(
        "--zed-root",
        help="Zed source checkout to audit. Use a clean upstream checkout.",
    )

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--language", required=True)
    validate_parser.add_argument(
        "--cleanup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Remove reports/translation/<language> after successful validation.",
    )

    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--language", required=True)

    prepare_translation_parser = subparsers.add_parser("prepare-translation")
    prepare_translation_parser.add_argument("--language", required=True)
    prepare_translation_parser.add_argument(
        "--zed-root",
        help="Clean Zed source checkout used to include source code context.",
    )
    prepare_translation_parser.add_argument("--batch-size", type=int, default=40)
    prepare_translation_parser.add_argument("--context-lines", type=int, default=12)
    prepare_translation_parser.add_argument(
        "--output-dir",
        help="Directory for agent batch files. Defaults to reports/translation/<language>.",
    )
    prepare_translation_parser.add_argument(
        "--prompt",
        help="Base prompt file. Defaults to prompts/translation/<language>.md.",
    )
    prepare_translation_parser.add_argument(
        "--vscode-loc-root",
        default=".cache/vscode-loc",
        help="VS Code localization checkout used to add translation-memory references.",
    )
    prepare_translation_parser.add_argument(
        "--vscode-source-root",
        default=".cache/vscode-upstream",
        help="VS Code source checkout used to recover English source strings for VS Code references.",
    )
    prepare_translation_parser.add_argument(
        "--vscode-reference-count",
        type=int,
        default=3,
        help="Maximum VS Code translation-memory references per source string.",
    )
    prepare_scope = prepare_translation_parser.add_mutually_exclusive_group()
    prepare_scope.set_defaults(missing_only=True)
    prepare_scope.add_argument(
        "--missing-only",
        action="store_true",
        dest="missing_only",
        help="Prepare only accepted strings missing from translations/<language>.json.",
    )
    prepare_scope.add_argument(
        "--all",
        action="store_false",
        dest="missing_only",
        help="Prepare all accepted strings, not only missing translations.",
    )

    merge_translation_parser = subparsers.add_parser("merge-translation")
    merge_translation_parser.add_argument("--language", required=True)
    merge_translation_parser.add_argument(
        "--results-dir",
        help="Directory containing agent JSON results. Defaults to reports/translation/<language>/results.",
    )
    merge_translation_parser.add_argument(
        "--output",
        help="Translation JSON to write. Defaults to translations/<language>.json.",
    )

    context_groups_parser = subparsers.add_parser("extract-context-groups")
    context_groups_parser.add_argument("--language", required=True)
    context_groups_parser.add_argument(
        "--zed-root",
        help="Clean Zed source checkout used to resolve grouped source context.",
    )
    context_groups_parser.add_argument(
        "--group-type",
        choices=("all", "settings", "connected", "prompt", "prompt-components"),
        default="all",
        help="Which grouped review reports to write.",
    )
    context_groups_parser.add_argument(
        "--output-dir",
        help="Defaults to reports/context-groups/<language>.",
    )

    vscode_glossary_parser = subparsers.add_parser("generate-vscode-glossary")
    vscode_glossary_parser.add_argument(
        "--language",
        required=True,
        help="Target language such as ko-KR, ja-JP, or 'all'.",
    )
    vscode_glossary_parser.add_argument(
        "--vscode-loc-root",
        default=".cache/vscode-loc",
        help="VS Code localization checkout. Defaults to .cache/vscode-loc.",
    )
    vscode_glossary_parser.add_argument(
        "--vscode-source-root",
        default=".cache/vscode-upstream",
        help="VS Code source checkout used to recover English source strings.",
    )
    vscode_glossary_parser.add_argument(
        "--prompt",
        default="prompts/translation/vscode-glossary-terms.md",
        help="Markdown file containing glossary source terms.",
    )
    vscode_glossary_parser.add_argument(
        "--output",
        help="Markdown output path. Defaults to reports/vscode-glossary/<language>.md.",
    )
    vscode_glossary_parser.add_argument(
        "--prompt-glossary-output-dir",
        default="prompts/translation/glossary",
        help="Directory for generated prompt glossary files.",
    )

    packaging_parser = subparsers.add_parser("generate-packaging")
    packaging_parser.add_argument("--manifest", required=True, help="Release manifest.json path.")
    packaging_parser.add_argument(
        "--cask-out",
        required=True,
        help="Output path for Casks/zed-i18n.rb in the Homebrew tap checkout.",
    )
    packaging_parser.add_argument(
        "--bucket-out",
        required=True,
        help="Output directory for Scoop bucket manifests.",
    )
    packaging_parser.add_argument(
        "--require-all-translations",
        action="store_true",
        help="Require packaging assets for every locale in translations/*.json.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "fetch-zed":
        return run_fetch_zed(root)
    if args.command == "extract":
        return run_extract(root, args.zed_root)
    if args.command == "audit-candidates":
        return run_audit_candidates(root, args.zed_root)
    if args.command == "validate":
        return run_validate(root, args.language, cleanup=args.cleanup)
    if args.command == "apply":
        return run_apply(root, args.language)
    if args.command == "prepare-translation":
        return run_prepare_translation(
            root,
            args.language,
            args.zed_root,
            args.batch_size,
            args.context_lines,
            args.missing_only,
            args.output_dir,
            args.prompt,
            args.vscode_loc_root,
            args.vscode_source_root,
            args.vscode_reference_count,
        )
    if args.command == "merge-translation":
        return run_merge_translation(root, args.language, args.results_dir, args.output)
    if args.command == "extract-context-groups":
        return run_extract_context_groups(
            root,
            args.language,
            args.zed_root,
            args.group_type,
            args.output_dir,
        )
    if args.command == "generate-vscode-glossary":
        return run_generate_vscode_glossary(
            root,
            args.language,
            args.vscode_loc_root,
            args.vscode_source_root,
            args.prompt,
            args.output,
            args.prompt_glossary_output_dir,
        )
    if args.command == "generate-packaging":
        return run_generate_packaging(
            root,
            args.manifest,
            args.cask_out,
            args.bucket_out,
            require_all_translations=args.require_all_translations,
        )

    parser.error(f"unknown command: {args.command}")


def run_fetch_zed(root: Path) -> int:
    config = load_project_config(root)
    checkout_paths = (
        zed_checkout_path(root, config),
        zed_clean_extract_checkout_path(root, config),
    )
    for checkout_path in checkout_paths:
        ensure_inside_workspace(root, checkout_path)

    for checkout_path in checkout_paths:
        if checkout_path.exists():
            print(f"Zed checkout already exists: {checkout_path}")
            verify_checkout_revision(config, checkout_path)
            continue

        checkout_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(build_clone_command(config, checkout_path), check=True)
        verify_checkout_revision(config, checkout_path)
    return 0


def run_extract(root: Path, zed_root: str | None = None) -> int:
    config = load_project_config(root)
    checkout_path = resolve_zed_root(root, config, zed_root)
    catalog, manifest = extract_repository(checkout_path)
    previous_manifest = _read_json_if_exists(root / "manifest" / "ui-strings.json")
    translation_sources = _translation_sources(root / "translations")
    preserve_manifest_statuses(manifest, previous_manifest, translation_sources)

    _write_json(root / "catalog" / "en-US.json", catalog)
    _write_json(root / "manifest" / "ui-strings.json", manifest)
    occurrence_count = sum(len(entry["occurrences"]) for entry in manifest.values())
    _write_json(
        root / "reports" / "extract-summary.json",
        {
            "source_count": len(catalog),
            "occurrence_count": occurrence_count,
        },
    )
    print(f"Extracted {len(catalog)} source strings from {occurrence_count} occurrences")
    return 0


def preserve_manifest_statuses(
    manifest: dict[str, dict[str, object]],
    previous_manifest: dict[str, dict[str, object]],
    translation_sources: Iterable[str],
) -> None:
    translated_sources = set(translation_sources)
    for source, entry in manifest.items():
        previous_entry = previous_manifest.get(source, {})
        previous_status = previous_entry.get("status")
        if previous_status in {"accepted", "ignored"}:
            entry["status"] = previous_status
        elif source in translated_sources:
            entry["status"] = "accepted"


def run_audit_candidates(root: Path, zed_root: str | None = None) -> int:
    config = load_project_config(root)
    checkout_path = resolve_zed_root(root, config, zed_root)
    report = audit_repository(checkout_path)
    _write_json(root / "reports" / "ui-candidate-audit.json", report)
    summary = report["summary"]
    print(
        "Audited "
        f"{summary['candidate_count']} string candidates; "
        f"{summary['matched_by_rule_count']} matched extraction rules, "
        f"{summary['unmatched_count']} unmatched"
    )
    return 0


def resolve_zed_root(root: Path, config, zed_root: str | None) -> Path:
    checkout_path = Path(zed_root) if zed_root else zed_clean_extract_checkout_path(root, config)
    if not checkout_path.is_absolute():
        checkout_path = root / checkout_path
    return ensure_inside_workspace(root, checkout_path)


def run_validate(root: Path, language: str, cleanup: bool = True) -> int:
    manifest = _read_json(root / "manifest" / "ui-strings.json")
    translations = _read_json(root / "translations" / f"{language}.json")
    report = validate_translations(manifest, translations)
    _write_json(root / "reports" / f"validate-{language}.json", asdict(report))
    if not report.ok:
        print(
            f"Validation failed for {language}: "
            f"{len(report.missing)} missing, "
            f"{len(report.placeholder_mismatches)} placeholder mismatches, "
            f"{len(report.protected_token_mismatches)} protected token mismatches, "
            f"{len(report.extra)} extra translations"
        )
        return 1
    print(f"Validation passed for {language}")
    if cleanup:
        cleanup_report = cleanup_translation_workspace(root, language)
        if cleanup_report.removed:
            print(f"Cleaned translation workspace: {cleanup_report.output_dir}")
    return 0


def run_apply(root: Path, language: str) -> int:
    config = load_project_config(root)
    checkout_path = zed_checkout_path(root, config)
    manifest = _read_json(root / "manifest" / "ui-strings.json")
    translations = _read_json(root / "translations" / f"{language}.json")
    report = apply_translations(checkout_path, manifest, translations)
    _write_json(root / "reports" / f"apply-{language}.json", asdict(report))
    if not report.ok:
        print(
            f"Apply failed for {language}: "
            f"{len(report.missing)} missing translations, {len(report.stale)} stale occurrences"
        )
        return 1
    print(f"Applied {len(report.applied)} source strings for {language}")
    return 0


def run_prepare_translation(
    root: Path,
    language: str,
    zed_root: str | None,
    batch_size: int,
    context_lines: int,
    missing_only: bool,
    output_dir: str | None,
    prompt: str | None,
    vscode_loc_root: str | None = ".cache/vscode-loc",
    vscode_source_root: str | None = ".cache/vscode-upstream",
    vscode_reference_count: int = 3,
) -> int:
    output_path = _resolve_optional_workspace_path(root, output_dir)
    prompt_path = _resolve_optional_workspace_path(root, prompt)
    vscode_loc_path = _resolve_optional_workspace_path(root, vscode_loc_root)
    if vscode_loc_path is not None and not vscode_loc_path.exists():
        vscode_loc_path = None
    vscode_source_path = _resolve_optional_workspace_path(root, vscode_source_root)
    if vscode_source_path is not None and not vscode_source_path.exists():
        vscode_source_path = None
    options = PrepareTranslationOptions(
        batch_size=batch_size,
        context_lines=context_lines,
        missing_only=missing_only,
        output_dir=output_path,
        prompt_path=prompt_path,
        vscode_loc_root=vscode_loc_path,
        vscode_source_root=vscode_source_path,
        vscode_reference_count=vscode_reference_count,
    )
    config = load_project_config(root)
    checkout_path = resolve_zed_root(root, config, zed_root)
    report = prepare_translation_batches(
        root=root,
        language=language,
        zed_root=checkout_path,
        options=options,
    )
    _write_json(root / "reports" / "translation" / language / "prepare-summary.json", asdict(report))
    print(
        f"Prepared {report.source_count} source strings in {report.batch_count} "
        f"agent batches for {language}: {report.output_dir}"
    )
    return 0


def run_generate_vscode_glossary(
    root: Path,
    language: str,
    vscode_loc_root: str,
    vscode_source_root: str,
    prompt: str,
    output: str | None,
    prompt_glossary_output_dir: str | None,
) -> int:
    vscode_loc_path = _resolve_optional_workspace_path(root, vscode_loc_root)
    vscode_source_path = _resolve_optional_workspace_path(root, vscode_source_root)
    prompt_path = _resolve_optional_workspace_path(root, prompt)
    prompt_glossary_output_path = _resolve_optional_workspace_path(
        root,
        prompt_glossary_output_dir,
    )
    if vscode_loc_path is None or not vscode_loc_path.exists():
        raise ValueError("VS Code localization checkout does not exist")
    if prompt_path is None or not prompt_path.exists():
        raise ValueError("glossary source prompt does not exist")
    if vscode_source_path is not None and not vscode_source_path.exists():
        vscode_source_path = None
    if language.lower() != "all" and is_vscode_pseudo_language(language):
        raise ValueError(f"{language} is a pseudo-localization language, not a glossary target")

    terms = extract_glossary_terms_from_prompt(prompt_path)
    if not terms:
        raise ValueError("no glossary terms found in prompt")

    if language.lower() == "all":
        languages = list_vscode_languages(vscode_loc_path)
        default_output = root / "reports" / "vscode-glossary" / "all-languages.md"
        output_path = _resolve_optional_workspace_path(root, output) or default_output
        sections = [
            generate_vscode_glossary_markdown(vscode_loc_path, target_language, terms).strip()
            if vscode_source_path is None
            else generate_vscode_glossary_markdown(
                vscode_loc_path,
                target_language,
                terms,
                vscode_source_path,
            ).strip()
            for target_language in languages
        ]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
        prompt_glossary_count = _write_prompt_glossaries(
            vscode_loc_path,
            vscode_source_path,
            prompt_glossary_output_path,
            languages,
            terms,
        )
        print(
            f"Generated VS Code glossary candidates for {len(languages)} languages: {output_path}"
        )
        if prompt_glossary_count:
            print(f"Generated prompt glossaries for {prompt_glossary_count} languages")
        return 0

    default_output = root / "reports" / "vscode-glossary" / f"{language}.md"
    output_path = _resolve_optional_workspace_path(root, output) or default_output
    markdown = generate_vscode_glossary_markdown(
        vscode_loc_path,
        language,
        terms,
        vscode_source_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    prompt_glossary_count = _write_prompt_glossaries(
        vscode_loc_path,
        vscode_source_path,
        prompt_glossary_output_path,
        [language],
        terms,
    )
    print(f"Generated VS Code glossary candidates for {language}: {output_path}")
    if prompt_glossary_count:
        print(f"Generated prompt glossaries for {prompt_glossary_count} languages")
    return 0


def run_generate_packaging(
    root: Path,
    manifest: str,
    cask_out: str,
    bucket_out: str,
    *,
    require_all_translations: bool = False,
) -> int:
    manifest_path = _resolve_workspace_path(root, manifest)
    cask_path = _resolve_workspace_path(root, cask_out)
    bucket_path = _resolve_workspace_path(root, bucket_out)
    expected_locales = _translation_locale_names(root) if require_all_translations else None
    generate_packaging_files(manifest_path, cask_path, bucket_path, expected_locales)
    print(f"Generated Homebrew cask: {_relative_to_root(root, cask_path)}")
    print(f"Generated Scoop bucket manifests: {_relative_to_root(root, bucket_path)}")
    return 0


def run_extract_context_groups(
    root: Path,
    language: str,
    zed_root: str | None,
    group_type: str,
    output_dir: str | None,
) -> int:
    config = load_project_config(root)
    checkout_path = resolve_zed_root(root, config, zed_root)
    manifest = _read_json(root / "manifest" / "ui-strings.json")
    translations = _read_json(root / "translations" / f"{language}.json")
    output_path = (
        _resolve_optional_workspace_path(root, output_dir)
        or root / "reports" / "context-groups" / language
    )
    groups = build_context_groups(checkout_path, manifest, translations)
    write_context_group_reports(output_path, groups, group_type=group_type)
    print(
        f"Extracted {len(groups.settings)} setting groups and "
        f"{len(groups.connected_lines)} connected line groups and "
        f"{len(groups.prompt_components)} prompt component groups for {language}: "
        f"{_relative_to_root(root, output_path)}"
    )
    return 0


def _write_prompt_glossaries(
    vscode_loc_path: Path,
    vscode_source_path: Path | None,
    output_dir: Path | None,
    languages: Iterable[str],
    terms: Iterable[str],
) -> int:
    if output_dir is None:
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for language in languages:
        if is_vscode_pseudo_language(language):
            continue
        markdown = generate_prompt_glossary_markdown(
            vscode_loc_path,
            language,
            terms,
            vscode_source_path,
        )
        (output_dir / f"{language}.md").write_text(markdown, encoding="utf-8")
        count += 1
    return count


def run_merge_translation(
    root: Path,
    language: str,
    results_dir: str | None,
    output: str | None,
) -> int:
    result_path = _resolve_optional_workspace_path(root, results_dir)
    output_path = _resolve_optional_workspace_path(root, output)
    report = merge_translation_results(root, language, result_path, output_path)
    if not report.ok:
        print(
            f"Merged {len(report.merged)} translations for {language} with issues: "
            f"{len(report.unknown_sources)} unknown, "
            f"{len(report.invalid_values)} invalid, "
            f"{len(report.placeholder_mismatches)} placeholder mismatches, "
            f"{len(report.protected_token_mismatches)} protected token mismatches"
        )
        return 1
    print(
        f"Merged {len(report.merged)} translations for {language}; "
        f"{len(report.null_values)} null values skipped"
    )
    return 0


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return _read_json(path)


def _translation_sources(path: Path) -> set[str]:
    if not path.exists():
        return set()

    sources: set[str] = set()
    for translation_file in sorted(path.glob("*.json")):
        sources.update(_read_json(translation_file))
    return sources


def _translation_locale_names(root: Path) -> set[str]:
    translations_dir = root / "translations"
    if not translations_dir.exists():
        raise ValueError("translations directory does not exist")
    locales = {path.stem for path in translations_dir.glob("*.json")}
    if not locales:
        raise ValueError("translations directory has no locale JSON files")
    return locales


def _resolve_optional_workspace_path(root: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return ensure_inside_workspace(root, path)


def _resolve_workspace_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return ensure_inside_workspace(root, path)


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
