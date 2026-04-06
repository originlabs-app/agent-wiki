"""AST extraction via tree-sitter for code files."""
from __future__ import annotations

import re
from pathlib import Path

from atlas.core.models import Edge, Extraction, Node

_RATIONALE_RE = re.compile(r"#\s*(NOTE|HACK|WHY|IMPORTANT|TODO|FIXME):\s*(.+)", re.IGNORECASE)


def extract_python(path: Path) -> Extraction:
    """Extract nodes and edges from a Python file using the ast module.

    Falls back to stdlib ast if tree-sitter is not available.
    """
    if not path.is_file():
        return Extraction()

    try:
        import ast as stdlib_ast
        source = path.read_text(encoding="utf-8")
        tree = stdlib_ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return Extraction()

    stem = path.stem
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_ids: set[str] = set()

    # File node
    file_id = stem
    nodes.append(Node(id=file_id, label=f"{path.name}", type="code", source_file=str(path)))
    seen_ids.add(file_id)

    # Extract imports
    for node in stdlib_ast.walk(tree):
        if isinstance(node, stdlib_ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                mod_id = f"_import_{mod}"
                if mod_id not in seen_ids:
                    seen_ids.add(mod_id)
                    nodes.append(Node(id=mod_id, label=mod, type="code", source_file="<external>"))
                edges.append(Edge(source=file_id, target=mod_id, relation="imports", confidence="EXTRACTED", source_file=str(path)))
        elif isinstance(node, stdlib_ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                mod_id = f"_import_{mod}"
                if mod_id not in seen_ids:
                    seen_ids.add(mod_id)
                    nodes.append(Node(id=mod_id, label=mod, type="code", source_file="<external>"))
                edges.append(Edge(source=file_id, target=mod_id, relation="imports_from", confidence="EXTRACTED", source_file=str(path)))

    # Extract classes and functions
    for node in stdlib_ast.iter_child_nodes(tree):
        if isinstance(node, stdlib_ast.ClassDef):
            class_id = f"{stem}_{node.name}"
            if class_id not in seen_ids:
                seen_ids.add(class_id)
                nodes.append(Node(id=class_id, label=node.name, type="code", source_file=str(path), source_location=f"L{node.lineno}"))
                edges.append(Edge(source=file_id, target=class_id, relation="contains", confidence="EXTRACTED"))

            # Methods
            for item in stdlib_ast.iter_child_nodes(node):
                if isinstance(item, stdlib_ast.FunctionDef):
                    method_id = f"{class_id}_{item.name}"
                    if method_id not in seen_ids:
                        seen_ids.add(method_id)
                        nodes.append(Node(id=method_id, label=f".{item.name}()", type="code", source_file=str(path), source_location=f"L{item.lineno}"))
                        edges.append(Edge(source=class_id, target=method_id, relation="method", confidence="EXTRACTED"))

        elif isinstance(node, stdlib_ast.FunctionDef):
            func_id = f"{stem}_{node.name}"
            if func_id not in seen_ids:
                seen_ids.add(func_id)
                nodes.append(Node(id=func_id, label=f"{node.name}()", type="code", source_file=str(path), source_location=f"L{node.lineno}"))
                edges.append(Edge(source=file_id, target=func_id, relation="contains", confidence="EXTRACTED"))

    # Extract rationale comments
    for i, line in enumerate(source.splitlines(), 1):
        m = _RATIONALE_RE.search(line)
        if m:
            tag, text = m.group(1).upper(), m.group(2).strip()
            rat_id = f"{stem}_rationale_L{i}"
            if rat_id not in seen_ids:
                seen_ids.add(rat_id)
                nodes.append(Node(id=rat_id, label=f"{tag}: {text}", type="code", source_file=str(path), source_location=f"L{i}"))

    # Infer call edges (simple name matching)
    func_names: dict[str, str] = {}
    for n in nodes:
        if n.label.endswith("()"):
            name = n.label.rstrip("()").lstrip(".")
            func_names[name] = n.id

    for node in stdlib_ast.walk(tree):
        if isinstance(node, stdlib_ast.Call):
            if isinstance(node.func, stdlib_ast.Name) and node.func.id in func_names:
                # Find which function/method contains this call
                caller_id = _find_enclosing(tree, node.lineno, stem)
                target_id = func_names[node.func.id]
                if caller_id and caller_id != target_id:
                    edges.append(Edge(source=caller_id, target=target_id, relation="calls", confidence="INFERRED", confidence_score=0.8))

    return Extraction(nodes=nodes, edges=edges, source_file=str(path))


def _find_enclosing(tree, lineno: int, stem: str) -> str | None:
    """Find the function/class enclosing a given line number."""
    import ast as stdlib_ast
    best = None
    for node in stdlib_ast.walk(tree):
        if isinstance(node, (stdlib_ast.FunctionDef, stdlib_ast.ClassDef)):
            if hasattr(node, "lineno") and node.lineno <= lineno:
                if hasattr(node, "end_lineno") and (node.end_lineno is None or node.end_lineno >= lineno):
                    best = f"{stem}_{node.name}"
    return best
