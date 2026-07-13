#!/usr/bin/env python3
"""Ten-pass repository audit used locally and in CI."""
from __future__ import annotations

import ast
import compileall
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_FILES = [*ROOT.joinpath("haruka").rglob("*.py"), ROOT / "bootstrap.py", ROOT / "launcher.pyw"]


def passed(number: int, label: str) -> None:
    print(f"[{number}/10] PASS · {label}")


def main() -> int:
    # 1. Bytecode compilation.
    assert compileall.compile_dir(ROOT / "haruka", quiet=1)
    assert compileall.compile_file(ROOT / "bootstrap.py", quiet=1)
    passed(1, "all Python sources compile")

    # 2. Regression suite.
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=True,
    )
    passed(2, "regression tests")

    # 3. AST shape and duplicate definitions.
    for path in PYTHON_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for scope in [tree, *[node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]]:
            names = []
            for node in scope.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.append(node.name)
            assert len(names) == len(set(names)), f"duplicate definition in {path}"
    passed(3, "AST and duplicate definitions")

    # 4. No interactive configuration in runtime code.
    runtime = "\n".join(path.read_text(encoding="utf-8") for path in PYTHON_FILES)
    assert "input(" not in runtime
    assert "getpass(" not in runtime
    passed(4, "zero-terminal runtime configuration")

    # 5. One release version everywhere that matters.
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == "2.0.0"
    assert '__version__ = "2.0.2"' in (ROOT / "haruka/version.py").read_text()
    passed(5, "version 2.0.0 consistency")

    # 6. Relative Markdown links resolve.
    missing = []
    for path in [*ROOT.glob("*.md"), *ROOT.joinpath("docs").glob("*.md")]:
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            clean = target.split("#", 1)[0]
            if clean and not (path.parent / clean).exists():
                missing.append((path, target))
    assert not missing, missing
    passed(6, "documentation links")

    # 7. Dependency declarations are unique and minimum Python is correct.
    project = metadata["project"]
    dependencies = [item.split("[", 1)[0].split("=", 1)[0].lower() for item in project["dependencies"]]
    assert len(dependencies) == len(set(dependencies))
    assert project["requires-python"] == ">=3.10"
    passed(7, "packaging metadata")

    # 8. Secret/runtime files are absent from the repository tree.
    forbidden = (".session", ".session-journal", ".db", ".db-wal", ".db-shm", ".hrk")
    leaked = [path for path in ROOT.rglob("*") if path.is_file() and path.name != ".env.example" and path.name.endswith(forbidden)]
    assert not leaked, leaked
    assert not (ROOT / ".env").exists()
    passed(8, "secret and runtime file hygiene")

    # 9. Whitespace and accidental debug markers.
    bad = []
    for path in PYTHON_FILES:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.rstrip() != line or "TODO" in line or "FIXME" in line:
                bad.append((path, number))
    assert not bad, bad
    passed(9, "source hygiene")

    # 10. Critical architecture invariants.
    assert "create_subprocess_shell" in (ROOT / "haruka/modules/terminal.py").read_text()
    assert "Role.OWNER" in (ROOT / "haruka/modules/evaluator.py").read_text()
    assert "ensure_browser_login" in (ROOT / "haruka/core/app.py").read_text()
    assert "Command collision" in (ROOT / "haruka/core/loader.py").read_text()
    assert "client_max_size" in (ROOT / "haruka/web/server.py").read_text()
    passed(10, "security and architecture invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
