import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# core/ decides and formats; it never touches sockets, GPIO, files, processes, or clocks.
CORE_IMPORTS = {"__future__", "enum", "json", "typing", "dataclasses", "."}


def imports(source: str) -> set:
    """Top-level module names a file imports. Relative imports appear as '.'."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add("." if node.level else (node.module or "").split(".")[0])
    return found


def package_imports(package: str) -> set:
    return set().union(*(imports(path.read_text(encoding="utf-8"))
                         for path in (ROOT / package).rglob("*.py")))


class ArchitectureTests(unittest.TestCase):
    def test_core_stays_pure(self):
        self.assertLessEqual(package_imports("core"), CORE_IMPORTS,
                             "core/ must not do I/O; put it in zone_controller/ or central/.")

    def test_devices_only_share_through_core(self):
        self.assertNotIn("central", package_imports("zone_controller"),
                         "zone_controller/ must not import central/.")
        self.assertNotIn("zone_controller", package_imports("central"),
                         "central/ must not import zone_controller/.")

    def test_import_check_sees_violations(self):
        self.assertEqual(imports("import socket\nfrom zone_controller.gpio import x\nfrom . import y"),
                         {"socket", "zone_controller", "."})
