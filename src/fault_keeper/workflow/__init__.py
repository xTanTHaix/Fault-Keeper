"""Workflow and Daily Developer Tools Module — Phase 2.

Pillars in this package: TC-GTC, RDA-NP, CASI-OP, PTHO, CRCAE, LQPC, SSDL, STAS.
Submodules are loaded lazily on first attribute access to keep the package import
cheap and avoid pulling every tool into memory up front.  Loading is performed via
``importlib.import_module`` which automatically registers modules under ``sys.modules``
without direct mutation (compliant with LIPA best practices).
"""

from __future__ import annotations

import os as _os_path


def _load_submodule(sub_name: str) -> object:
    """Load a sibling submodule by its short name using standard import machinery.

    The module is loaded via ``importlib.import_module`` which:
    - Automatically registers the module under sys.modules without direct mutation
    - Returns the fully-loaded module object ready for use
    - Handles circular imports gracefully through PEP-302/PEP-451 spec loading

    Args:
        sub_name: Short name of submodule (e.g., 'stas', 'tc_gtc').

    Returns:
        Fully loaded module object.

    Raises:
        ImportError: If the submodule cannot be found or loaded.
    """
    full_name = f"fault_keeper.workflow.{sub_name}"
    
    try:
        # Use standard import machinery which handles registration automatically
        return __import__(full_name, fromlist=[''])  # type: ignore[call-overload]
    except ImportError as e:
        raise ImportError(f"cannot load workflow submodule {full_name!r}") from e


_SUBMODULES: list[str] = ["tc_gtc", "rda_np", "casi_op", "ptho", "crcae", "lqpc", "ssdl", "stas"]


def __getattr__(name: str) -> object:
    """Lazy-load a workflow submodule by short name."""
    if name in _SUBMODULES:
        return _load_submodule(name)  # type: ignore[return-value]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__: list[str] = [
    "tc_gtc",
    "rda_np",
    "casi_op",
    "ptho",
    "crcae",
    "lqpc",
    "ssdl",
    "stas",
]
