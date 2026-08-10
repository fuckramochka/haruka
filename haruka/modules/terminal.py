"""Shell command execution with live output and secret masking."""

from __future__ import annotations

import asyncio
import os
import re
import signal
import time

from haruka.api import Context, Module, command, render

MAX_OUTPUT = 3500
EDIT_INTERVAL = 2.0
MAX_RUNTIME = 300
_DANGEROUS = re.compile(
    r"(?:^|[;&|]\s*)(?:sudo\s+)?rm\s+-[^\n]*(?:/\s*$|--no-preserve-root)|"
    r"(?:^|[;&|]\s*)(?:mkfs|wipefs|shutdown|reboot|poweroff)\b",
    re.IGNORECASE,
)


class Terminal(Module):
    name = "Terminal"
    description = "Run shell commands from Telegram"
    emoji = "\N{PERSONAL COMPUTER}"

    @command(aliases=["sh", "term", "terminalcmd"], doc="Run a shell command", usage="<command>")
    async def terminal(self, ctx: Context):
        if not ctx.args_raw:
            await ctx.error("Give me a command to run.")
            return

        cmd = ctx.args_raw
        force = cmd.startswith("--force ")
        if force:
            cmd = cmd[len("--force "):]
        if _DANGEROUS.search(cmd) and not force:
            await ctx.error("Potentially destructive command blocked. Repeat with <code>--force</code>.")
            return
        started = time.perf_counter()
        await ctx.loading(f"Running {render.mono(cmd)}")

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            start_new_session=(os.name != "nt"),
        )

        chunks: list[bytes] = []
        last_edit = 0.0

        async def _render(done: bool, code: int | None = None) -> str:
            text = b"".join(chunks).decode("utf-8", errors="replace")
            if len(text) > MAX_OUTPUT:
                text = "...\n" + text[-MAX_OUTPUT:]
            status = (
                render.ok(f"Exit code {code}")
                if done
                else render.loading("Running...")
            )
            body = render.code_block(text or "(no output)", "bash")
            return f"{render.title('Terminal', self.emoji)}\n{render.mono(cmd)}\n{body}\n{status}"

        try:
            assert proc.stdout is not None
            while True:
                remaining = MAX_RUNTIME - (time.perf_counter() - started)
                if remaining <= 0:
                    raise asyncio.TimeoutError
                chunk = await asyncio.wait_for(proc.stdout.read(4096), timeout=remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                now = asyncio.get_event_loop().time()
                if now - last_edit > EDIT_INTERVAL:
                    last_edit = now
                    await ctx.respond(await _render(done=False))
        except asyncio.TimeoutError:
            if os.name != "nt":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            chunks.append(b"\n[terminated after 300 seconds]\n")
        finally:
            code = await proc.wait()

        result = await _render(done=True, code=code)
        result += f"\n{render.info(f'Execution time: {time.perf_counter() - started:.2f}s')}"
        await ctx.respond(result)
        await ctx.db.audit("terminal.exec", cmd)
