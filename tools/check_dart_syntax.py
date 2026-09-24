#!/usr/bin/env python3
"""Vérification syntaxique des sources Dart FASO LOVE via tree-sitter.

Utilise la grammaire Dart officielle (tree-sitter-dart) : détecte les
erreurs de SYNTAXE (accolades, guillemets, structure). Ne remplace pas
`flutter analyze` (analyse sémantique + types), qui reste exécuté en CI.

Usage : python3 tools/check_dart_syntax.py
Prérequis : pip install tree-sitter tree-sitter-dart
Retour : code 0 si tout est propre, 1 sinon.
"""
import os
import sys

from tree_sitter import Language, Parser
import tree_sitter_dart as tsdart

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCAN_DIRS = ("lib", "test")


def iter_error_nodes(node):
    if node.type == "ERROR" or node.is_missing:
        yield node
    for child in node.children:
        yield from iter_error_nodes(child)


def main() -> int:
    parser = Parser(Language(tsdart.language()))
    failures = 0
    checked = 0

    for scan in SCAN_DIRS:
        base = os.path.join(ROOT, scan)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for name in sorted(files):
                if not name.endswith(".dart"):
                    continue
                path = os.path.join(dirpath, name)
                checked += 1
                src = open(path, "rb").read()
                tree = parser.parse(src)
                if not tree.root_node.has_error:
                    continue
                failures += 1
                rel = os.path.relpath(path, ROOT)
                print(f"❌ {rel}")
                lines = src.decode("utf-8", "replace").splitlines()
                for err in iter_error_nodes(tree.root_node):
                    row, col = err.start_point
                    excerpt = lines[row][:100] if row < len(lines) else ""
                    print(f"   ligne {row + 1}, col {col + 1} : {err.type}")
                    print(f"      {excerpt.strip()}")

    print(f"\n{checked} fichiers analysés — {failures} avec erreur de syntaxe")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
