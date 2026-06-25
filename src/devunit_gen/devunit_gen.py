#!/usr/bin/env python3
"""Generate a systemd --user unit file and optionally open it in vi."""
# huggingface chat agentic with Kimi-K2.6 via fireworks-ai 2026-05-29
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Generate a systemd user unit from the current directory"
    )
    parser.add_argument("name", help="Service name (becomes name.service)")
    parser.add_argument(
        "--cmd",
        help='Command to run, e.g. "python -m http.server 8000". '
             'If omitted, a placeholder is inserted.',
    )
    parser.add_argument(
        "--desc",
        help="Unit description (default: Dev server: NAME)",
    )
    parser.add_argument(
        "--dir",
        default=os.getcwd(),
        help=f"Working directory (default: {os.getcwd()})",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        help="Environment variable as KEY=VALUE (repeatable)",
    )
    parser.add_argument(
        "--restart",
        default="on-failure",
        choices=[
            "no", "on-success", "on-failure", "on-abnormal",
            "on-watchdog", "on-abort", "always",
        ],
    )
    parser.add_argument(
        "--restart-sec",
        type=int,
        default=2,
        help="Seconds to wait before restarting (default: 2)",
    )
    parser.add_argument(
        "--no-edit",
        action="store_true",
        help="Do not open $EDITOR (default: vi) after generation",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing unit file",
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start the service immediately after generation",
    )

    args = parser.parse_args()

    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit_path = unit_dir / f"{args.name}.service"

    if unit_path.exists() and not args.force:
        print(
            f"Error: {unit_path} already exists. "
            "Use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    description = args.desc or f"Dev server: {args.name}"
    directory = os.path.expanduser(args.dir)

    # Build unit file line-by-line so indentation stays clean
    lines = []
    lines.append("[Unit]")
    lines.append(f"Description={description}")
    lines.append("After=network.target")
    lines.append("")
    lines.append("[Service]")
    lines.append("Type=simple")
    lines.append(f"WorkingDirectory={directory}")

    if args.cmd:
        lines.append(f"ExecStart={args.cmd}")
    else:
        lines.append("# <EDIT> Add your ExecStart below:")
        lines.append("# ExecStart=/usr/bin/python3 -m http.server 8000")

    if args.env:
        for env in args.env:
            lines.append(f'Environment="{env}"')
    else:
        lines.append("# <EDIT> Add env vars if needed:")
        lines.append('# Environment="DEBUG=1"')

    lines.append(f"Restart={args.restart}")
    lines.append(f"RestartSec={args.restart_sec}")
    lines.append("StandardOutput=journal")
    lines.append("StandardError=journal")
    lines.append("")
    lines.append("[Install]")
    lines.append("WantedBy=default.target")
    lines.append("")

    unit_path.write_text("\n".join(lines))
    print(f"Generated {unit_path}")

    # Open editor
    if not args.no_edit and sys.stdin.isatty():
        editor = os.environ.get("EDITOR", "vi")
        subprocess.run([editor, str(unit_path)])
        print(f"Editor closed. Saved to {unit_path}")

    # Reload so systemctl sees the new/changed unit
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    print("Ran systemctl --user daemon-reload")

    if args.start:
        subprocess.run(["systemctl", "--user", "start", f"{args.name}.service"])
        print(f"Started {args.name}.service")


if __name__ == "__main__":
    main()