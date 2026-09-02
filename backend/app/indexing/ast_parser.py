"""Structural (AST) code analysis via tree-sitter.

Extracts symbols (functions, classes, methods, imports) and relationships
(imports, containment) from source files. Partial failures never abort the
indexing pipeline — files that fail to parse are recorded and skipped.
"""
from __future__ import annotations

import hashlib
from typing import Any

from app.core.logging import get_logger
from app.indexing.language import AST_LANGUAGES
from app.indexing.secrets import redact
from app.models.domain import Relationship, RelationshipKind, Symbol, SymbolKind

log = get_logger(__name__)

try:
    from tree_sitter_language_pack import get_parser

    def _get_parser(lang: str):
        return get_parser(lang)
except ImportError:  # pragma: no cover - fallback when tree-sitter is missing
    def _get_parser(lang: str):  # type: ignore[misc]
        raise ImportError("tree-sitter-language-pack not installed")


def _symbol_id(file_path: str, name: str, kind: SymbolKind, line: int) -> str:
    digest = hashlib.sha1(f"{file_path}:{name}:{kind}:{line}".encode()).hexdigest()[:10]
    return f"sym_{digest}"


def extract_symbols(file_path: str, source: str, language: str) -> tuple[list[Symbol], list[Relationship]]:
    """Extract symbols/relationships for a single file. Never raises.

    Prefers tree-sitter; falls back to stdlib ast for Python on any failure.
    """
    if language not in AST_LANGUAGES and language not in {"javascript", "typescript"}:
        return [], []
    try:
        return _extract_tree_sitter(file_path, source, language)
    except Exception as exc:  # noqa: BLE001
        if language == "python":
            try:
                return _extract_python_ast(file_path, source)
            except Exception:  # noqa: BLE001
                pass
        log.debug("parse failure %s (%s): %s", file_path, language, exc)
        return [], []


def _kind_from_node_type(node_type: str) -> SymbolKind | None:
    mapping = {
        "function_definition": SymbolKind.FUNCTION,
        "function_declaration": SymbolKind.FUNCTION,
        "arrow_function": SymbolKind.FUNCTION,
        "generator_function_declaration": SymbolKind.FUNCTION,
        "class_definition": SymbolKind.CLASS,
        "class_declaration": SymbolKind.CLASS,
        "method_definition": SymbolKind.METHOD,
        "method_declaration": SymbolKind.METHOD,
        "decorated_definition": None,
        "import_statement": SymbolKind.IMPORT,
        "import_from_statement": SymbolKind.IMPORT,
    }
    return mapping.get(node_type)


def _signature_line(source: str, line_number: int) -> str | None:
    """First source line of a definition, trimmed, as its signature."""
    lines = source.splitlines()
    if 0 < line_number <= len(lines):
        return lines[line_number - 1].strip()[:300]
    return None


def _name_for_node(node: Any, source: str) -> str | None:
    """Extract the declared name; byte offsets must slice the encoded bytes."""
    try:
        data = source.encode("utf-8")
        for child in node.children:
            if child.type in ("identifier", "property_identifier", "type_identifier"):
                return data[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None
    return None


def _extract_tree_sitter(
    file_path: str, source: str, language: str
) -> tuple[list[Symbol], list[Relationship]]:
    parser = _get_parser(language)
    tree = parser.parse(source.encode("utf-8"))
    root = tree.root_node

    symbols: list[Symbol] = []
    relationships: list[Relationship] = []
    redacted_source = redact(source)

    def walk(node: Any, parent_symbol: Symbol | None) -> None:
        kind = _kind_from_node_type(node.type)
        if kind is not None:
            if kind == SymbolKind.IMPORT:
                name = _import_name_for_node(node, source)
            else:
                name = _name_for_node(node, source)
            if name:
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                sym = Symbol(
                    id=_symbol_id(file_path, name, kind, start_line),
                    name=name,
                    kind=kind,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    parent=parent_symbol.id if parent_symbol else None,
                    language=language,
                    signature=_signature_line(redacted_source, start_line),
                )
                if parent_symbol is None or kind != SymbolKind.IMPORT:
                    symbols.append(sym)
                if parent_symbol:
                    relationships.append(Relationship(
                        source=parent_symbol.id, target=sym.id, kind=RelationshipKind.CONTAINS,
                    ))
                if kind == SymbolKind.IMPORT:
                    _record_import(sym, source, node, relationships, symbols, file_path)
                for child in node.children:
                    walk(child, sym)
                return
        for child in node.children:
            walk(child, parent_symbol)

    walk(root, None)
    return symbols, relationships


def _import_name_for_node(node: Any, source: str) -> str | None:
    """Import statements: build a readable name from the statement text."""
    try:
        data = source.encode("utf-8")
        text = data[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        text = " ".join(text.split())  # collapse whitespace/newlines
        return text[:200]
    except Exception:  # noqa: BLE001
        return None


def _record_import(sym: Symbol, source: str, node: Any, relationships: list[Relationship],
                   symbols: list[Symbol], file_path: str) -> None:
    """Turn a tree-sitter import node into import relationships + module symbols."""
    try:
        import ast as pyast

        data = source.encode("utf-8")
        text = data[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        if sym.language == "python" or "import" in text[:20]:
            try:
                mod = pyast.parse(text)
            except SyntaxError:
                return
            modules: set[str] = set()
            for stmt in mod.body:
                if isinstance(stmt, pyast.Import):
                    for alias in stmt.names:
                        modules.add(alias.name)
                elif isinstance(stmt, pyast.ImportFrom) and stmt.module:
                    modules.add(stmt.module)
            for module_name in modules:
                target = _symbol_id(file_path, f"module:{module_name}", SymbolKind.MODULE, 0)
                relationships.append(Relationship(
                    source=sym.id, target=target, kind=RelationshipKind.IMPORTS,
                ))
                module_symbol = Symbol(
                    id=target, name=f"module:{module_name}", kind=SymbolKind.MODULE,
                    file_path=file_path, start_line=sym.start_line, end_line=sym.end_line,
                    language=sym.language,
                )
                if not any(s.id == target for s in symbols):
                    symbols.append(module_symbol)
    except Exception:  # noqa: BLE001
        pass


def _extract_python_ast(file_path: str, source: str) -> tuple[list[Symbol], list[Relationship]]:
    import ast

    redacted_source = redact(source)
    tree = ast.parse(source)
    symbols: list[Symbol] = []
    relationships: list[Relationship] = []

    def handle(node: Any, parent: Symbol | None) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sym = Symbol(
                id=_symbol_id(file_path, node.name, SymbolKind.FUNCTION, node.lineno),
                name=node.name,
                kind=SymbolKind.FUNCTION if parent is None else SymbolKind.METHOD,
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                parent=parent.id if parent else None,
                language="python",
                signature=_signature_line(redacted_source, node.lineno),
            )
            symbols.append(sym)
            if parent:
                relationships.append(Relationship(
                    source=parent.id, target=sym.id, kind=RelationshipKind.CONTAINS,
                ))
            for child in ast.iter_child_nodes(node):
                handle(child, sym)
        elif isinstance(node, ast.ClassDef):
            sym = Symbol(
                id=_symbol_id(file_path, node.name, SymbolKind.CLASS, node.lineno),
                name=node.name,
                kind=SymbolKind.CLASS,
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                parent=parent.id if parent else None,
                language="python",
                signature=_signature_line(redacted_source, node.lineno),
            )
            symbols.append(sym)
            if parent:
                relationships.append(Relationship(
                    source=parent.id, target=sym.id, kind=RelationshipKind.CONTAINS,
                ))
            for base in node.bases:
                relationships.append(Relationship(
                    source=sym.id,
                    target=_symbol_id(file_path, f"class:{_attr_name(base)}", SymbolKind.CLASS, 0),
                    kind=RelationshipKind.IMPORTS,
                    metadata={"relation": "inherits"},
                ))
            for child in ast.iter_child_nodes(node):
                handle(child, sym)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", None) or ""
            names = ",".join(a.name for a in node.names)
            sym = Symbol(
                id=_symbol_id(file_path, f"import:{module or names}", SymbolKind.IMPORT, node.lineno),
                name=f"import {module or names}".strip(),
                kind=SymbolKind.IMPORT,
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                parent=parent.id if parent else None,
                language="python",
            )
            symbols.append(sym)
            for alias in node.names:
                target_module = module if isinstance(node, ast.ImportFrom) else alias.name
                relationships.append(Relationship(
                    source=sym.id,
                    target=_symbol_id(file_path, f"module:{target_module}", SymbolKind.MODULE, 0),
                    kind=RelationshipKind.IMPORTS,
                ))
        else:
            for child in ast.iter_child_nodes(node):
                handle(child, parent)

    handle(tree, None)
    return symbols, relationships


def _attr_name(node: Any) -> str:
    import ast

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_attr_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Constant):
        return str(node.value)
    return "unknown"
