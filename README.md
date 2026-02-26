# gpu-tracker

GPU Session Recovery Tool — track long-running commands on GPU servers, recover from crashes.

When running long ML jobs on RunPod, Lambda, or any GPU server, sessions can crash, SSH can disconnect, or terminals can close. gpu-tracker saves the state of every command (started, finished, crashed, exit code, duration, last output lines) to a JSON file so you can see exactly where you left off and resume.

## Install

```bash
# Remote GPU server (RunPod, Lambda, etc.)
pip install git+https://github.com/sariekr/gpu-session-tracker.git

# Local development
git clone https://github.com/sariekr/gpu-session-tracker.git
cd gpu-session-tracker
pip install -e .
```

## How It Works

gpu-tracker is **not** a background daemon. You run your commands **through** it:

```
# Without gpu-tracker:
python train.py --epochs 10              # SSH koptu, nerede kaldın? bilmiyorsun

# With gpu-tracker:
gpu-tracker run "python train.py"        # aynı komutu çalıştırır + state'i JSON'a yazar
```

The flow:

```
1. gpu-tracker init "my session"         # .gpu-tracker/ klasörü oluşur
2. gpu-tracker add "python step1.py"     # komutları planla
3. gpu-tracker add "python step2.py"
4. gpu-tracker run-all                   # hepsini sırayla çalıştır
   └─ her komut bittikçe JSON güncellenir (5 saniyede bir de ara kayıt)
5. [SSH kopar / pod çöker]
6. [yeni pod aç, aynı dizine git]
7. gpu-tracker status                    # hangileri bitti, hangisi crash oldu
8. gpu-tracker retry                     # crash olanı tekrar çalıştır
9. gpu-tracker next --run                # kalan pending'lerle devam et
```

State is stored locally in `.gpu-tracker/` inside your working directory. Nothing is sent to GitHub or any remote service. If your workspace is on persistent storage (e.g. `/workspace` on RunPod), the state survives pod restarts.

## Quick Start

```bash
# Create a session
gpu-tracker init "reranker benchmark"

# Add commands to run later
gpu-tracker add "python train.py --epochs 10"
gpu-tracker add "python evaluate.py --model nemotron"

# Run all pending commands sequentially
gpu-tracker run-all

# Or add + run immediately (one command)
gpu-tracker run "python train.py --epochs 10"

# Check status
gpu-tracker status

# See what's left
gpu-tracker remaining
```

## Run All with Skip Errors

`run-all` runs all pending commands in order. By default it stops on the first failure:

```bash
gpu-tracker run-all                  # stops if any command fails
```

With `--skip-errors`, failed commands are marked as "skipped" and execution continues:

```bash
gpu-tracker run-all --skip-errors    # skip failures, continue with the rest
```

Example:

```
$ gpu-tracker run-all --skip-errors

Running [1]: python model1.py
✓ [1] done (exit=0)
Running [2]: python model2.py          # this one crashes
⊘ [2] skipped (exit=1)
Running [3]: python model3.py          # continues anyway
✓ [3] done (exit=0)

Finished: 3 ran, 1 skipped, 0 failed
```

You can also manually skip all interrupted commands:

```bash
gpu-tracker skip                     # mark all interrupted as skipped
gpu-tracker next --run               # continue with next pending
```

## Crash Recovery

```bash
# After a pod crash / SSH disconnect:
cd /workspace/my-project
gpu-tracker status          # see what finished and what didn't
gpu-tracker retry           # re-run the interrupted command
gpu-tracker next --run      # continue with remaining commands

# Or skip the crashed one and move on:
gpu-tracker skip
gpu-tracker run-all
```

## Commands

| Command | Description |
|---------|-------------|
| `gpu-tracker init <name>` | Create a new session |
| `gpu-tracker add <cmd>` | Add a command (pending) |
| `gpu-tracker run <cmd>` | Add and immediately run a command |
| `gpu-tracker run-all` | Run all pending commands sequentially |
| `gpu-tracker run-all --skip-errors` | Run all, skip failures and continue |
| `gpu-tracker next` | Show next pending command |
| `gpu-tracker next --run` | Run next pending command |
| `gpu-tracker status` | Show full status table |
| `gpu-tracker status --json` | Status as JSON |
| `gpu-tracker remaining` | List remaining commands |
| `gpu-tracker retry` | Retry first interrupted command |
| `gpu-tracker skip` | Mark all interrupted as skipped |
| `gpu-tracker list` | List all sessions |
| `gpu-tracker delete <id>` | Delete a session |

## Command Statuses

| Status | Symbol | Meaning |
|--------|--------|---------|
| pending | ○ | Not yet started |
| running | ► | Currently executing |
| done | ✓ | Finished successfully (exit 0) |
| interrupted | ✗ | Crashed, killed, or non-zero exit |
| skipped | ⊘ | Failed but skipped via --skip-errors |

## Technical Details

- State is saved to `.gpu-tracker/` as JSON in the current directory
- During execution, state is flushed to disk every 5 seconds (crash-safe)
- SIGINT (Ctrl+C) and SIGTERM are caught and mark the command as "interrupted"
- Last 20 lines of stdout/stderr are kept per command
- No external dependencies required (rich is optional for colored tables)

## License

MIT
