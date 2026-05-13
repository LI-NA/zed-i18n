from __future__ import annotations

from dataclasses import dataclass, field

from .rust_strings import rust_format_placeholders
from .translation_checks import protected_tokens_match


@dataclass
class ValidationReport:
    missing: list[str] = field(default_factory=list)
    placeholder_mismatches: list[str] = field(default_factory=list)
    protected_token_mismatches: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (
            self.missing
            or self.placeholder_mismatches
            or self.protected_token_mismatches
            or self.extra
        )


def validate_translations(
    manifest: dict[str, dict[str, object]],
    translations: dict[str, str],
) -> ValidationReport:
    report = ValidationReport()
    accepted_sources: set[str] = set()
    for source, entry in manifest.items():
        if entry.get("status") != "accepted":
            continue
        accepted_sources.add(source)
        translation = translations.get(source)
        if translation is None:
            report.missing.append(source)
            continue
        if rust_format_placeholders(source) != rust_format_placeholders(translation):
            report.placeholder_mismatches.append(source)
        if not protected_tokens_match(source, translation):
            report.protected_token_mismatches.append(source)
    for source in sorted(translations):
        if source not in accepted_sources:
            report.extra.append(source)
    return report
