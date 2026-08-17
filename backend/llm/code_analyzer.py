"""AST-based code analysis with tree-sitter availability checks."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List

try:
    from tree_sitter import Parser
    from tree_sitter_python import language as tree_sitter_python_language
except Exception:
    Parser = None
    tree_sitter_python_language = None


class CodeAnalyzer:
    def __init__(self) -> None:
        self.parser = None
        if Parser is not None and tree_sitter_python_language is not None:
            try:
                self.parser = Parser(tree_sitter_python_language())
            except Exception:
                self.parser = None

    def _parse_python(self, source: str) -> ast.AST:
        if self.parser is not None:
            try:
                self.parser.parse(source.encode("utf-8"))
            except Exception:
                pass
        return ast.parse(source)

    def analyze_python_file(
        self,
        file_path: Path,
        source: str,
    ) -> Dict[str, Any]:
        tree = self._parse_python(source)
        imports: List[str] = []
        functions: List[str] = []
        classes: List[str] = []
        calls: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend(
                    f"{module}.{alias.name}".strip(".")
                    for alias in node.names
                )
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Call):
                func = getattr(node.func, "id", None)
                if func is None and hasattr(node.func, "attr"):
                    func = node.func.attr
                if func:
                    calls.append(func)

        return {
            "path": str(file_path).replace("\\", "/"),
            "imports": sorted(set(imports)),
            "functions": sorted(set(functions)),
            "classes": sorted(set(classes)),
            "calls": sorted(set(calls)),
        }

    def analyze_workspace(self, workspace_root: Path) -> Dict[str, Any]:
        files: List[Dict[str, Any]] = []
        dependency_edges: List[Dict[str, str]] = []
        for file_path in workspace_root.rglob("*.py"):
            if any(
                part in {".venv", "__pycache__"}
                for part in file_path.parts
            ):
                continue
            try:
                source = file_path.read_text(encoding="utf-8")
                analysis = self.analyze_python_file(
                    file_path.relative_to(workspace_root),
                    source,
                )
            except Exception:
                continue
            files.append(analysis)
            for imported in analysis["imports"]:
                dependency_edges.append(
                    {
                        "from": analysis["path"],
                        "to": imported,
                        "type": "import",
                    }
                )
            for called in analysis["calls"]:
                dependency_edges.append(
                    {
                        "from": analysis["path"],
                        "to": called,
                        "type": "call",
                    }
                )

        return {
            "files": files,
            "dependency_graph": dependency_edges,
            "parser": "tree-sitter+ast" if self.parser is not None else "ast",
        }

    def write_analysis_report(self, workspace_root: Path) -> str:
        report = self.analyze_workspace(workspace_root)
        docs_dir = workspace_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        report_path = docs_dir / "code_analysis.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(report_path.relative_to(workspace_root)).replace("\\", "/")


code_analyzer = CodeAnalyzer()
