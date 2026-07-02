"""
GAMA Code Agent — entry point.

Usage:
    python agent.py path/to/model.gaml

The agent will: validate syntax -> read the code against the checklist (in
.claude/skills/gama-code-reviewer/SKILL.md) -> auto-fix syntax errors if any
(looping up to MAX_SYNTAX_FIX_ITERATIONS times) -> optionally run it -> report.

Safety
------
* Every file change is meant to go through git, so before running make sure the
  project holding your .gaml is a git repo with no uncommitted changes — that
  way you can `git diff` / `git checkout` anything the agent touched.
* `can_use_tool` below HARD-BLOCKS any Bash command that is not `git ...`, and
  blocks Write/Edit outside the directory of the model being reviewed. This is a
  hard guardrail, independent of whether the model "obeys" the system prompt.
"""

import asyncio
import os
import sys

# Load a local .env (ANTHROPIC_API_KEY, GAMA_HEADLESS_DIR) BEFORE importing the
# tools module, which reads GAMA_HEADLESS_DIR at import time.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # python-dotenv is optional; env vars can also be exported in the shell

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from tools.gama_tools import gama_tools_server

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_SYNTAX_FIX_ITERATIONS = 5


def make_can_use_tool(allowed_edit_root: str):
    """Build a permission callback that only allows edits inside allowed_edit_root."""

    async def can_use_tool(tool_name, input_data, context):
        # Our own MCP tools (validate / run) are always allowed.
        if tool_name.startswith("mcp__gama-tools__"):
            return PermissionResultAllow()

        # Bash: only git commands (for commit/diff/backup); block everything else.
        if tool_name == "Bash":
            command = input_data.get("command", "")
            if command.strip().startswith("git ") or command.strip() == "git":
                return PermissionResultAllow()
            return PermissionResultDeny(message="Only `git` commands are allowed via Bash.")

        # Write/Edit: only inside the directory of the model under review.
        if tool_name in ("Write", "Edit"):
            file_path = os.path.abspath(input_data.get("file_path", ""))
            if os.path.commonpath([file_path, allowed_edit_root]) == allowed_edit_root:
                return PermissionResultAllow()
            return PermissionResultDeny(
                message=f"Refusing to edit files outside the model directory: {allowed_edit_root}"
            )

        # Read/Glob/Grep: always safe.
        if tool_name in ("Read", "Glob", "Grep"):
            return PermissionResultAllow()

        return PermissionResultDeny(message=f"Tool '{tool_name}' is not in the allow-list.")

    return can_use_tool


async def review_model(gaml_path: str):
    gaml_path = os.path.abspath(gaml_path)
    allowed_edit_root = os.path.dirname(gaml_path)

    options = ClaudeAgentOptions(
        cwd=PROJECT_ROOT,  # so the project skill in .claude/skills is loaded
        mcp_servers={"gama-tools": gama_tools_server},
        allowed_tools=[
            "mcp__gama-tools__validate_gaml_syntax",
            "mcp__gama-tools__run_gama_headless",
            "Read",
            "Grep",
            "Glob",
            "Edit",
            "Bash",
        ],
        permission_mode="default",  # every Edit/Bash goes through can_use_tool above
        can_use_tool=make_can_use_tool(allowed_edit_root),
        max_turns=40,
        setting_sources=["project"],  # load .claude/skills/gama-code-reviewer/SKILL.md
    )

    prompt = (
        f"Review the GAML model at: {gaml_path}\n"
        f"Follow the gama-code-reviewer skill exactly. First Read the file to find "
        f"an experiment name, then validate. "
        f"For SYNTAX errors: you may auto-fix and loop up to "
        f"{MAX_SYNTAX_FIX_ITERATIONS} times. For LOGIC/data errors (per the checklist): "
        f"ONLY propose changes, do NOT edit the file, wait for the user. "
        f"Produce the final report in the format defined in the skill."
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
                    elif isinstance(block, ToolUseBlock):
                        print(f"\n[tool call: {block.name}]")
            elif isinstance(message, ResultMessage):
                print(f"\n--- Done: {message.subtype} ---")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python agent.py path/to/model.gaml")
        sys.exit(1)
    asyncio.run(review_model(sys.argv[1]))
