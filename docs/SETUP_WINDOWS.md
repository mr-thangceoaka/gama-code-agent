# Setup on Windows

Step-by-step guide to run the GAMA Code Agent on Windows 10/11.

## 1. Prerequisites

### Python (standard CPython — important)
Install Python **3.11 or 3.12** from [python.org](https://www.python.org/downloads/windows/)
(3.12 recommended). During install, tick **"Add python.exe to PATH"**.

> ⚠️ **Do not use an MSYS2 / MinGW / Git-Bash Python** (the one that lives under
> `/usr/bin/python3`). Its virtual environments cannot install `pywin32`, a
> dependency of the Claude Agent SDK, and setup will fail. Use the official
> installer or the Microsoft Store build. You can verify with:
> ```bash
> py -0p          # lists installed standard CPython versions
> ```

### Node.js
Install **Node.js ≥ 20 LTS** from [nodejs.org](https://nodejs.org/). Verify:
```bash
node --version
```

### GAMA
Install **GAMA** from [gama-platform.org](https://gama-platform.org/download).
Note where it lands — typically:
```
C:\Users\<you>\AppData\Local\Programs\Gama\
```
The headless launcher you need is at:
```
C:\Users\<you>\AppData\Local\Programs\Gama\headless\gama-headless.bat
```

## 2. Get the code

```bash
git clone <your-repo-url> gama-code-agent
cd gama-code-agent
```

## 3. Create a virtual environment & install

Using the `py` launcher to guarantee a standard CPython:

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If you are in Git Bash instead of `cmd`/PowerShell, activate with:
```bash
source .venv/Scripts/activate
```

## 4. Configure

Copy the example env file and fill it in:

```bash
copy .env.example .env      # cmd/PowerShell
# or:  cp .env.example .env  # Git Bash
```

Edit `.env`:

```ini
ANTHROPIC_API_KEY=sk-ant-...
GAMA_HEADLESS_DIR=C:\Users\<you>\AppData\Local\Programs\Gama\headless
```

> The path must be the folder that contains `gama-headless.bat`.
> Backslashes are fine here.

## 5. (Recommended) Put your model under git

So you can review/revert anything the agent edits:

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

The agent prints its reasoning, `[tool call: ...]` markers, and a final report.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ERROR: No matching distribution found for pywin32` | You used an MSYS/MinGW Python. Recreate the venv with `py -3.12 -m venv .venv`. |
| `Cannot find gama-headless.bat in GAMA_HEADLESS_DIR` | `GAMA_HEADLESS_DIR` is wrong — it must point at the `headless` subfolder, not the GAMA root. |
| `'gama-headless.bat' is not recognized` | Handled automatically by the agent (it calls the `.bat` by absolute path). If you see this running the bat manually, `cd` into the `headless` folder first. |
| Validate always says PASS even for broken models | Make sure you're on this version — it uses `-xml`, not `-validate` (which ignores your file). |
| `ANTHROPIC_API_KEY` not found | Check `.env` exists in the repo root and the key has no quotes/spaces. |
