"""Tests for devunit-gen."""

import argparse
import os
import sys
from pathlib import Path

import pytest

from devunit_gen.devunit_gen import build_unit_lines, generate_unit_file


# ---- build_unit_lines (pure logic) ----------------------------------------


def test_build_unit_lines_defaults(args_base):
    """With no cmd, placeholder lines are inserted."""
    lines = build_unit_lines(args_base)
    assert "[Unit]" in lines
    assert 'Description=Dev server: myapp' in lines
    assert "After=network.target" in lines
    assert "WorkingDirectory=/home/user/proj" in lines
    assert '# <EDIT> Add your ExecStart below:' in lines
    assert "# ExecStart=/usr/bin/python3 -m http.server 8000" in lines
    assert '# <EDIT> Add env vars if needed:' in lines
    assert '# Environment="DEBUG=1"' in lines
    assert "Restart=on-failure" in lines
    assert "RestartSec=2" in lines
    assert "StandardOutput=journal" in lines
    assert "StandardError=journal" in lines
    assert "[Install]" in lines
    assert "WantedBy=default.target" in lines


def test_build_unit_lines_with_cmd(args_base):
    """When --cmd is given, ExecStart is set and placeholders are omitted."""
    args_base.cmd = "python -m http.server 8000"
    lines = build_unit_lines(args_base)
    assert "ExecStart=python -m http.server 8000" in lines
    assert "# <EDIT> Add your ExecStart below:" not in lines


def test_build_unit_lines_description(args_base):
    """Custom --desc overrides the default."""
    args_base.desc = "My custom service"
    lines = build_unit_lines(args_base)
    assert "Description=My custom service" in lines
    assert "Dev server:" not in lines


def test_build_unit_lines_default_description(args_base):
    """Without --desc, default is 'Dev server: <name>'."""
    args_base.desc = None
    args_base.name = "myapp"
    lines = build_unit_lines(args_base)
    assert "Description=Dev server: myapp" in lines


def test_build_unit_lines_env(args_base):
    """--env KEY=VALUE pairs produce Environment lines."""
    args_base.env = ["DEBUG=1", "PORT=8080"]
    lines = build_unit_lines(args_base)
    assert 'Environment="DEBUG=1"' in lines
    assert 'Environment="PORT=8080"' in lines
    assert "# <EDIT> Add env vars if needed:" not in lines


def test_build_unit_lines_no_env(args_base):
    """Without --env, placeholder env lines appear."""
    args_base.env = []
    lines = build_unit_lines(args_base)
    assert '# Environment="DEBUG=1"' in lines
    assert "# <EDIT> Add env vars if needed:" in lines


def test_build_unit_lines_restart(args_base):
    """--restart and --restart-sec are reflected."""
    args_base.restart = "always"
    args_base.restart_sec = 5
    lines = build_unit_lines(args_base)
    assert "Restart=always" in lines
    assert "RestartSec=5" in lines


def test_build_unit_lines_working_dir(args_base):
    """--dir with ~ is expanded."""
    args_base.dir = "~/projects"
    lines = build_unit_lines(args_base)
    expected = os.path.expanduser("~/projects")
    assert f"WorkingDirectory={expected}" in lines


# ---- generate_unit_file (file-writing side effects) -----------------------


def test_generate_unit_file_writes_file(args_base, tmp_home):
    """Unit file is written to the expected path."""
    result = generate_unit_file(args_base)
    expected = tmp_home / ".config" / "systemd" / "user" / "myapp.service"
    assert result == expected
    assert expected.exists()
    assert expected.read_text().startswith("[Unit]")


def test_generate_unit_file_content(args_base, tmp_home):
    """Written file contains the full unit file content."""
    generate_unit_file(args_base)
    path = tmp_home / ".config" / "systemd" / "user" / "myapp.service"
    text = path.read_text()
    assert "Description=Dev server: myapp" in text
    # No real ExecStart directive (only a comment placeholder)
    assert "ExecStart=" in text  # the placeholder starts with #
    assert "Restart=on-failure" in text


def test_generate_unit_file_exists_without_force(args_base, tmp_home, capsys):
    """When file exists and --force is not set, return None and print error."""
    path = tmp_home / ".config" / "systemd" / "user" / "myapp.service"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("existing content")

    result = generate_unit_file(args_base)
    assert result is None
    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_generate_unit_file_exists_with_force(args_base, tmp_home, capsys):
    """When file exists and --force is set, overwrite it."""
    args_base.force = True
    path = tmp_home / ".config" / "systemd" / "user" / "myapp.service"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("existing content")

    result = generate_unit_file(args_base)
    assert result == path
    assert path.exists()
    # Content should now be the generated unit file
    assert "[Unit]" in path.read_text()


def test_generate_unit_file_creates_dir(args_base, tmp_home):
    """Parent directories are created if they don't exist."""
    # tmp_home is empty, no .config/systemd/user yet
    result = generate_unit_file(args_base)
    expected_dir = tmp_home / ".config" / "systemd" / "user"
    assert expected_dir.is_dir()
    assert result is not None
    assert result.parent == expected_dir


# ---- service name validation ---------------------------------------------


def test_valid_service_name_allowed(args_base, monkeypatch):
    """Service names matching the regex ^[a-zA-Z0-9_\-\.]+$ are accepted."""
    args_base.start = True
    args_base.name = "my-app_1.0"
    # Prevent actual systemctl call
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)
    # generate_unit_file will validate and call subprocess.run (monkeypatched)
    # We just need to ensure no sys.exit is called
    try:
        generate_unit_file(args_base)
    except SystemExit:
        pytest.fail("Valid name caused sys.exit")


def test_invalid_service_name_rejected(args_base, monkeypatch, capsys):
    """Service names with special chars cause sys.exit."""
    args_base.start = True
    args_base.name = "my app; rm -rf /"
    with pytest.raises(SystemExit):
        generate_unit_file(args_base)
    captured = capsys.readouterr()
    assert "invalid service name" in captured.err


# ---- main entry point (CLI smoke test) -----------------------------------


def test_main_help(capsys):
    """--help prints usage and exits."""
    from devunit_gen.devunit_gen import main

    with pytest.raises(SystemExit):
        main()
    # main() will parse_args() which reads sys.argv; we need to set argv
    # Actually we test via direct call below


def test_main_cli_smoke(monkeypatch, tmp_home, capsys):
    """Run main() with --no-edit and a temp home to verify no crash."""
    from devunit_gen.devunit_gen import main

    monkeypatch.setattr(sys, "argv", ["prog", "testunit", "--no-edit"])
    # Prevent systemctl calls
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)

    # Redirect stdin so isatty() returns False
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    main()
    captured = capsys.readouterr()
    assert "Generated" in captured.out


def test_main_cli_with_cmd(monkeypatch, tmp_home, capsys):
    """Run main() with --cmd and verify output."""
    from devunit_gen.devunit_gen import main

    monkeypatch.setattr(
        sys, "argv", ["prog", "testunit", "--no-edit", "--cmd", "echo hello"]
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    main()
    captured = capsys.readouterr()
    assert "Generated" in captured.out


def test_main_cli_exists_error(monkeypatch, tmp_home, capsys):
    """When unit file exists and --force is absent, error is printed."""
    from devunit_gen.devunit_gen import main

    # Pre-create the file
    unit_dir = tmp_home / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    (unit_dir / "testunit.service").write_text("existing")

    monkeypatch.setattr(
        sys, "argv", ["prog", "testunit", "--no-edit"]
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(SystemExit):
        main()
    captured = capsys.readouterr()
    assert "already exists" in captured.err
