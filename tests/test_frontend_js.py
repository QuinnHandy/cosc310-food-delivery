"""Runs the browser-script behaviour tests in tests/js with a JavaScript engine.

Each tests/js/*.test.js file loads the real scripts from app/static into a small fake browser
(tests/js/harness.js) with a stubbed fetch, then clicks buttons and submits forms and checks
what the page shows and which requests it sends. This covers behaviour the text checks in
test_frontend*.py cannot, such as the 401 redirect and the sign-in token header.

Uses Node if it is installed (GitHub's Ubuntu runners have it), otherwise macOS's built-in
JavaScriptCore. The tests are skipped if neither is available.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from app.core.config import PROJECT_ROOT

JS_DIR = Path(__file__).parent / "js"
HARNESS = JS_DIR / "harness.js"
JSC = Path("/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc")


def _engine_command() -> list[str] | None:
    node = shutil.which("node")
    if node:
        return [node, str(JS_DIR / "run_node.js")]
    if JSC.exists():
        return [str(JSC)]
    return None


ENGINE = _engine_command()


@pytest.mark.skipif(ENGINE is None, reason="no JavaScript engine (node or jsc) available")
@pytest.mark.parametrize("test_file", sorted(JS_DIR.glob("*.test.js")), ids=lambda p: p.stem)
def test_browser_script_behaviour(test_file):
    result = subprocess.run(
        [*ENGINE, str(HARNESS), str(test_file)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert " passed, 0 failed" in output, output  # the test file reached its done() call
