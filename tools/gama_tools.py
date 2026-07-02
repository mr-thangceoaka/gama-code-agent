r"""
Two tools that wrap GAMA headless so Claude can call them:
  validate_gaml_syntax -> compile-check one model (no full run)
  run_gama_headless    -> actually run a batch experiment

Setup: point GAMA_HEADLESS_DIR at your GAMA `headless` folder (the one with
gama-headless.bat / .sh). See docs/.

Two gotchas I hit, baked in below so you don't have to:
- Windows: gama-headless.bat only runs via an ABSOLUTE path with cwd on the
  headless folder. Bare name -> "not recognized".
- Use -xml to compile-check a model, NOT -validate. -validate only checks
  GAMA's built-in library and ignores your file. exit 0 + xml written = PASS.
"""

import os
import subprocess
import tempfile

from claude_agent_sdk import create_sdk_mcp_server, tool

# Where GAMA lives. Must come from the environment, no hardcoded paths.
GAMA_HEADLESS_DIR = os.environ.get("GAMA_HEADLESS_DIR", "").strip()

IS_WINDOWS = os.name == "nt"
_SCRIPT = "gama-headless.bat" if IS_WINDOWS else "gama-headless.sh"


def _script_path() -> str:
    return os.path.join(GAMA_HEADLESS_DIR, _SCRIPT)


def _config_error() -> "str | None":
    # Message if GAMA isn't wired up yet, else None.
    if not GAMA_HEADLESS_DIR:
        return (
            "GAMA_HEADLESS_DIR is not set. Point it at the `headless` folder of "
            "your GAMA install (see docs/SETUP_WINDOWS.md or docs/SETUP_MACOS.md)."
        )
    if not os.path.isfile(_script_path()):
        return f"Cannot find {_SCRIPT} in GAMA_HEADLESS_DIR = {GAMA_HEADLESS_DIR!r}."
    return None


def _headless_cmd(extra_args):
    script = _script_path()
    if IS_WINDOWS:
        # abs path + cwd on headless folder, see gotcha at top
        return ["cmd", "/c", script] + extra_args
    # bash so we don't need chmod +x
    return ["bash", script] + extra_args


def _run(extra_args, timeout):
    result = subprocess.run(
        _headless_cmd(extra_args),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=GAMA_HEADLESS_DIR,
    )
    return result.returncode, result.stdout, result.stderr


def _log_tail(n_lines=25):
    # GAMA dumps compile errors here; grab the tail for context on FAIL.
    log_path = os.path.join(GAMA_HEADLESS_DIR, ".metadata", ".log")
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n_lines:])
    except OSError:
        return "(could not read .metadata/.log)"


@tool(
    "validate_gaml_syntax",
    "Compile-check one GAML model with `gama-headless -xml` (compiles it, does "
    "not run a full sim). Returns PASS if it compiles, or FAIL plus the GAMA "
    "log. Call this first. Needs the .gaml path and one experiment name from the "
    "model.",
    {"gaml_path": str, "experiment_name": str},
)
async def validate_gaml_syntax(args):
    err = _config_error()
    if err:
        return {"content": [{"type": "text", "text": err}]}

    out_xml = os.path.join(tempfile.gettempdir(), "gama_validate_check.xml")
    if os.path.exists(out_xml):
        os.remove(out_xml)
    try:
        code, _stdout, _stderr = _run(
            ["-xml", args["experiment_name"], args["gaml_path"], out_xml], timeout=180
        )
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": "TIMEOUT after 180s during compile-check."}]}

    # PASS only if it exited clean AND actually wrote the xml
    compiled = code == 0 and os.path.exists(out_xml)
    status = "PASS" if compiled else "FAIL"
    detail = f"validate: {status}\nexit_code: {code}\n"
    if not compiled:
        detail += "\n--- compile log (.metadata/.log) ---\n" + _log_tail()
        # GAMA won't tell us the line, so read the .gaml to find it
        detail += "\n(GAMA only says it failed, not which line. Read the .gaml to locate it.)"
    if os.path.exists(out_xml):
        os.remove(out_xml)
    return {"content": [{"type": "text", "text": detail}]}


@tool(
    "run_gama_headless",
    "Run a GAMA experiment for real in batch mode (`gama-headless -batch`). Only "
    "after validate_gaml_syntax PASSes. Can take a few minutes.",
    {"gaml_path": str, "experiment_name": str, "verbose": bool},
)
async def run_gama_headless(args):
    err = _config_error()
    if err:
        return {"content": [{"type": "text", "text": err}]}

    extra = []
    if args.get("verbose"):
        extra.append("-v")
    extra += ["-batch", args["experiment_name"], args["gaml_path"]]
    try:
        code, stdout, stderr = _run(extra, timeout=900)
        text = f"exit_code: {code}\n\nstdout:\n{stdout}\n\nstderr:\n{stderr}"
    except subprocess.TimeoutExpired:
        text = "TIMEOUT after 900s. Model's probably too heavy or stuck in a loop."
    return {"content": [{"type": "text", "text": text}]}


# One in-process MCP server holding both tools, registered with the agent.
gama_tools_server = create_sdk_mcp_server(
    name="gama-tools",
    version="1.0.0",
    tools=[validate_gaml_syntax, run_gama_headless],
)
