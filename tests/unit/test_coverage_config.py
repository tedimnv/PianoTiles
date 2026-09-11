import pathlib
import subprocess
import sys
import tomllib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read_pyproject() -> dict:
    return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())


@pytest.mark.unit
def test_pytest_cov_plugin_is_installed() -> None:
    """pytest-cov must be importable so `--cov` works at all."""
    import importlib

    assert importlib.import_module("pytest_cov") is not None


@pytest.mark.unit
def test_coverage_source_targets_piano_tiles_package() -> None:
    """coverage.run.source must include the piano_tiles package (src-layout
    directory form) so unimported modules still appear in the report."""
    config = _read_pyproject()
    sources = config.get("tool", {}).get("coverage", {}).get("run", {}).get("source", [])
    assert "src/piano_tiles" in sources


@pytest.mark.unit
def test_coverage_run_emits_report_and_passes(pytestconfig) -> None:
    """`pytest --cov=src/piano_tiles` runs, prints a report, and exits 0 when tests pass."""
    project_root = pytestconfig.rootpath
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=src/piano_tiles",
            "-m",
            "unit and not coverage_run",
            "--no-header",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/unit/test_placeholder.py",
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    # Coverage report header lines from coverage.py
    assert "coverage" in combined.lower()
    assert "piano_tiles" in combined


@pytest.mark.unit
def test_coverage_report_lists_every_module_under_piano_tiles(pytestconfig) -> None:
    """Every .py file under piano_tiles/ must appear in the report, even at 0% coverage."""
    project_root = pytestconfig.rootpath
    expected = sorted(
        p.relative_to(project_root).as_posix()
        for p in (project_root / "src" / "piano_tiles").rglob("*.py")
    )
    assert expected, "no piano_tiles modules found — package layout missing?"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=src/piano_tiles",
            "--cov-report=term",
            "-m",
            "unit",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/unit/test_placeholder.py",
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    for module_path in expected:
        assert module_path in combined, (
            f"module {module_path!r} missing from coverage report:\n{combined}"
        )
