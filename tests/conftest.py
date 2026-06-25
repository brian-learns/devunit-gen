"""Shared pytest fixtures for devunit-gen tests."""

import argparse
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def args_base() -> argparse.Namespace:
    """Return a minimal argparse.Namespace with default values."""
    return argparse.Namespace(
        name="myapp",
        cmd=None,
        desc=None,
        dir="/home/user/proj",
        env=[],
        restart="on-failure",
        restart_sec=2,
        no_edit=True,
        force=False,
        start=False,
    )


@pytest.fixture
def tmp_home(monkeypatch: Any, tmp_path: Path) -> Path:
    """Redirect Path.home() to a temporary directory so unit files are written there."""
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
    return fake_home
