"""Guards #106: every repository and service provider lives in app/api/dependencies.py."""

import ast
import re
from pathlib import Path

import app.api.routes as routes_package

PROVIDER_NAME = re.compile(r"^get_\w+_(repository|service)$")
ROUTES_DIR = Path(routes_package.__file__).parent


def test_no_route_module_defines_its_own_provider():
    offenders = []
    for path in sorted(ROUTES_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and PROVIDER_NAME.match(node.name):
                offenders.append(f"{path.name}: {node.name}")
    assert not offenders, f"Move these into app/api/dependencies.py: {offenders}"
