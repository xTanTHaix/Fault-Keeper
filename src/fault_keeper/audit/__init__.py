"""Fault-Keeper Audit Module — Phase 2: U-FSR + WPA-HIS.

Re-exports the three Phase-1 audit primitives (A-SMW, ACDS, AEC-VS) lazily so
that ``from fault_keeper.audit import ast_merge`` keeps working at call time
without paying eager-import cost on every package load.  The U-FSR and WPA-HIS
pillars live in the sibling :mod:`fault_keeper.audit.ufsr` / :mod:``wpahis``
modules; this file only wires up discovery + lazy binding.
"""

from __future__ import annotations

import os as _os


def discover_audit_modules(root: str) -> dict[str, int]:
    """Scan a directory tree and return every Python file's line count.

    Args:
        root (str): Directory to scan; must exist on disk.

    Returns:
        Dict mapping absolute paths of ``*.py`` files to their total
        line counts.  Non-Python files are skipped silently.
    """
    result: dict[str, int] = {}
    if not _os.path.isdir(root):
        return result  # pragma: no cover - defensive guard

    for dirpath, _, files in _os.walk(root):
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            full_path = _os.path.join(dirpath, filename)
            try:
                with open(full_path, "r", encoding="utf-8") as fh:
                    result[full_path] = len(fh.readlines())  # type: ignore[arg-type]
            except OSError:
                continue

    return result


# ---------------------------------------------------------------------------
# Lazy binding of Phase-1 audit primitives exposed at package level.
#
# Each entry maps a canonical public name to the (module, attribute) pair that
# implements it.  Functions are fetched on first access so importing this
# package never triggers heavy AST / copy-paste analysis up front — which is
# exactly what ``from fault_keeper.audit import ast_merge`` in facade.py needs.
# ---------------------------------------------------------------------------

_LAZY_PRIMITIVES: dict[str, tuple[str, str]] = {
    "ast_merge": ("fault_keeper.audit.ast_rewrite", "ast_merge"),
    "detect_copy_paste_drift": ("fault_keeper.audit.anti_unify", "detect_copy_paste_drift"),
    "validate_env_contract": ("fault_keeper.audit.env_contract", "validate_env_contract"),
}


def _load_primitive(name: str) -> object:
    """Resolve a lazily-bound primitive to its callable/object."""
    module_name, attr = _LAZY_PRIMITIVES[name]  # type: ignore[misc,index]
    resolved_module = __import__(module_name, fromlist=[attr])
    return getattr(resolved_module, attr)


def __getattr__(name: str) -> object:
    """PEP 562 lazy lookup for Phase-1 audit primitives.

    Only invoked when the name is not a real attribute of this module (e.g.
    ``ast_merge``), which also satisfies ``from fault_keeper.audit import X``
    bindings performed by consumers such as :mod:`fault_keeper.core.facade`.
    """
    if name in _LAZY_PRIMITIVES:
        return _load_primitive(name)  # type: ignore[return-value]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__: list[str] = [
    "discover_audit_modules",
    "ast_merge",
    "detect_copy_paste_drift",
    "validate_env_contract",
]
