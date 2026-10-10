"""CDC-ABS: Cross-Boundary Contract & API Breaking-Change Sentry.

Performs static zero-E2E cross-boundary verification between backend route
handlers/DTOs and frontend client call-sites:
1. Dual-Border AST Harvester: Extracts backend routes and Pydantic/TypedDict/DTO
   schemas alongside client fetch/axios property access chains pi_client(E).
2. Unified Cross-Boundary Route Matcher: Normalizes URL path templates across
   FastAPI, Flask, Express, and TypeScript template literals.
3. Structural Subtyping Covariance Verifier: Enforces response width/depth
   covariance tau_new(f) <=_sub tau_client(f) and detects Nullability Drift.
4. Client Inhabitation Quotient: Computes Q_inhabit(Delta_schema) to suppress
   false-positive alerts when deleting unused dead fields.
"""

from __future__ import annotations

import ast
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SchemaField:
    """Represents a single field in a backend or client API schema."""

    name: str
    type_name: str
    nullable: bool = False
    required: bool = True
    lineno: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize schema field to a dictionary."""
        return {
            "name": self.name,
            "type_name": self.type_name,
            "nullable": self.nullable,
            "required": self.required,
            "lineno": self.lineno,
        }


@dataclass
class BackendEndpointContract:
    """Backend route contract harvested from AST or DTO declarations."""

    method: str
    path: str
    normalized_path: str
    handler_name: str
    response_schema: Dict[str, SchemaField] = field(default_factory=dict)
    request_schema: Dict[str, SchemaField] = field(default_factory=dict)
    file_path: str = "<backend>"
    lineno: int = 1

    @property
    def endpoint_key(self) -> str:
        """Return canonical METHOD + normalized_path key."""
        return f"{self.method.upper()} {self.normalized_path}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize backend endpoint contract to a dictionary."""
        return {
            "method": self.method.upper(),
            "path": self.path,
            "normalized_path": self.normalized_path,
            "handler_name": self.handler_name,
            "response_schema": {
                k: v.to_dict() for k, v in self.response_schema.items()
            },
            "request_schema": {
                k: v.to_dict() for k, v in self.request_schema.items()
            },
            "file_path": self.file_path,
            "lineno": self.lineno,
        }


@dataclass(frozen=True)
class ClientFieldProjection:
    """Single field accessed by a frontend/client call-site in pi_client(E)."""

    field_name: str
    expected_type: str = "any"
    null_safe: bool = False
    file_path: str = "<client>"
    lineno: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize client field projection to a dictionary."""
        return {
            "field_name": self.field_name,
            "expected_type": self.expected_type,
            "null_safe": self.null_safe,
            "file_path": self.file_path,
            "lineno": self.lineno,
        }


@dataclass
class ClientCallSite:
    """Client HTTP call-site and its projected response fields pi_client(E)."""

    method: str
    url_path: str
    normalized_path: str
    projected_fields: Dict[str, ClientFieldProjection] = field(default_factory=dict)
    request_fields: Dict[str, str] = field(default_factory=dict)
    file_path: str = "<client>"
    lineno: int = 1

    @property
    def endpoint_key(self) -> str:
        """Return canonical METHOD + normalized_path key."""
        return f"{self.method.upper()} {self.normalized_path}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize client call-site to a dictionary."""
        return {
            "method": self.method.upper(),
            "url_path": self.url_path,
            "normalized_path": self.normalized_path,
            "projected_fields": {
                k: v.to_dict() for k, v in self.projected_fields.items()
            },
            "request_fields": dict(self.request_fields),
            "file_path": self.file_path,
            "lineno": self.lineno,
        }


@dataclass
class BreakingChangeViolation:
    """Detailed record of a cross-boundary contract violation."""

    endpoint: str
    field_name: str
    violation_kind: str  # "FIELD_REMOVED", "TYPE_MISMATCH", "NULLABILITY_DRIFT", "REQUEST_CONTRAVARIANCE"
    backend_type: str
    client_expected_type: str
    backend_file: str
    backend_lineno: int
    client_file: str
    client_lineno: int
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize breaking change violation to a dictionary."""
        return {
            "endpoint": self.endpoint,
            "field_name": self.field_name,
            "violation_kind": self.violation_kind,
            "backend_type": self.backend_type,
            "client_expected_type": self.client_expected_type,
            "backend_file": self.backend_file,
            "backend_lineno": self.backend_lineno,
            "client_file": self.client_file,
            "client_lineno": self.client_lineno,
            "message": self.message,
        }


@dataclass
class ContractVerificationReport:
    """Result of static cross-boundary contract verification."""

    phi_break: bool
    inhabitation_quotient: float
    suppression_ratio: float
    violations: List[BreakingChangeViolation] = field(default_factory=list)
    suppressed_dead_fields: List[str] = field(default_factory=list)
    matched_endpoints: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize contract verification report to a dictionary."""
        return {
            "phi_break": self.phi_break,
            "inhabitation_quotient": round(self.inhabitation_quotient, 6),
            "suppression_ratio": round(self.suppression_ratio, 6),
            "violations": [v.to_dict() for v in self.violations],
            "suppressed_dead_fields": list(self.suppressed_dead_fields),
            "matched_endpoints": list(self.matched_endpoints),
            "elapsed_ms": round(self.elapsed_ms, 4),
        }


# ---------------------------------------------------------------------------
# 1. Unified Cross-Boundary Route Matcher
# ---------------------------------------------------------------------------

_DOMAIN_PREFIX_RE = re.compile(r"^https?://[^/]+", re.IGNORECASE)
_PARAM_PATTERNS = [
    re.compile(r"\$\{[^}]+\}"),          # JS template literal: ${userId}
    re.compile(r"\{[a-zA-Z0-9_:.-]+\}"), # FastAPI/OpenAPI: {id} or {id:int}
    re.compile(r"<[^>]+>"),              # Flask/Werkzeug: <int:id>
    re.compile(r"(?<=/):[a-zA-Z_][a-zA-Z0-9_]*"),  # Express: /:id
]


def normalize_route_path(raw_path: str) -> str:
    """Normalize backend and frontend route paths into a canonical template.

    Replaces language-specific path parameter syntax (`{id}`, `${userId}`,
    `<int:id>`, `:id`) with `{param}` and strips scheme/host and query strings.

    Args:
        raw_path: Raw route string from backend decorator or client fetch URL.

    Returns:
        Canonical route path starting with `/` (e.g., `/api/users/{param}`).
    """
    path = raw_path.strip().strip("'\"`")
    path = _DOMAIN_PREFIX_RE.sub("", path)
    if "?" in path:
        path = path.split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    for pat in _PARAM_PATTERNS:
        path = pat.sub("{param}", path)
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path


# ---------------------------------------------------------------------------
# 2. Structural Subtyping Lattice & Nullability Resolver
# ---------------------------------------------------------------------------

_TYPE_ALIASES: Dict[str, str] = {
    "str": "string",
    "string": "string",
    "int": "int",
    "integer": "int",
    "float": "float",
    "number": "float",
    "double": "float",
    "decimal": "float",
    "bool": "bool",
    "boolean": "bool",
    "list": "list",
    "array": "list",
    "sequence": "list",
    "dict": "dict",
    "mapping": "dict",
    "object": "dict",
    "record": "dict",
    "any": "any",
    "unknown": "any",
}


def parse_type_annotation(raw_type: str) -> Tuple[str, bool]:
    """Parse a Python or TypeScript type annotation into (base_type, is_nullable).

    Handles `Optional[str]`, `str | None`, `Union[int, None]`, `string | null`,
    `string | undefined`, and `?string`.

    Args:
        raw_type: Type string from AST or TypeScript interface.

    Returns:
        Tuple of (canonical_base_type, is_nullable).
    """
    cleaned = raw_type.strip()
    nullable = False

    # Optional[...] wrapper
    opt_match = re.match(r"^(?:typing\.)?Optional\[(.+)\]$", cleaned)
    if opt_match:
        nullable = True
        cleaned = opt_match.group(1).strip()

    # Union[..., None] wrapper
    union_match = re.match(r"^(?:typing\.)?Union\[(.+)\]$", cleaned)
    if union_match:
        parts = [p.strip() for p in union_match.group(1).split(",")]
        non_null = [
            p for p in parts if p.lower() not in ("none", "null", "undefined", "nonetype")
        ]
        if len(non_null) < len(parts):
            nullable = True
        cleaned = non_null[0] if non_null else "none"

    # Pipe union: `str | None` or `string | null | undefined`
    if "|" in cleaned:
        parts = [p.strip() for p in cleaned.split("|")]
        non_null = [
            p for p in parts if p.lower() not in ("none", "null", "undefined", "nonetype")
        ]
        if len(non_null) < len(parts):
            nullable = True
        cleaned = non_null[0] if non_null else "none"

    if cleaned.startswith("?"):
        nullable = True
        cleaned = cleaned[1:].strip()

    # Strip generic container parameters like list[int] -> list
    base_token = cleaned.split("[", 1)[0].strip().lower()
    if base_token.endswith("[]"):
        base_token = "list"

    canonical = _TYPE_ALIASES.get(base_token, base_token)
    return canonical, nullable


def is_structural_subtype(
    sub_type: str,
    super_type: str,
    sub_nullable: bool = False,
    super_nullable: bool = False,
) -> bool:
    """Verify whether (sub_type, sub_nullable) <=_sub (super_type, super_nullable).

    Enforces:
    - Nullability soundness: A nullable type cannot be a subtype of a non-nullable
      type (prevents Nullability Drift).
    - Numeric tower covariance: `int <=_sub float` (`number`).
    - Top type: Any type is a subtype of `any` (provided nullability is respected).

    Args:
        sub_type: New backend field type name.
        super_type: Client expected field type name.
        sub_nullable: Whether the backend field can be None/null.
        super_nullable: Whether the client handles None/null safely.

    Returns:
        True if the subtype relation holds; False otherwise.
    """
    c_sub, parsed_sub_null = parse_type_annotation(sub_type)
    c_sup, parsed_sup_null = parse_type_annotation(super_type)

    effective_sub_null = sub_nullable or parsed_sub_null
    effective_sup_null = super_nullable or parsed_sup_null

    if effective_sub_null and not effective_sup_null:
        return False

    if c_sup == "any" or c_sub == c_sup:
        return True

    # int is a subtype of float/number across JSON serialization boundaries
    if c_sub == "int" and c_sup == "float":
        return True

    return False


# ---------------------------------------------------------------------------
# 3. Dual-Border AST Harvester (Backend & Client)
# ---------------------------------------------------------------------------

def _ast_annotation_to_str(node: Optional[ast.AST]) -> str:
    """Convert a Python AST type annotation node to a string representation."""
    if node is None:
        return "any"
    if hasattr(ast, "unparse"):
        return ast.unparse(node)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return str(node.value)
    return "any"


def harvest_backend_contracts(
    source_code: str,
    file_path: str = "<backend>",
) -> List[BackendEndpointContract]:
    """Harvest backend route contracts and DTO/Pydantic schemas from source code.

    Supports FastAPI/Flask route decorators (`@app.get("/path", response_model=...)`),
    return type annotations (`-> UserResponse`), inline dictionary returns, and
    Pydantic `BaseModel` / `TypedDict` / `@dataclass` class definitions.

    Args:
        source_code: Backend Python source code.
        file_path: File path for diagnostic reporting.

    Returns:
        List of BackendEndpointContract instances.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    # Step 1: Harvest all class-based DTO schemas (Pydantic BaseModel, TypedDict, dataclass)
    dto_schemas: Dict[str, Dict[str, SchemaField]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            fields_map: Dict[str, SchemaField] = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fname = item.target.id
                    raw_ann = _ast_annotation_to_str(item.annotation)
                    base_t, is_null = parse_type_annotation(raw_ann)
                    required = item.value is None or (
                        isinstance(item.value, ast.Constant)
                        and item.value.value is Ellipsis
                    )
                    fields_map[fname] = SchemaField(
                        name=fname,
                        type_name=base_t,
                        nullable=is_null,
                        required=required,
                        lineno=getattr(item, "lineno", node.lineno),
                    )
            dto_schemas[node.name] = fields_map

    # Step 2: Harvest route handler functions decorated with @app.<method> or @router.<method>
    contracts: List[BackendEndpointContract] = []
    http_methods = {"get", "post", "put", "delete", "patch"}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue

            method_name = ""
            if isinstance(dec.func, ast.Attribute) and dec.func.attr.lower() in http_methods:
                method_name = dec.func.attr.upper()
            elif isinstance(dec.func, ast.Name) and dec.func.id.lower() in http_methods:
                method_name = dec.func.id.upper()

            if not method_name or not dec.args:
                continue

            first_arg = dec.args[0]
            if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                continue

            raw_path = first_arg.value
            norm_path = normalize_route_path(raw_path)

            # Determine response schema from response_model=... or return annotation
            resp_schema: Dict[str, SchemaField] = {}
            req_schema: Dict[str, SchemaField] = {}

            for kw in dec.keywords:
                if kw.arg == "response_model" and isinstance(kw.value, ast.Name):
                    model_name = kw.value.id
                    if model_name in dto_schemas:
                        resp_schema = dict(dto_schemas[model_name])

            if not resp_schema and node.returns is not None:
                ret_name = _ast_annotation_to_str(node.returns)
                if ret_name in dto_schemas:
                    resp_schema = dict(dto_schemas[ret_name])

            # Inspect function parameters for request DTO models
            for arg in node.args.args:
                if arg.annotation is not None:
                    ann_name = _ast_annotation_to_str(arg.annotation)
                    if ann_name in dto_schemas:
                        req_schema.update(dto_schemas[ann_name])

            # Fallback: inspect return dict literals inside the route function body
            if not resp_schema:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Dict):
                        for k_node, v_node in zip(sub.value.keys, sub.value.values):
                            if isinstance(k_node, ast.Constant) and isinstance(k_node.value, str):
                                key_name = k_node.value
                                val_type = "any"
                                is_null = False
                                if isinstance(v_node, ast.Constant):
                                    if v_node.value is None:
                                        val_type = "any"
                                        is_null = True
                                    elif isinstance(v_node.value, bool):
                                        val_type = "bool"
                                    elif isinstance(v_node.value, int):
                                        val_type = "int"
                                    elif isinstance(v_node.value, float):
                                        val_type = "float"
                                    elif isinstance(v_node.value, str):
                                        val_type = "string"
                                resp_schema[key_name] = SchemaField(
                                    name=key_name,
                                    type_name=val_type,
                                    nullable=is_null,
                                    lineno=getattr(v_node, "lineno", node.lineno),
                                )

            contracts.append(
                BackendEndpointContract(
                    method=method_name,
                    path=raw_path,
                    normalized_path=norm_path,
                    handler_name=node.name,
                    response_schema=resp_schema,
                    request_schema=req_schema,
                    file_path=file_path,
                    lineno=node.lineno,
                )
            )

    return contracts


_TS_INTERFACE_RE = re.compile(
    r"interface\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\{([^}]+)\}",
    re.MULTILINE | re.DOTALL,
)
_TS_FIELD_RE = re.compile(
    r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)(\?)?\s*:\s*([^;\n]+)",
    re.MULTILINE,
)
_CLIENT_CALL_RE = re.compile(
    r"(?:fetch|axios\.(get|post|put|delete|patch)|client\.(get|post|put|delete|patch)|requests\.(get|post|put|delete|patch))"
    r"(?:<([a-zA-Z_][a-zA-Z0-9_]*)>)?\s*\(\s*([`'\"][^`'\"]+[`'\"])",
    re.IGNORECASE,
)


def harvest_client_callsites(
    source_code: str,
    file_path: str = "<client>",
) -> List[ClientCallSite]:
    """Harvest frontend/client API call-sites and field projections pi_client(E).

    Supports both TypeScript/JavaScript (`fetch`, `axios.get<T>`, property
    access chains `data.email`, optional chaining `data?.email`, TS interfaces)
    and Python client code.

    Args:
        source_code: Client source code (TypeScript, JavaScript, or Python).
        file_path: Source file path for diagnostic provenance.

    Returns:
        List of ClientCallSite instances with projected fields and line numbers.
    """
    lines = source_code.splitlines()

    # Step 1: Parse TypeScript interfaces if present
    ts_interfaces: Dict[str, Dict[str, Tuple[str, bool, int]]] = {}
    for match in _TS_INTERFACE_RE.finditer(source_code):
        iface_name = match.group(1)
        body_text = match.group(2)
        base_line = source_code[: match.start()].count("\n") + 1
        fields_info: Dict[str, Tuple[str, bool, int]] = {}
        for fmatch in _TS_FIELD_RE.finditer(body_text):
            fname = fmatch.group(1)
            opt_q = fmatch.group(2) is not None
            raw_t = fmatch.group(3).strip()
            canon_t, is_null = parse_type_annotation(raw_t)
            f_line = base_line + body_text[: fmatch.start()].count("\n")
            fields_info[fname] = (canon_t, opt_q or is_null, f_line)
        ts_interfaces[iface_name] = fields_info

    # Step 2: Locate fetch / axios / client / requests call-sites
    callsites: List[ClientCallSite] = []
    for match in _CLIENT_CALL_RE.finditer(source_code):
        method_group = match.group(1) or match.group(2) or match.group(3)
        method = method_group.upper() if method_group else "GET"
        generic_type = match.group(4)
        raw_url = match.group(5).strip("`'\"")
        call_lineno = source_code[: match.start()].count("\n") + 1

        # Check if fetch options specify method: 'POST' etc. on the same line
        call_line_text = lines[call_lineno - 1] if call_lineno <= len(lines) else ""
        method_override = re.search(
            r"method\s*:\s*['\"](GET|POST|PUT|DELETE|PATCH)['\"]",
            call_line_text,
            re.IGNORECASE,
        )
        if method_override:
            method = method_override.group(1).upper()

        norm_path = normalize_route_path(raw_url)
        projections: Dict[str, ClientFieldProjection] = {}

        if generic_type and generic_type in ts_interfaces:
            for fname, (ftype, is_null, fline) in ts_interfaces[generic_type].items():
                projections[fname] = ClientFieldProjection(
                    field_name=fname,
                    expected_type=ftype,
                    null_safe=is_null,
                    file_path=file_path,
                    lineno=fline,
                )

        callsites.append(
            ClientCallSite(
                method=method,
                url_path=raw_url,
                normalized_path=norm_path,
                projected_fields=projections,
                file_path=file_path,
                lineno=call_lineno,
            )
        )

    if not callsites:
        return []

    # Step 3: Harvest property access chains (e.g. data.email, user.email, data["email"])
    # and associate with the active call-site in scope.
    prop_access_re = re.compile(
        r"\b(?:data|res|response|payload|user|item|body|json|result)"
        r"(\?)?\.(?!json\b|then\b|catch\b|get\b|post\b|put\b|delete\b)"
        r"([a-zA-Z_][a-zA-Z0-9_]*)"
        r"(\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*))?"
    )
    dict_access_re = re.compile(
        r"\b(?:data|res|response|payload|user|item|body|json|result)"
        r"\[\s*['\"]([a-zA-Z_][a-zA-Z0-9_]*)['\"]\s*\]"
    )
    safe_get_re = re.compile(
        r"\b(?:data|res|response|payload|user|item|body|json|result)"
        r"\.get\(\s*['\"]([a-zA-Z_][a-zA-Z0-9_]*)['\"]"
    )

    string_methods = {
        "toLowerCase",
        "toUpperCase",
        "trim",
        "split",
        "slice",
        "startsWith",
        "endsWith",
        "includes",
        "replace",
        "lower",
        "upper",
        "strip",
    }
    number_methods = {"toFixed", "toPrecision"}
    array_methods = {"map", "filter", "reduce", "forEach", "length"}

    for line_idx, line_text in enumerate(lines, start=1):
        # Find the nearest preceding call-site
        target_site = callsites[0]
        for cs in callsites:
            if cs.lineno <= line_idx:
                target_site = cs

        for pm in prop_access_re.finditer(line_text):
            opt_chain = pm.group(1) == "?"
            fname = pm.group(2)
            chained_method = pm.group(4)

            inferred_type = "any"
            if chained_method in string_methods:
                inferred_type = "string"
            elif chained_method in number_methods:
                inferred_type = "float"
            elif chained_method in array_methods:
                inferred_type = "list"

            existing = target_site.projected_fields.get(fname)
            final_type = (
                existing.expected_type
                if existing and existing.expected_type != "any"
                else inferred_type
            )
            target_site.projected_fields[fname] = ClientFieldProjection(
                field_name=fname,
                expected_type=final_type,
                null_safe=opt_chain,
                file_path=file_path,
                lineno=line_idx,
            )

        for dm in dict_access_re.finditer(line_text):
            fname = dm.group(1)
            existing = target_site.projected_fields.get(fname)
            target_site.projected_fields[fname] = ClientFieldProjection(
                field_name=fname,
                expected_type=existing.expected_type if existing else "any",
                null_safe=False,
                file_path=file_path,
                lineno=line_idx,
            )

        for sm in safe_get_re.finditer(line_text):
            fname = sm.group(1)
            existing = target_site.projected_fields.get(fname)
            target_site.projected_fields[fname] = ClientFieldProjection(
                field_name=fname,
                expected_type=existing.expected_type if existing else "any",
                null_safe=True,
                file_path=file_path,
                lineno=line_idx,
            )

    return callsites


# ---------------------------------------------------------------------------
# 4. Client Inhabitation Quotient & Breaking-Change Verifier
# ---------------------------------------------------------------------------

def compute_inhabitation_quotient(
    schema_delta_fields: Set[str],
    client_projected_fields: Set[str],
) -> Tuple[float, float]:
    """Compute the Client Inhabitation Quotient Q_inhabit and Suppression Ratio.

    Formula:
        Q_inhabit(Delta_schema) = |Delta_schema intersect pi_client| / |Delta_schema|
        SuppressionRatio = 1.0 - Q_inhabit(Delta_schema)

    When a backend deletes or alters fields that have zero overlap with client
    projections (Q_inhabit == 0.0), SuppressionRatio == 1.0 (zero false alerts).

    Args:
        schema_delta_fields: Set of field names modified or removed in backend.
        client_projected_fields: Set of field names accessed by the client AST.

    Returns:
        Tuple of (inhabitation_quotient, suppression_ratio).
    """
    if not schema_delta_fields:
        return 0.0, 1.0
    inhabited = schema_delta_fields & client_projected_fields
    q_inhabit = len(inhabited) / float(len(schema_delta_fields))
    suppression = 1.0 - q_inhabit
    return q_inhabit, suppression


def verify_cross_boundary_contracts(
    backend_contracts: Sequence[BackendEndpointContract],
    client_callsites: Sequence[ClientCallSite],
    old_backend_contracts: Optional[Sequence[BackendEndpointContract]] = None,
) -> ContractVerificationReport:
    """Evaluate the Cross-Boundary Breaking Change Predicate Phi_break.

    Matches backend route handlers against frontend call-sites and checks:
    1. Field Removal: Any f in pi_client(E) missing from Fields(S_new).
    2. Structural Subtyping Covariance: tau_new(f) <=_sub tau_client(f).
    3. Nullability Drift: Field becomes nullable in S_new while client accesses
       it without null-safety guards.
    4. Dead-Field Pruning Suppression: Fields removed from S_old that are not in
       pi_client(E) yield Q_inhabit == 0 and are suppressed from breaking alerts.

    Args:
        backend_contracts: Current (new) backend endpoint contracts.
        client_callsites: Harvested client call-sites and projections.
        old_backend_contracts: Optional baseline backend contracts prior to change.

    Returns:
        ContractVerificationReport detailing Phi_break, Q_inhabit, and violations.
    """
    start_ns = time.perf_counter_ns()

    backend_by_key: Dict[str, BackendEndpointContract] = {
        bc.endpoint_key: bc for bc in backend_contracts
    }
    old_by_key: Dict[str, BackendEndpointContract] = (
        {bc.endpoint_key: bc for bc in old_backend_contracts}
        if old_backend_contracts
        else {}
    )

    violations: List[BreakingChangeViolation] = []
    suppressed_dead_fields: List[str] = []
    matched_endpoints: List[str] = []

    all_delta_fields: Set[str] = set()
    all_client_fields: Set[str] = set()

    for callsite in client_callsites:
        ekey = callsite.endpoint_key
        backend = backend_by_key.get(ekey)
        if backend is None:
            continue

        if ekey not in matched_endpoints:
            matched_endpoints.append(ekey)

        old_backend = old_by_key.get(ekey)
        new_fields = backend.response_schema
        client_projs = callsite.projected_fields
        all_client_fields.update(client_projs.keys())

        # Determine schema delta if old contract is available
        if old_backend is not None:
            old_fields = old_backend.response_schema
            for fname, old_f in old_fields.items():
                if fname not in new_fields:
                    all_delta_fields.add(fname)
                    if fname not in client_projs:
                        suppressed_dead_fields.append(fname)
                else:
                    new_f = new_fields[fname]
                    if (
                        new_f.type_name != old_f.type_name
                        or new_f.nullable != old_f.nullable
                    ):
                        all_delta_fields.add(fname)

        # Verify every client-projected field against S_new
        for fname, proj in client_projs.items():
            if fname not in new_fields:
                all_delta_fields.add(fname)
                violations.append(
                    BreakingChangeViolation(
                        endpoint=ekey,
                        field_name=fname,
                        violation_kind="FIELD_REMOVED",
                        backend_type="<missing>",
                        client_expected_type=proj.expected_type,
                        backend_file=backend.file_path,
                        backend_lineno=backend.lineno,
                        client_file=proj.file_path,
                        client_lineno=proj.lineno,
                        message=(
                            f"Field '{fname}' projected by client at "
                            f"{proj.file_path}:{proj.lineno} was removed from {ekey}."
                        ),
                    )
                )
                continue

            bfield = new_fields[fname]

            # Check Nullability Drift first for explicit diagnostic reporting
            if bfield.nullable and not proj.null_safe:
                all_delta_fields.add(fname)
                violations.append(
                    BreakingChangeViolation(
                        endpoint=ekey,
                        field_name=fname,
                        violation_kind="NULLABILITY_DRIFT",
                        backend_type=f"{bfield.type_name} | null",
                        client_expected_type=proj.expected_type,
                        backend_file=backend.file_path,
                        backend_lineno=bfield.lineno,
                        client_file=proj.file_path,
                        client_lineno=proj.lineno,
                        message=(
                            f"Nullability drift on field '{fname}' in {ekey}: "
                            f"backend returns nullable '{bfield.type_name} | null' "
                            f"({backend.file_path}:{bfield.lineno}) while client "
                            f"dereferences without guard ({proj.file_path}:{proj.lineno})."
                        ),
                    )
                )
                continue

            # Check Structural Subtyping Covariance: tau_new(f) <=_sub tau_client(f)
            if not is_structural_subtype(
                sub_type=bfield.type_name,
                super_type=proj.expected_type,
                sub_nullable=bfield.nullable,
                super_nullable=proj.null_safe,
            ):
                all_delta_fields.add(fname)
                violations.append(
                    BreakingChangeViolation(
                        endpoint=ekey,
                        field_name=fname,
                        violation_kind="TYPE_MISMATCH",
                        backend_type=bfield.type_name,
                        client_expected_type=proj.expected_type,
                        backend_file=backend.file_path,
                        backend_lineno=bfield.lineno,
                        client_file=proj.file_path,
                        client_lineno=proj.lineno,
                        message=(
                            f"Covariance violation on '{fname}' in {ekey}: "
                            f"backend type '{bfield.type_name}' is not a subtype of "
                            f"client expected type '{proj.expected_type}'."
                        ),
                    )
                )

    q_inhabit, suppression_ratio = compute_inhabitation_quotient(
        all_delta_fields, all_client_fields
    )
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0

    return ContractVerificationReport(
        phi_break=(len(violations) > 0),
        inhabitation_quotient=q_inhabit,
        suppression_ratio=suppression_ratio,
        violations=violations,
        suppressed_dead_fields=sorted(set(suppressed_dead_fields)),
        matched_endpoints=matched_endpoints,
        elapsed_ms=elapsed_ms,
    )


def analyse_cross_boundary(
    backend_source: str,
    client_source: str,
    old_backend_source: Optional[str] = None,
    backend_file: str = "backend/routes.py",
    client_file: str = "frontend/client.ts",
) -> ContractVerificationReport:
    """Convenience entrypoint parsing backend and client sources and verifying contracts."""
    new_contracts = harvest_backend_contracts(backend_source, file_path=backend_file)
    client_sites = harvest_client_callsites(client_source, file_path=client_file)
    old_contracts = (
        harvest_backend_contracts(old_backend_source, file_path=backend_file)
        if old_backend_source is not None
        else None
    )
    return verify_cross_boundary_contracts(
        backend_contracts=new_contracts,
        client_callsites=client_sites,
        old_backend_contracts=old_contracts,
    )


# ---------------------------------------------------------------------------
# High-Level Orchestrator Class
# ---------------------------------------------------------------------------

class CrossBoundaryContractSentry:
    """High-level CDC-ABS engine for monorepo and pre-commit contract verification."""

    def verify_sources(
        self,
        backend_source: str,
        client_source: str,
        old_backend_source: Optional[str] = None,
        backend_file: str = "backend/api.py",
        client_file: str = "frontend/api.ts",
    ) -> ContractVerificationReport:
        """Harvest AST contracts from source strings and verify compatibility."""
        return analyse_cross_boundary(
            backend_source=backend_source,
            client_source=client_source,
            old_backend_source=old_backend_source,
            backend_file=backend_file,
            client_file=client_file,
        )
