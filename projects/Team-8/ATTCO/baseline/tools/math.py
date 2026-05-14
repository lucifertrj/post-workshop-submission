"""Calculator tool for quantitative reasoning."""
from __future__ import annotations
import ast
import operator
from typing import Any
from .base import BaseTool
from .registry import default_registry

class CalculatorTool(BaseTool):
    name = "Calculator"
    description = "Evaluates simple mathematical expressions. Use this for math. E.g. '4 * 2.5'."

    async def execute(self, query: str, **kwargs: Any) -> str:
        try:
            # Safely evaluate math expressions
            allowed_operators = {
                ast.Add: operator.add, ast.Sub: operator.sub,
                ast.Mult: operator.mul, ast.Div: operator.truediv,
                ast.Pow: operator.pow, ast.USub: operator.neg
            }

            def eval_node(node: ast.AST) -> float:
                if isinstance(node, ast.Num):
                    return float(node.n)
                elif isinstance(node, ast.BinOp):
                    return allowed_operators[type(node.op)](eval_node(node.left), eval_node(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return allowed_operators[type(node.op)](eval_node(node.operand))
                else:
                    raise TypeError(f"Unsupported AST node: {type(node)}")

            node = ast.parse(query, mode='eval').body
            result = eval_node(node)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

# Register tool
default_registry.register(CalculatorTool())
