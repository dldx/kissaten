"""Pre/post-flight validation gates for varietal and processing method mappings.

Centralises the "load JSON file, run validator, raise on issues" flow so the
categorizer CLIs and the database loader can all enforce the same invariant:
one canonical mapping per original_name.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path

from rich.console import Console

from .processing_method_categorizer import ProcessCategorizer
from .varietal_categorizer import VarietalCategorizer

console = Console()


class MappingValidationError(ValueError):
    """Raised when one of the mappings files has duplicate original_name entries.

    Inherits from ``ValueError`` for backward compatibility with code that
    previously raised ``ValueError`` directly. Always carries the list of
    issues on the ``issues`` attribute for callers that want to render them
    with ``print_validation_report_static``.
    """


def _raise_or_warn(
    label: str,
    mappings_file: Path,
    issues: list[dict],
    *,
    printer: Callable[[list[dict], Path | str], None],
    raise_on_error: bool,
) -> None:
    """Render issues and either raise or warn.

    Centralised so all call sites (post-categorizer CLI gate, pre-load db.py
    gate) behave the same way.
    """
    if not issues:
        console.print(f"[bold green]OK[/bold green] {label}: no duplicate original_name entries in {mappings_file}")
        return

    console.print(f"[bold red]✗ {label} validation FAILED[/bold red] for {mappings_file}")
    printer(issues, mappings_file)

    if raise_on_error:
        conflicts = sum(1 for i in issues if i.get("is_conflict"))
        redundant = len(issues) - conflicts
        raise MappingValidationError(
            f"{mappings_file} contains {len(issues)} duplicate original_name "
            f"group(s) ({conflicts} conflicting, {redundant} redundant). "
            f"Run `kissaten categorize {label.lower()}-validate` to inspect, "
            f"then fix the file before retrying."
        )
    else:
        console.print(
            f"[yellow]⚠ {label} validation found issues but continuing "
            f"(raise_on_error=False).[/yellow]"
        )


def validate_varietal_mappings_file(
    mappings_file: Path,
    *,
    raise_on_error: bool = True,
) -> list[dict]:
    """Validate the varietal mappings file and return the list of issues.

    If ``raise_on_error`` is True (the default), raises
    :class:`MappingValidationError` when any duplicates are found. The
    returned list is always populated for the caller to inspect, even when
    raising.
    """
    return _validate_file(
        label="Varietal",
        mappings_file=mappings_file,
        validator=VarietalCategorizer.validate_mappings_static,
        printer=VarietalCategorizer.print_validation_report_static,
        raise_on_error=raise_on_error,
    )


def validate_processing_mappings_file(
    mappings_file: Path,
    *,
    raise_on_error: bool = True,
) -> list[dict]:
    """Validate the processing method mappings file and return the list of issues."""
    return _validate_file(
        label="Processing method",
        mappings_file=mappings_file,
        validator=ProcessCategorizer.validate_mappings_static,
        printer=ProcessCategorizer.print_validation_report_static,
        raise_on_error=raise_on_error,
    )


def validate_both_mappings_files(
    *,
    raise_on_error: bool = True,
) -> list[dict]:
    """Validate both mappings files. Returns a flat list of all issues found."""
    base = Path(__file__).parent.parent / "database"
    varietal_file = base / "varietal_mappings.json"
    processing_file = base / "processing_methods_mappings.json"

    all_issues: list[dict] = []
    all_issues.extend(
        _validate_file(
            label="Varietal",
            mappings_file=varietal_file,
            validator=VarietalCategorizer.validate_mappings_static,
            printer=VarietalCategorizer.print_validation_report_static,
            raise_on_error=False,  # collect, don't raise
        )
    )
    all_issues.extend(
        _validate_file(
            label="Processing method",
            mappings_file=processing_file,
            validator=ProcessCategorizer.validate_mappings_static,
            printer=ProcessCategorizer.print_validation_report_static,
            raise_on_error=False,  # collect, don't raise
        )
    )

    if all_issues and raise_on_error:
        raise MappingValidationError(
            f"Found {len(all_issues)} duplicate original_name group(s) across "
            f"the varietal and processing method mappings files. "
            f"Run `kissaten validate-mappings` to inspect."
        )

    return all_issues


def _validate_file(
    *,
    label: str,
    mappings_file: Path,
    validator: Callable[[Iterable[dict]], list[dict]],
    printer: Callable[[list[dict], Path | str], None],
    raise_on_error: bool,
) -> list[dict]:
    """Read the file, run the validator, render issues, raise/warn as configured."""
    if not mappings_file.exists():
        # Nothing to validate; not an error (categorizer hasn't run yet).
        return []

    with open(mappings_file, encoding="utf-8") as f:
        data = json.load(f)

    issues = validator(data)
    _raise_or_warn(
        label=label,
        mappings_file=mappings_file,
        issues=issues,
        printer=printer,
        raise_on_error=raise_on_error,
    )
    return issues


__all__ = [
    "MappingValidationError",
    "validate_varietal_mappings_file",
    "validate_processing_mappings_file",
    "validate_both_mappings_files",
]
