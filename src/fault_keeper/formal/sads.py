"""Smooth AST Differentiable Synthesis Engine (SADS).

Continuous relaxation of discrete Abstract Syntax Tree grammars for gradient-guided
and formal constraint-directed programmatic synthesis.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class GrammarProduction:
    """Represents a discrete AST grammar production rule with continuous weight."""
    rule_id: str
    symbol: str
    template: str
    weight: float = 1.0


class SADSSynthesizer:
    """Differentiable continuous relaxation synthesizer for formal AST generation."""

    def __init__(self, temperature: float = 1.0) -> None:
        self._temperature = temperature
        self._rules: Dict[str, List[GrammarProduction]] = {}

    def add_rule(self, symbol: str, template: str, initial_weight: float = 1.0) -> str:
        """Register a grammar production rule with continuous relaxation weight."""
        try:
            if not symbol or not template:
                raise ValueError("symbol and template must be non-empty strings.")
        except ValueError:
            raise

        if symbol not in self._rules:
            self._rules[symbol] = []

        rule_id = f"{symbol}_{len(self._rules[symbol])}"
        self._rules[symbol].append(
            GrammarProduction(rule_id=rule_id, symbol=symbol, template=template, weight=initial_weight)
        )
        return rule_id

    def get_softmax_probabilities(self, symbol: str) -> List[Tuple[GrammarProduction, float]]:
        """Compute categorical probabilities using continuous Softmax relaxation."""
        try:
            if symbol not in self._rules or not self._rules[symbol]:
                raise KeyError(f"Symbol '{symbol}' has no registered grammar rules.")
        except KeyError:
            raise

        rules = self._rules[symbol]
        max_w = max(r.weight for r in rules)
        exp_weights = [math.exp((r.weight - max_w) / max(self._temperature, 1e-5)) for r in rules]
        sum_exp = sum(exp_weights)
        probs = [ew / sum_exp for ew in exp_weights]

        return list(zip(rules, probs))

    def update_gradient(self, rule_id: str, loss_gradient: float, learning_rate: float = 0.1) -> None:
        """Update continuous grammar rule weights via gradient descent step."""
        for symbol, rules in self._rules.items():
            for r in rules:
                if r.rule_id == rule_id:
                    # Gradient descent: weight <- weight - lr * gradient
                    r.weight -= learning_rate * loss_gradient
                    return

    def synthesize_ast(self, start_symbol: str) -> ast.AST:
        """Synthesize concrete AST choosing max-likelihood relaxed production."""
        try:
            if start_symbol not in self._rules:
                raise KeyError(f"Symbol '{start_symbol}' not found.")
        except KeyError:
            raise

        probs = self.get_softmax_probabilities(start_symbol)
        # Select best rule
        best_rule, _ = max(probs, key=lambda x: x[1])

        # Parse template into Python AST
        parsed = ast.parse(best_rule.template)
        return parsed
