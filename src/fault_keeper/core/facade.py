"""FaultKeeper: 1-line Python API & Context Manager with Comprehensive Lazy Loading."""

from __future__ import annotations

import sys
from typing import Any, Optional


class FaultKeeper:
    """Core unified facade for lazy-loading all Fault-Keeper domains and pillars.
    
    Provides 1-line Python ergonomics across all 51 pillars:
    - fk.num: Numerical & Autodiff Kernels (FK-NUM, TC-GTC, RDA-NP, CASI-OP)
    - fk.sla: Sparse Linear Algebra & Latency (FK-SLA, Multi-Hop Latency, Token Bucket)
    - fk.geo: Computational Geometry (FK-GEO Shewchuk, BVH, Monotone Chain)
    - fk.audit: Code Health & Invariants (A-SMW, ACDS, AEC-VS, U-FSR, WPA-HIS)
    - fk.typing: Type Safety & Keystroke (FSAS, ATH-BS, AE-FPS, TWSA)
    - fk.workflow: Developer Workflow (CRCAE, LQPC, SSDL, STAS, PTHO, GSL-D, ZEC-SW)
    - fk.daily: Daily Developer Sentry (FT-DSO, Tx-DLO, CDC-ABS)
    - fk.systems: Hardware & Low-Level Sentries (16 Phase 3 Systems Pillars)
    - fk.armor: AI Agent Speculative Armor (ASP-HG, ACT-LO, SC-PVE)
    - fk.mcp: Cognitive Router & Omni-Facade (MCP-OFA)
    - fk.distributed: Distributed Systems (D-CAS)
    - fk.timetravel: Time-Travel Execution Tracer (CADRE)
    - fk.formal: Formal Verification & Synthesis (CIS3, DCEG, SADS, FSLS)
    """

    _instance: Optional["FaultKeeper"] = None

    def __new__(cls) -> "FaultKeeper":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize lazy-loaded module caches."""
        self._num: Optional[Any] = None
        self._sla: Optional[Any] = None
        self._geo: Optional[Any] = None
        self._audit: Optional[Any] = None
        self._typing: Optional[Any] = None
        self._workflow: Optional[Any] = None
        self._daily: Optional[Any] = None
        self._systems: Optional[Any] = None
        self._armor: Optional[Any] = None
        self._mcp: Optional[Any] = None
        self._distributed: Optional[Any] = None
        self._timetravel: Optional[Any] = None
        self._formal: Optional[Any] = None

    @property
    def num(self) -> Any:
        """Lazy-load numerical and autodiff kernels."""
        if self._num is None:
            from fault_keeper.num import (
                DualNumber,
                Fixed128,
                SpringDynamicsSolver,
                WelfordAccumulator,
            )
            from fault_keeper.num.cas_i_op_cache import StampedePrevention, XFetchAlgorithm
            from fault_keeper.num.rdas_redos import RegexComplexityAnalyzer
            from fault_keeper.num.tc_gtc_timezone import DSTTrapDetector, TimezoneDriftDetector

            self._num = type(
                "NumModule",
                (object,),
                {
                    "DualNumber": DualNumber,
                    "Fixed128": Fixed128,
                    "WelfordAccumulator": WelfordAccumulator,
                    "SpringDynamicsSolver": SpringDynamicsSolver,
                    "XFetchAlgorithm": XFetchAlgorithm,
                    "StampedePrevention": StampedePrevention,
                    "RegexComplexityAnalyzer": RegexComplexityAnalyzer,
                    "TimezoneDriftDetector": TimezoneDriftDetector,
                    "DSTTrapDetector": DSTTrapDetector,
                },
            )()
        return self._num

    @property
    def sla(self) -> Any:
        """Lazy-load sparse linear algebra and SLA latency bounds."""
        if self._sla is None:
            from fault_keeper.sla import CSRMatrix, randomized_svd, spmv
            from fault_keeper.sla.latency_bounds import LatencyBoundComputation, MultiHopLatencyAnalyzer
            from fault_keeper.sla.token_bucket import TokenBucketSimulator, TokenBucketState

            self._sla = type(
                "SLAModule",
                (object,),
                {
                    "CSRMatrix": CSRMatrix,
                    "spmv": staticmethod(spmv),
                    "randomized_svd": staticmethod(randomized_svd),
                    "LatencyBoundComputation": LatencyBoundComputation,
                    "MultiHopLatencyAnalyzer": MultiHopLatencyAnalyzer,
                    "TokenBucketSimulator": TokenBucketSimulator,
                    "TokenBucketState": TokenBucketState,
                },
            )()
        return self._sla

    @property
    def geo(self) -> Any:
        """Lazy-load computational geometry kernels."""
        if self._geo is None:
            from fault_keeper.geo.convex_hull import convex_hull_monotone_chain
            from fault_keeper.geo.morton_bvh import MortonBVH
            from fault_keeper.geo.shewchuk import ShewchukPredicates

            self._geo = type(
                "GeoModule",
                (object,),
                {
                    "Orient2D": staticmethod(ShewchukPredicates.orient2d),
                    "ShewchukPredicates": ShewchukPredicates,
                    "MortonBVH": MortonBVH,
                    "convex_hull_monotone_chain": staticmethod(convex_hull_monotone_chain),
                },
            )()
        return self._geo

    @property
    def audit(self) -> Any:
        """Lazy-load code health and invariant audit modules."""
        if self._audit is None:
            from fault_keeper.audit import (
                ast_merge,
                detect_copy_paste_drift,
                validate_env_contract,
            )
            from fault_keeper.audit.ufsr import FailureSinkReport, analyse_file
            from fault_keeper.audit.wpahis import ModuleNode, ProjectGraph, analyse_project

            self._audit = type(
                "AuditModule",
                (object,),
                {
                    "ast_merge": staticmethod(ast_merge),
                    "detect_copy_paste_drift": staticmethod(detect_copy_paste_drift),
                    "validate_env_contract": staticmethod(validate_env_contract),
                    "analyse_file": staticmethod(analyse_file),
                    "FailureSinkReport": FailureSinkReport,
                    "analyse_project": staticmethod(analyse_project),
                    "ModuleNode": ModuleNode,
                    "ProjectGraph": ProjectGraph,
                },
            )()
        return self._audit

    @property
    def typing(self) -> Any:
        """Lazy-load inner-loop typing and keystroke intelligence modules."""
        if self._typing is None:
            from fault_keeper.typing.ae_fps_await_checker import AsyncAwaitLifecycleChecker
            from fault_keeper.typing.ath_byped_hole import TypeHole, TypedHoleSynthesizer
            from fault_keeper.typing.fsas_ghost_cst import GhostCST, GhostCSTParser
            from fault_keeper.typing.twsa_type_lattice import TWSAAutoComplete, TypeLatticeNode

            self._typing = type(
                "TypingModule",
                (object,),
                {
                    "GhostCST": GhostCST,
                    "GhostCSTParser": GhostCSTParser,
                    "TypedHoleSynthesizer": TypedHoleSynthesizer,
                    "TypeHole": TypeHole,
                    "AsyncAwaitLifecycleChecker": AsyncAwaitLifecycleChecker,
                    "TWSAAutoComplete": TWSAAutoComplete,
                    "TypeLatticeNode": TypeLatticeNode,
                },
            )()
        return self._typing

    @property
    def workflow(self) -> Any:
        """Lazy-load developer productivity and root-causal engines."""
        if self._workflow is None:
            from fault_keeper.fullstack.gsl_d_simplex import SimplexSolver, fix_horizontal_overflow
            from fault_keeper.fullstack.zec_sw_migration import MigrationPlan, ZeroDowntimeMigrationEngine
            from fault_keeper.workflow.crcae_root_causal import CausalGraph, StructuralCausalAbduction
            from fault_keeper.workflow.lqpc_n_plus_one import NPlusOneQueryDetector
            from fault_keeper.workflow.ptho import ImpactGraphBuilder
            from fault_keeper.workflow.ssdl_dependency_hell import DependencyConflictDetector, PublicAPISlicer
            from fault_keeper.workflow.stas_simd_trigram import TrigramIndex

            self._workflow = type(
                "WorkflowModule",
                (object,),
                {
                    "CausalGraph": CausalGraph,
                    "StructuralCausalAbduction": StructuralCausalAbduction,
                    "NPlusOneQueryDetector": NPlusOneQueryDetector,
                    "ImpactGraphBuilder": ImpactGraphBuilder,
                    "DependencyConflictDetector": DependencyConflictDetector,
                    "PublicAPISlicer": PublicAPISlicer,
                    "TrigramIndex": TrigramIndex,
                    "SimplexSolver": SimplexSolver,
                    "fix_horizontal_overflow": staticmethod(fix_horizontal_overflow),
                    "ZeroDowntimeMigrationEngine": ZeroDowntimeMigrationEngine,
                    "MigrationPlan": MigrationPlan,
                },
            )()
        return self._workflow

    @property
    def daily(self) -> Any:
        """Lazy-load daily developer trap and sentry modules (FT-DSO, Tx-DLO, CDC-ABS)."""
        if self._daily is None:
            from fault_keeper.daily.cdcabs import CrossBoundaryContractSentry
            from fault_keeper.daily.ftdso import FlakyTestDeterministicSieve
            from fault_keeper.daily.txdlo import TransactionDeadlockOracle

            self._daily = type(
                "DailyModule",
                (object,),
                {
                    "FlakyTestDeterministicSieve": FlakyTestDeterministicSieve,
                    "TransactionDeadlockOracle": TransactionDeadlockOracle,
                    "CrossBoundaryContractSentry": CrossBoundaryContractSentry,
                },
            )()
        return self._daily

    @property
    def systems(self) -> Any:
        """Lazy-load low-level hardware & kernel sentries (Phase 3)."""
        if self._systems is None:
            from fault_keeper import systems as sys_pkg
            self._systems = sys_pkg
        return self._systems

    @property
    def armor(self) -> Any:
        """Lazy-load AI Agent Speculative Armor (ASP-HG, ACT-LO, SC-PVE)."""
        if self._armor is None:
            from fault_keeper.armor.actlo import ACTLOEngine, DefectState, DoomLoopDetector
            from fault_keeper.armor.asphg import ASPHGEngine, PatchSentry
            from fault_keeper.armor.scpve import CoWWorkerPool, SCPVEEngine

            self._armor = type(
                "ArmorModule",
                (object,),
                {
                    "ASPHGEngine": ASPHGEngine,
                    "PatchSentry": PatchSentry,
                    "ACTLOEngine": ACTLOEngine,
                    "DoomLoopDetector": DoomLoopDetector,
                    "DefectState": DefectState,
                    "SCPVEEngine": SCPVEEngine,
                    "CoWWorkerPool": CoWWorkerPool,
                },
            )()
        return self._armor

    @property
    def mcp(self) -> Any:
        """Lazy-load MCP Omni-Facade & Adaptive Capability Arbiter."""
        if self._mcp is None:
            from fault_keeper.mcp.omni_facade import MCPOmniFacade, OmniToolDefinition, VirtualResourceProvider
            self._mcp = type(
                "MCPModule",
                (object,),
                {
                    "MCPOmniFacade": MCPOmniFacade,
                    "OmniToolDefinition": OmniToolDefinition,
                    "VirtualResourceProvider": VirtualResourceProvider,
                },
            )()
        return self._mcp

    @property
    def distributed(self) -> Any:
        """Lazy-load Distributed Chaos Simulator (D-CAS)."""
        if self._distributed is None:
            from fault_keeper.distributed.dcas import DCASSimulator, NetworkPacket, NodeState
            self._distributed = type(
                "DistributedModule",
                (object,),
                {
                    "DCASSimulator": DCASSimulator,
                    "NetworkPacket": NetworkPacket,
                    "NodeState": NodeState,
                },
            )()
        return self._distributed

    @property
    def timetravel(self) -> Any:
        """Lazy-load Time-Travel Execution Tracer (CADRE)."""
        if self._timetravel is None:
            from fault_keeper.timetravel.cadre import CADRETimeTravelTracer, CheckpointSnapshot, ExecutionFrame
            self._timetravel = type(
                "TimeTravelModule",
                (object,),
                {
                    "CADRETimeTravelTracer": CADRETimeTravelTracer,
                    "ExecutionFrame": ExecutionFrame,
                    "CheckpointSnapshot": CheckpointSnapshot,
                },
            )()
        return self._timetravel

    @property
    def formal(self) -> Any:
        """Lazy-load Formal Verification & Mathematical Synthesis engines (CIS3, DCEG, SADS, FSLS)."""
        if self._formal is None:
            from fault_keeper.formal.cis3 import CIS3SMTSynthesizer, SMTFieldConstraint
            from fault_keeper.formal.dceg import CausalNode, DCEGDifferentialGraph
            from fault_keeper.formal.fsls import FSLSAdjointFunctor, FormalCategoryObject
            from fault_keeper.formal.sads import GrammarProduction, SADSSynthesizer

            self._formal = type(
                "FormalModule",
                (object,),
                {
                    "CIS3SMTSynthesizer": CIS3SMTSynthesizer,
                    "SMTFieldConstraint": SMTFieldConstraint,
                    "DCEGDifferentialGraph": DCEGDifferentialGraph,
                    "CausalNode": CausalNode,
                    "SADSSynthesizer": SADSSynthesizer,
                    "GrammarProduction": GrammarProduction,
                    "FSLSAdjointFunctor": FSLSAdjointFunctor,
                    "FormalCategoryObject": FormalCategoryObject,
                },
            )()
        return self._formal

    def __enter__(self) -> "FaultKeeper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        pass


def get_fault_keeper() -> FaultKeeper:
    """Get singleton FaultKeeper instance."""
    return FaultKeeper()