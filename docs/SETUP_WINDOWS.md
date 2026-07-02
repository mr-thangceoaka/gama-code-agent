# Setup on Windows

How to run the GAMA Code Agent on Windows 10/11.

## 1. Prerequisites

### Python (use standard CPython)
Install Python **3.11 or 3.12** from [python.org](https://www.python.org/downloads/windows/)
(3.12 is fine). Tick **"Add python.exe to PATH"** during install.

> Don't use an MSYS2 / MinGW / Git-Bash Python (the `/usr/bin/python3` one). Its
> venvs can't install `pywin32`, which the Claude Agent SDK needs, so setup will
> fail. Check what you have:
> ```bash
> py -0p          # lists standard CPython versions
> ```

### Node.js
Install **Node.js >= 20 LTS** from [nodejs.org](https://nodejs.org/). Check:
```bash
node --version
```

### GAMA
Install **GAMA** from [gama-platform.org](https://gama-platform.org/download).
It usually lands in:
```
C:\Users\<you>\AppData\Local\Programs\Gama\
```
The launcher you need is:
```
C:\Users\<you>\AppData\Local\Programs\Gama\headless\gama-headless.bat
```

## 2. Get the code

```bash
git clone <your-repo-url> gama-code-agent
cd gama-code-agent
```

## 3. Virtual env + install

Use the `py` launcher so you get a standard CPython:

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

In Git Bash instead of cmd/PowerShell, activate with:
```bash
source .venv/Scripts/activate
```

## 4. Configure

```bash
copy .env.example .env      # cmd/PowerShell
# or:  cp .env.example .env  # Git Bash
```

Fill in `.env`:

```ini
ANTHROPIC_API_KEY=sk-ant-...
GAMA_HEADLESS_DIR=C:\Users\<you>\AppData\Local\Programs\Gama\headless
```

Point `GAMA_HEADLESS_DIR` at the folder that holds `gama-headless.bat`.
Backslashes are fine.

## 5. Put your model under git (recommended)

So you can review or revert what the agent edits:

```bash
cd C:\path\to\your\gama\project
git init
git add -A
git commit -m "before agent review"
```

## 6. Run

```bash
cd C:\path\to\gama-code-agent
.venv\Scripts\activate
python agent.py "C:\path\to\your\model.gaml"
```

It prints its reasoning, `[tool call: ...]` markers, and a final report.

## Troubleshooting

**`No matching distribution found for pywin32`**
You used an MSYS/MinGW Python. Recreate the venv with `py -3.12 -m venv .venv`.

**`Cannot find gama-headless.bat in GAMA_HEADLESS_DIR`**
Wrong path. It must point at the `headless` subfolder, not the GAMA root.

**`'gama-headless.bat' is not recognized`**
The agent handles this (it calls the bat by absolute path). If you hit it running
the bat by hand, `cd` into the `headless` folder first.

**Validate says PASS even for broken models**
Make sure you're on this version. It uses `-xml`, not `-validate` (which ignores
your file).

**`ANTHROPIC_API_KEY` not found**
Check `.env` sits in the repo root and the key has no quotes or spaces.
