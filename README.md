# gpu-tracker

GPU Session Recovery Tool — track long-running commands on GPU servers, recover from crashes.

When running long ML jobs on RunPod, Lambda, or any GPU server, sessions can crash, SSH can disconnect, or terminals can close. gpu-tracker saves the state of every command (started, finished, crashed, exit code, duration, last output lines) to a JSON file so you can see exactly where you left off and resume.

## Install

```bash
pip install -e .
```

## Quick Start

```bash
# Create a session
gpu-tracker init "reranker benchmark"

# Add commands to run later
gpu-tracker add "python train.py --epochs 10"
gpu-tracker add "python evaluate.py --model nemotron"

# Or add + run immediately
gpu-tracker run "python train.py --epochs 10"

# Check status
gpu-tracker status

# Run next pending command
gpu-tracker next --run

# See what's left
gpu-tracker remaining

# If something crashed, retry it
gpu-tracker retry
```

## Commands

| Command | Description |
|---------|-------------|
| `gpu-tracker init <name>` | Create a new session |
| `gpu-tracker add <cmd>` | Add a command (pending) |
| `gpu-tracker run <cmd>` | Add and immediately run a command |
| `gpu-tracker next` | Show next pending command |
| `gpu-tracker next --run` | Run next pending command |
| `gpu-tracker status` | Show full status table |
| `gpu-tracker status --json` | Status as JSON |
| `gpu-tracker remaining` | List remaining commands |
| `gpu-tracker retry` | Retry first interrupted command |
| `gpu-tracker list` | List all sessions |
| `gpu-tracker delete <id>` | Delete a session |

## How It Works

- Session state is stored in `.gpu-tracker/` in the current directory
- Each command's status, exit code, duration, and last 20 output lines are tracked
- State is saved every 5 seconds during execution (survives crashes)
- SIGINT/SIGTERM are caught and mark the command as "interrupted"

## Crash Recovery

```bash
# After a pod crash / SSH disconnect:
cd /workspace/my-project
gpu-tracker status          # see what finished and what didn't
gpu-tracker retry           # re-run the interrupted command
gpu-tracker next --run      # continue with remaining commands
```

## License

MIT
