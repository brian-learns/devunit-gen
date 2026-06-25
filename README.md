# devunit-gen

Generate a systemd **--user** unit file from the current directory, then optionally
open it in your editor, reload systemd, and start the service — all in one command.

## Prerequsite
By default, systemd user services are terminated the moment you close your SSH session or log out of your desktop. 
```
loginctl show-user $USER --property=Linger
```
needs to show
```
Linger=yes
```
or you need to run
```
sudo loginctl enable-linger $USER
```

## Quick start

```bash
# Generate a unit file for a service called "myapp"
devunit-gen myapp
```

This creates `~/.config/systemd/user/myapp.service`, opens `$EDITOR` (or `vi`) so you
can fill in the command to run, then runs `systemctl --user daemon-reload`.

## Usage

```bash
devunit-gen <name> [options]
```

### Positional argument

| Argument | Description |
|---|---|
| `name` | Service name. Becomes `<name>.service`. |

### Options

| Option | Description |
|---|---|
| `--cmd` | The command the service should run, e.g. `"python -m http.server 8000"`. If omitted, a placeholder is inserted for you to edit. |
| `--desc` | Unit description. Default: `"Dev server: <name>"`. |
| `--dir` | Working directory for the service. Default: current directory. |
| `--env` | Environment variable as `KEY=VALUE` (can be repeated). If omitted, placeholder lines are inserted. |
| `--restart` | Restart policy. Choices: `no`, `on-success`, `on-failure`, `on-abnormal`, `on-watchdog`, `on-abort`, `always`. Default: `on-failure`. |
| `--restart-sec` | Seconds to wait before restarting. Default: `2`. |
| `--no-edit` | Skip opening `$EDITOR` after generation. |
| `--force` | Overwrite an existing unit file. |
| `--start` | Also run `systemctl --user start <name>.service` after generation. |

## Examples

### Minimal — edit the command yourself

```bash
devunit-gen myapp
```

Creates the unit file and opens `vi`. Fill in the `ExecStart=` line, save, and close.

### Full command, no edit needed

```bash
devunit-gen myapp \
  --cmd "python -m http.server 8000" \
  --desc "Dev HTTP server" \
  --dir /home/user/myproject \
  --env DEBUG=1 \
  --restart always \
  --restart-sec 5 \
  --no-edit \
  --start
```

Generates the file, skips the editor, reloads systemd, and starts the service.

### Multiple environment variables

```bash
devunit-gen myapp \
  --cmd "python app.py" \
  --env PORT=8080 \
  --env DEBUG=1
```

## Generated file location

All unit files go under `~/.config/systemd/user/<name>.service`.

## How it works

1. Builds a systemd user unit file from your arguments.
2. Writes it to the standard user unit directory.
3. Opens `$EDITOR` (default `vi`) for any final tweaks.
4. Runs `systemctl --user daemon-reload` so systemd picks up the new unit.
5. If `--start` is given, runs `systemctl --user start <name>.service`.
