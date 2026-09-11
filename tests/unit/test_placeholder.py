import subprocess
import sys
import textwrap

import pytest


@pytest.mark.unit
def test_unit_placeholder_runs_without_pygame_display() -> None:
    """Unit tests must not initialize pygame's display subsystem."""
    if "pygame" in sys.modules:
        import pygame

        assert not pygame.display.get_init()


@pytest.mark.unit
def test_fixtures_are_available(seeded_rng, fake_clock) -> None:
    """The conftest fixtures wire up: seeded RNG is deterministic and the fake clock advances."""
    import random

    assert isinstance(seeded_rng, random.Random)
    assert fake_clock.now == 0.0
    fake_clock.advance(1.5)
    assert fake_clock.now == 1.5
    with pytest.raises(ValueError):
        fake_clock.advance(-0.1)


@pytest.mark.unit
def test_strict_markers_rejects_unknown_marker(tmp_path, pytestconfig) -> None:
    """An unknown marker must fail under the strict-markers configuration."""
    test_file = tmp_path / "test_bad_marker.py"
    test_file.write_text(
        textwrap.dedent(
            """
            import pytest

            @pytest.mark.this_marker_does_not_exist
            def test_x():
                assert True
            """
        )
    )

    project_root = pytestconfig.rootpath
    config_file = project_root / "pyproject.toml"
    assert config_file.exists()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(config_file),
            "--rootdir",
            str(project_root),
            str(test_file),
            "-q",
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"expected nonzero exit. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "this_marker_does_not_exist" in combined or "strict" in combined
