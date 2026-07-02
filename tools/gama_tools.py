r"""
Custom tools for the GAMA Code Agent.

Wraps the GAMA headless launcher (`gama-headless.bat` on Windows,
`gama-headless.sh` on macOS/Linux) into two tools the Claude agent can call:

  * validate_gaml_syntax  -> compile-check ONE model without running a full sim
  * run_gama_headless     -> actually run a batch experiment

Configuration
-------------
Set the environment variable ``GAMA_HEADLESS_DIR`` to the ``headless`` folder
inside your GAMA installation (the folder that contains ``gama-headless.bat`` /
``gama-headless.sh``). See docs/SETUP_WINDOWS.md or docs/SETUP_MACOS.md.

Technical notes (verified in practice)
--------------------------------------
* On Windows, ``gama-headless.bat`` fails with "not recognized" if invoked as a
  bare name; it must be called with an ABSOLUTE path, while keeping the working
  directory set to the headless folder so its internal relative paths
  (``..\plugins``) resolve. This module handles that automatically.
* The GAMA ``-validate`` flag only validates the BUILT-IN library, not your
  file. To compile-check a specific model we use ``-xml`` (which forces GAMA to
  compile the model in order to emit the XML). Exit code 0 + XML produced =
  PASS; a non-zero exit (e.g. 13) = compilation failure.
"""

import os
import subprocess
import tempfile

from claude_agent_sdk import create_sdk_mcp_server, tool

# Path to the GAMA `headless` directory. MUST be provided via environment.
GAMA_HEADLESS_DIR = os.environ.get("GAMA_HEADLESS_DIR", "").strip()

IS_WINDOWS = os.name == "nt"
_SCRIPT = "gama-headless.bat" if IS_WINDOWS else "gama-headless.sh"


def _script_path() -> str:
    return os.path.join(GAMA_HEADLESS_DIR, _SCRIPT)


def _config_error() -> "str | None":
    """Return a human-readable error if GAMA is not configured, else None."""
    if not GAMA_HEADLESS_DIR:
        return (
            "GAMA_HEADLESS_DIR is not set. Point it at the `headless` folder of "
            "your GAMA install (see docs/SETUP_WINDOWS.md or docs/SETUP_MACOS.md)."
        )
    if not os.path.isfile(_script_path()):
        return f"Cannot find {_SCRIPT} in GAMA_HEADLESS_DIR = {GAMA_HEADLESS_DIR!r}."
    return None


def _headless_cmd(extra_args):
    """Build the subprocess argv for gama-headless with the given extra args."""
    script = _script_path()
    if IS_WINDOWS:
        return ["cmd", "/c", script] + extra_args
    # macOS / Linux: invoke through bash so no chmod +x is required.
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
    """Tail of GAMA's workspace log — extra context when a compile fails."""
    log_path = os.path.join(GAMA_HEADLESS_DIR, ".metadata", ".log")
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n_lines:])
    except OSError:
        return "(could not read .metadata/.log)"


@tool(
    "validate_gaml_syntax",
    "Compile-check a single GAML model with `gama-headless -xml` (forces GAMA to "
    "compile the model but does NOT run a full simulation). Returns PASS if the "
    "model compiles cleanly, or FAIL with the GAMA log otherwise. Always call "
    "this first when reviewing a model. Needs the .gaml path and the name of one "
    "experiment defined in the model.",
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

    compiled = code == 0 and os.path.exists(out_xml)
    status = "PASS" if compiled else "FAIL"
    detail = f"validate: {status}\nexit_code: {code}\n"
    if not compiled:
        detail += "\n--- compile log (.metadata/.log) ---\n" + _log_tail()
        detail += (
            "\n(GAMA headless reports that compilation failed but not the exact "
            "line — Read the .gaml file to locate the error.)"
        )
    if os.path.exists(out_xml):
        os.remove(out_xml)
    return {"content": [{"type": "text", "text": detail}]}


@tool(
    "run_gama_headless",
    "Actually run a GAMA experiment in batch mode (`gama-headless -batch`). Only "
    "call after validate_gaml_syntax has PASSED. May take minutes depending on "
    "the simulation size.",
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
        text = "TIMEOUT after 900s. The model may be too heavy or stuck in an infinite loop."
    return {"content": [{"type": "text", "text": text}]}


# In-process MCP server bundling the two tools for registration with the agent.
gama_tools_server = create_sdk_mcp_server(
    name="gama-tools",
    version="1.0.0",
    tools=[validate_gaml_syntax, run_gama_headless],
)
