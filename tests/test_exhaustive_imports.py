"""Exhaustive Full-Inventory Import Verification Gate (Tier 2).

Verifies 100% clean, non-crashing imports across all modules, packages,
pillars, engines, sentries, and public APIs of Fault-Keeper.
Guarantees zero missing symbols, zero broken submodules, and zero circular imports.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Dict, List, Set, Tuple
import pytest

import fault_keeper as fk
from fault_keeper.core.armor import ArmorViolationError, armored, guard, protect
from fault_keeper.core.facade import FaultKeeper
from fault_keeper.core.mcp.server import MCPDispatcher


def test_top_level_package_exports():
    """Verify top-level package namespace exports all fundamental public symbols."""
    assert hasattr(fk, "FaultKeeper")
    assert hasattr(fk, "MCPDispatcher")
    assert hasattr(fk, "systems")
    assert hasattr(fk, "guard")
    assert hasattr(fk, "protect")
    assert hasattr(fk, "armored")
    assert hasattr(fk, "ArmorViolationError")
    assert hasattr(fk, "__version__")
    assert fk.__version__ == "1.0.0"

    assert callable(fk.guard)
    assert callable(fk.protect)
    assert issubclass(fk.ArmorViolationError, RuntimeError)


def test_core_facade_and_lazy_modules():
    """Verify FaultKeeper singleton facade and lazy property initializers."""
    facade = FaultKeeper()
    assert facade is FaultKeeper()  # Singleton identity

    # Phase 1 Numerical Kernels
    assert hasattr(facade, "num")
    assert hasattr(facade.num, "DualNumber")
    assert hasattr(facade.num, "Fixed128")
    assert hasattr(facade.num, "WelfordAccumulator")
    assert hasattr(facade.num, "SpringDynamicsSolver")

    # Sparse Linear Algebra
    assert hasattr(facade, "sla")
    assert hasattr(facade.sla, "CSRMatrix")
    assert hasattr(facade.sla, "spmv")
    assert hasattr(facade.sla, "randomized_svd")

    # Computational Geometry
    assert hasattr(facade, "geo")
    assert hasattr(facade.geo, "Orient2D")
    assert hasattr(facade.geo, "ShewchukPredicates")
    assert hasattr(facade.geo, "MortonBVH")
    assert hasattr(facade.geo, "convex_hull_monotone_chain")

    # Killer Trio Audits
    assert hasattr(facade, "audit")
    assert hasattr(facade.audit, "ast_merge")
    assert hasattr(facade.audit, "detect_copy_paste_drift")
    assert hasattr(facade.audit, "validate_env_contract")


def test_phase1_module_direct_imports():
    """Verify all Phase 1 foundation mathematical kernels and audit engines."""
    from fault_keeper.num.dual_number import DualNumber
    from fault_keeper.num.fixed128 import Fixed128
    from fault_keeper.num.welford import WelfordAccumulator
    from fault_keeper.num.spring_ode import SpringDynamicsSolver
    from fault_keeper.sla.csr_matrix import CSRMatrix
    from fault_keeper.sla.spmv import spmv
    from fault_keeper.sla.randomized_svd import randomized_svd
    from fault_keeper.geo.shewchuk import ShewchukPredicates
    from fault_keeper.geo.morton_bvh import MortonBVH
    from fault_keeper.geo.convex_hull import convex_hull_monotone_chain
    from fault_keeper.audit.ast_rewrite import ast_merge
    from fault_keeper.audit.anti_unify import detect_copy_paste_drift
    from fault_keeper.audit.env_contract import validate_env_contract

    dn = DualNumber(5.0, 1.0)
    assert dn.real == 5.0
    f128 = Fixed128.from_float(3.14159)
    assert f128 is not None
    welford = WelfordAccumulator()
    welford.update(10.0)
    assert welford.count == 1
    assert callable(spmv)
    assert callable(randomized_svd)
    assert callable(ast_merge)
    assert callable(detect_copy_paste_drift)
    assert callable(validate_env_contract)


def test_phase2_developer_productivity_all_19_pillars_imports():
    """Verify all 19 Phase 2 developer productivity pillars import cleanly."""
    # 1. FT-DSO
    from fault_keeper.daily.ftdso import FlakyTestDeterministicSieve, PermutationSchedule, StateSnapshot
    assert inspect.isclass(FlakyTestDeterministicSieve)
    assert inspect.isclass(PermutationSchedule)

    # 2. Tx-DLO
    from fault_keeper.daily.txdlo import TransactionDeadlockOracle, LockResource, TransactionFlow
    assert inspect.isclass(TransactionDeadlockOracle)
    assert inspect.isclass(LockResource)

    # 3. CDC-ABS
    from fault_keeper.daily.cdcabs import CrossBoundaryContractSentry, BackendEndpointContract, ClientCallSite
    assert inspect.isclass(CrossBoundaryContractSentry)
    assert inspect.isclass(BackendEndpointContract)

    # 4. U-FSR
    from fault_keeper.audit.ufsr import FailureSinkReport, analyse_file as ufsr_analyse_file
    assert inspect.isclass(FailureSinkReport)
    assert callable(ufsr_analyse_file)

    # 5. WPA-HIS
    from fault_keeper.audit.wpahis import ModuleNode, ProjectGraph, analyse_project as wpahis_analyse_project
    assert inspect.isclass(ModuleNode)
    assert callable(wpahis_analyse_project)

    # 6. TC-GTC
    from fault_keeper.num.tc_gtc_timezone import TimezoneDriftDetector, DSTTrapDetector
    assert inspect.isclass(TimezoneDriftDetector)
    assert inspect.isclass(DSTTrapDetector)

    # 7. RDA-NP
    from fault_keeper.num.rdas_redos import RegexComplexityAnalyzer
    assert inspect.isclass(RegexComplexityAnalyzer)

    # 8. CASI-OP
    from fault_keeper.num.cas_i_op_cache import XFetchAlgorithm, StampedePrevention
    assert inspect.isclass(XFetchAlgorithm)
    assert inspect.isclass(StampedePrevention)

    # 9. FSAS
    from fault_keeper.typing.fsas_ghost_cst import GhostCST, GhostCSTParser
    assert inspect.isclass(GhostCST)
    assert inspect.isclass(GhostCSTParser)

    # 10. ATH-BS
    from fault_keeper.typing.ath_byped_hole import TypedHoleSynthesizer, TypeHole
    assert inspect.isclass(TypedHoleSynthesizer)
    assert inspect.isclass(TypeHole)

    # 11. AE-FPS
    from fault_keeper.typing.ae_fps_await_checker import AsyncAwaitLifecycleChecker, MissingAwaitDetector
    assert inspect.isclass(AsyncAwaitLifecycleChecker)
    assert inspect.isclass(MissingAwaitDetector)

    # 12. TWSA
    from fault_keeper.typing.twsa_type_lattice import TypeLatticeAutoComplete, TypeLatticeNode
    assert inspect.isclass(TypeLatticeAutoComplete)
    assert inspect.isclass(TypeLatticeNode)

    # 13. PTHO
    from fault_keeper.workflow.ptho import TestSuitePruner
    assert inspect.isclass(TestSuitePruner)

    # 14. CRCAE
    from fault_keeper.workflow.crcae_root_causal import RootCausalAnalyzer, CausalGraph
    assert inspect.isclass(RootCausalAnalyzer)
    assert inspect.isclass(CausalGraph)

    # 15. LQPC
    from fault_keeper.workflow.lqpc_n_plus_one import NPlusOneQueryDetector
    assert inspect.isclass(NPlusOneQueryDetector)

    # 16. SSDL
    from fault_keeper.workflow.ssdl_dependency_hell import DependencyHellResolver
    assert inspect.isclass(DependencyHellResolver)

    # 17. STAS
    from fault_keeper.workflow.stas_simd_trigram import STASimDTrigramSearcher
    assert inspect.isclass(STASimDTrigramSearcher)

    # 18. GSL-D
    from fault_keeper.workflow.gsl_d_simplex import CSSLayoutSimplexSolver, solve_layout
    assert inspect.isclass(CSSLayoutSimplexSolver)
    assert callable(solve_layout)

    # 19. ZEC-SW
    from fault_keeper.fullstack.zec_sw_migration import MigrationPlan, SchemaVersion, execute_zero_downtime_migration
    assert inspect.isclass(MigrationPlan)
    assert inspect.isclass(SchemaVersion)
    assert callable(execute_zero_downtime_migration)


def test_phase3_systems_all_16_pillars_imports():
    """Verify all 16 Phase 3 Systems Low-Level & Kernel Sentry pillars import cleanly."""
    from fault_keeper import systems

    pillar_descriptors: List[Tuple[str, List[str]]] = [
        ("numa_afs", ["NUMAAFS", "InterconnectStallDetector", "FirstTouchAffinityEnforcer", "NUMAAFSConfig"]),
        ("thp_zsc", ["ZSC_ThP", "DualPoolHybridAllocator", "THPArenaSentry", "ZSCConfig"]),
        ("cache_fs_cco", ["FS_CCO", "StructLayoutAnalyzer", "CacheLineSentry", "FS_CCO_Config"]),
        ("memory_heh_dr", ["HEH_DR", "HazardPointerSystem", "EpochBasedRetirement", "LockFreeAllocator", "HEH_DR_Sentry"]),
        ("layout_apm_rlme", ["APM_RLME", "APM_RLMEConfig", "AoSSoATransposer", "ZeroStallContainer", "APM_RLME_Sentry"]),
        ("hardware_h_tss", ["H_TSS", "H_TSSConfig", "HardwarePointerTagging", "TaggedPointer", "H_TSS_Sentry"]),
        ("leak_dmcs", ["DMCSConfig", "DominatorTree", "MinCutAnalyzer", "DMCS", "DMCS_Sentry"]),
        ("concurrency_tsc", ["TSCA", "TSCAConfig", "SimplicialComplex", "TSCAEngine", "TSCASentry"]),
        ("ordering_cam_ro", ["CAMROConfig", "FenceSynthesizer", "LitmusTest", "CAMROSentry"]),
        ("yield_ac_sbe", ["ACSBEConfig", "AutoYieldTransformer", "BlockingLoopDetector", "ACSBESentry"]),
        ("kernel_ev_ipp", ["EVIPPConfig", "BpfVerifierEngine", "Tnum", "EVIPPSentry"]),
        ("vector_saba", ["SABAConfig", "LoopCarriedDependencyAnalyzer", "VectorLoopSynthesizer", "SABASentry"]),
        ("compile_sc_bbw", ["SCBBWConfig", "ControlFlowGraph", "GraphLaplacianCalculator", "SCBBWSentry"]),
        ("provenance_pt_pafs", ["PTPAFSConfig", "ProvenanceRegistry", "TreeBorrowsStateMachine", "PTPAFSSentry"]),
        ("io_uring_dis_ra", ["DISRAConfig", "IoUringEngine", "RingBuffer", "DISRASentry"]),
        ("binary_md_bbe", ["MDBBEConfig", "PolymorphicThunkDeduplicator", "StructuralABIEquivalenceScanner", "MDBBESentry"]),
    ]

    for mod_name, expected_symbols in pillar_descriptors:
        assert hasattr(systems, mod_name), f"Missing pillar module '{mod_name}' in systems"
        pillar_mod = getattr(systems, mod_name)
        for sym in expected_symbols:
            assert hasattr(pillar_mod, sym), f"Missing symbol '{sym}' in systems.{mod_name}"
            sym_obj = getattr(pillar_mod, sym)
            assert inspect.isclass(sym_obj) or callable(sym_obj), f"Symbol '{sym}' in {mod_name} must be class or callable"


def test_recursive_pkgutil_walk_imports():
    """Dynamically traverse every package and submodule under fault_keeper without error."""
    import fault_keeper
    package_path = fault_keeper.__path__
    
    discovered_modules: List[str] = []
    failed_imports: List[tuple[str, str]] = []

    for _, module_name, is_pkg in pkgutil.walk_packages(package_path, prefix="fault_keeper."):
        discovered_modules.append(module_name)
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None
        except Exception as exc:
            failed_imports.append((module_name, str(exc)))

    assert len(discovered_modules) >= 40, f"Expected at least 40 discovered modules, got {len(discovered_modules)}"
    assert not failed_imports, f"Modules failed to import: {failed_imports}"


def test_cli_import_and_dispatch():
    """Verify Sovereign Standalone CLI entrypoint (`fault_keeper.py`) imports and commands."""
    import importlib.util
    from pathlib import Path
    fk_script_path = Path(__file__).resolve().parent.parent / "fault_keeper.py"
    assert fk_script_path.exists(), "fault_keeper.py must exist at repository root"
    spec = importlib.util.spec_from_file_location("fault_keeper_root", fk_script_path)
    fk_root_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fk_root_mod)
    assert hasattr(fk_root_mod, "main")
    assert hasattr(fk_root_mod, "build_parser")
    fk_parser = fk_root_mod.build_parser()
    assert fk_parser is not None

    # Verify subcommands exist
    subparser_actions = [
        action for action in fk_parser._actions if isinstance(action, fk_root_mod.argparse._SubParsersAction)
    ]
    assert len(subparser_actions) > 0
    choices = subparser_actions[0].choices
    for cmd in ["audit", "test-audit", "diagnose", "solve-merge", "mcp"]:
        assert cmd in choices, f"Missing CLI subcommand: {cmd}"


def test_phase4_group1_armor_imports():
    """Verify Phase 4 Group 1 AI Armor pillars import cleanly."""
    from fault_keeper.armor.asphg import ASPHGEngine, PatchSentry, CandidatePatch
    from fault_keeper.armor.actlo import ACTLOEngine, MucSteeringAdvisor, DefectState
    from fault_keeper.armor.scpve import SCPVEEngine, CoWWorkerPool, ASTArbiter, CoWVFS

    assert inspect.isclass(ASPHGEngine)
    assert inspect.isclass(PatchSentry)
    assert inspect.isclass(ACTLOEngine)
    assert inspect.isclass(MucSteeringAdvisor)
    assert inspect.isclass(SCPVEEngine)
    assert inspect.isclass(CoWWorkerPool)
    assert inspect.isclass(ASTArbiter)
    assert inspect.isclass(CoWVFS)


def test_phase4_group2_mcp_omni_facade_imports():
    """Verify Phase 4 Group 2 MCP Omni-Facade imports cleanly."""
    from fault_keeper.mcp.omni_facade import (
        MCPOmniFacade,
        OmniToolDefinition,
        VirtualResourceProvider,
        get_omni_tools_schema,
        estimate_token_count,
    )
    from fault_keeper.mcp import (
        MCPOmniFacade as FacadeExport,
        OmniToolDefinition as ToolDefExport,
        VirtualResourceProvider as ResourceExport,
        get_omni_tools_schema as SchemaExport,
    )

    assert inspect.isclass(MCPOmniFacade)
    assert inspect.isclass(OmniToolDefinition)
    assert inspect.isclass(VirtualResourceProvider)
    assert callable(get_omni_tools_schema)
    assert callable(estimate_token_count)
    assert FacadeExport is MCPOmniFacade
    assert ToolDefExport is OmniToolDefinition
    assert ResourceExport is VirtualResourceProvider
    assert SchemaExport is get_omni_tools_schema


def test_phase4_deep_tech_formal_methods_all_10_pillars_imports():
    """Verify all 10 Phase 4 AI Armor, Distributed, Time-Travel, and Formal Methods pillars import cleanly.
    
    Test 4.5.5 compliance:
    1. ASP-HG: ASPHGEngine, PatchSentry
    2. ACT-LO: ACTLOEngine, DoomLoopDetector
    3. SC-PVE: SCPVEEngine, CoWWorkerPool
    4. MCP-OFA: MCPOmniFacade, OmniToolDefinition
    5. D-CAS: DCASSimulator, NetworkPacket
    6. CADRE: CADRETimeTravelTracer, ExecutionFrame
    7. CIS3: CIS3SMTSynthesizer, SMTFieldConstraint
    8. DCEG: DCEGDifferentialGraph, CausalNode
    9. SADS: SADSSynthesizer, GrammarProduction
    10. FSLS: FSLSAdjointFunctor, FormalCategoryObject
    """
    # 1. ASP-HG
    from fault_keeper.armor.asphg import ASPHGEngine, PatchSentry
    assert inspect.isclass(ASPHGEngine)
    assert inspect.isclass(PatchSentry)

    # 2. ACT-LO
    from fault_keeper.armor.actlo import ACTLOEngine, DoomLoopDetector
    assert inspect.isclass(ACTLOEngine)
    assert inspect.isclass(DoomLoopDetector)

    # 3. SC-PVE
    from fault_keeper.armor.scpve import SCPVEEngine, CoWWorkerPool
    assert inspect.isclass(SCPVEEngine)
    assert inspect.isclass(CoWWorkerPool)

    # 4. MCP-OFA
    from fault_keeper.mcp.omni_facade import MCPOmniFacade, OmniToolDefinition
    assert inspect.isclass(MCPOmniFacade)
    assert inspect.isclass(OmniToolDefinition)

    # 5. D-CAS
    from fault_keeper.distributed.dcas import DCASSimulator, NetworkPacket
    assert inspect.isclass(DCASSimulator)
    assert inspect.isclass(NetworkPacket)

    # 6. CADRE
    from fault_keeper.timetravel.cadre import CADRETimeTravelTracer, ExecutionFrame
    assert inspect.isclass(CADRETimeTravelTracer)
    assert inspect.isclass(ExecutionFrame)

    # 7. CIS3
    from fault_keeper.formal.cis3 import CIS3SMTSynthesizer, SMTFieldConstraint
    assert inspect.isclass(CIS3SMTSynthesizer)
    assert inspect.isclass(SMTFieldConstraint)

    # 8. DCEG
    from fault_keeper.formal.dceg import DCEGDifferentialGraph, CausalNode
    assert inspect.isclass(DCEGDifferentialGraph)
    assert inspect.isclass(CausalNode)

    # 9. SADS
    from fault_keeper.formal.sads import SADSSynthesizer, GrammarProduction
    assert inspect.isclass(SADSSynthesizer)
    assert inspect.isclass(GrammarProduction)

    # 10. FSLS
    from fault_keeper.formal.fsls import FSLSAdjointFunctor, FormalCategoryObject
    assert inspect.isclass(FSLSAdjointFunctor)
    assert inspect.isclass(FormalCategoryObject)


