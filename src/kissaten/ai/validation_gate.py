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
    allow_redundant: bool = False,
) -> list[dict]:
    """Render issues and either raise or warn.

    Centralised so all call sites (post-categorizer CLI gate, pre-load db.py
    gate) behave the same way.

    When ``allow_redundant`` is True, non-conflict (redundant) issues are
    filtered out before raising/printing. The file can still be loaded, but
    the user is told about the dirty state via the "Issues found" message
    below. This is the right default for production loading paths
    (``load_coffee_data`` / ``refresh_canonical_data``), where the runtime
    handles case-variants deterministically and a redundant row is dead
    weight, not a bug. The CLI ``validate-mappings`` and the post-run
    categorizer gate should keep the strict default (``False``) so the
    user is forced to clean up.
    """
    if allow_redundant:
        issues = [i for i in issues if i.get("is_conflict")]

    if not issues:
        console.print(f"[bold green]OK[/bold green] {label}: no duplicate original_name entries in {mappings_file}")
        return issues

    console.print(f"[bold red]✗ {label} validation FAILED[/bold red] for {mappings_file}")
    printer(issues, mappings_file)

    if raise_on_error:
        # ``issues`` is post-filter when ``allow_redundant`` is True (so all
        # are real conflicts); pre-filter otherwise (so it can include both
        # conflicting and redundant groups, which the user needs to know about
        # to fix the file).
        if allow_redundant:
            summary = f"{len(issues)} conflicting duplicate original_name group(s)"
        else:
            conflicts = sum(1 for i in issues if i.get("is_conflict"))
            redundant = len(issues) - conflicts
            summary = (
                f"{len(issues)} duplicate original_name group(s) "
                f"({conflicts} conflicting, {redundant} redundant)"
            )
        raise MappingValidationError(
            f"{mappings_file} contains {summary}. "
            f"Run `kissaten validate-mappings` to inspect, "
            f"then fix the file before retrying."
        )
    else:
        console.print(
            f"[yellow]⚠ {label} validation found issues but continuing "
            f"(raise_on_error=False).[/yellow]"
        )
    return issues


def validate_varietal_mappings_file(
    mappings_file: Path,
    *,
    raise_on_error: bool = True,
    allow_redundant: bool = False,
) -> list[dict]:
    """Validate the varietal mappings file and return the list of issues.

    If ``raise_on_error`` is True (the default), raises
    :class:`MappingValidationError` when conflicting duplicate ``original_name``
    entries are found. The returned list is always populated for the caller
    to inspect, even when raising.

    If ``allow_redundant`` is True, non-conflict duplicates (entries that
    agree on the canonical) are filtered out before the raise/warn decision.
    Use this in production loading paths where the runtime handles
    case-variants deterministically.
    """
    return _validate_file(
        label="Varietal",
        mappings_file=mappings_file,
        validator=VarietalCategorizer.validate_mappings_static,
        printer=VarietalCategorizer.print_validation_report_static,
        raise_on_error=raise_on_error,
        allow_redundant=allow_redundant,
    )


def validate_processing_mappings_file(
    mappings_file: Path,
    *,
    raise_on_error: bool = True,
    allow_redundant: bool = False,
) -> list[dict]:
    """Validate the processing method mappings file and return the list of issues.

    See :func:`validate_varietal_mappings_file` for ``raise_on_error`` and
    ``allow_redundant`` semantics.
    """
    return _validate_file(
        label="Processing method",
        mappings_file=mappings_file,
        validator=ProcessCategorizer.validate_mappings_static,
        printer=ProcessCategorizer.print_validation_report_static,
        raise_on_error=raise_on_error,
        allow_redundant=allow_redundant,
    )


def validate_both_mappings_files(
    *,
    raise_on_error: bool = True,
    allow_redundant: bool = False,
) -> list[dict]:
    """Validate both mappings files. Returns a flat list of all issues found.

    ``allow_redundant`` is passed through to both per-file validators.
    """
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
            allow_redundant=allow_redundant,
        )
    )
    all_issues.extend(
        _validate_file(
            label="Processing method",
            mappings_file=processing_file,
            validator=ProcessCategorizer.validate_mappings_static,
            printer=ProcessCategorizer.print_validation_report_static,
            raise_on_error=False,  # collect, don't raise
            allow_redundant=allow_redundant,
        )
    )

    if all_issues and raise_on_error:
        raise MappingValidationError(
            f"Found {len(all_issues)} conflicting duplicate original_name "
            f"group(s) across the varietal and processing method mappings "
            f"files. Run `kissaten validate-mappings` to inspect."
        )

    return all_issues


def _validate_file(
    *,
    label: str,
    mappings_file: Path,
    validator: Callable[[Iterable[dict]], list[dict]],
    printer: Callable[[list[dict], Path | str], None],
    raise_on_error: bool,
    allow_redundant: bool = False,
) -> list[dict]:
    """Read the file, run the validator, render issues, raise/warn as configured."""
    if not mappings_file.exists():
        # Nothing to validate; not an error (categorizer hasn't run yet).
        return []

    with open(mappings_file, encoding="utf-8") as f:
        data = json.load(f)

    issues = validator(data)
    return _raise_or_warn(
        label=label,
        mappings_file=mappings_file,
        issues=issues,
        printer=printer,
        raise_on_error=raise_on_error,
        allow_redundant=allow_redundant,
    )


__all__ = [
    "MappingValidationError",
    "validate_varietal_mappings_file",
    "validate_processing_mappings_file",
    "validate_both_mappings_files",
]
