from __future__ import annotations

from datetime import UTC, datetime

import pytest

from haruka.core.events import Event, EventBus
from haruka.core.modules import CommandSpec, ModuleManifest, ModuleRegistry
from haruka.core.security import Capability, CapabilityDenied, SecurityPolicy
from haruka.domain import IncomingMessage


class Demo:
    manifest = ModuleManifest("demo", "1.0.0")
    async def start(self, services): pass
    async def stop(self): pass


def message(text: str) -> IncomingMessage:
    return IncomingMessage(1, 2, 3, None, "User", None, text, True, False, False, datetime.now(UTC))


@pytest.mark.asyncio
async def test_event_priority_and_isolation() -> None:
    seen = []
    bus = EventBus()
    bus.subscribe("message", lambda event: seen.append("late"), priority=20)
    bus.subscribe("message", lambda event: seen.append("early"), priority=10)
    report = await bus.publish(Event("message", {}))
    assert seen == ["early", "late"]
    assert report.handled == 2


@pytest.mark.asyncio
async def test_module_command_dispatch() -> None:
    registry = ModuleRegistry(SecurityPolicy())
    registry.register_module(Demo())

    @registry.command(CommandSpec("hello", "demo", aliases=("hi",)))
    async def hello(ctx):
        return "hello " + " ".join(ctx.args)

    assert await registry.dispatch(message('.hello "Haruka Engine"'), object()) == "hello Haruka Engine"


def test_dangerous_capability_is_denied() -> None:
    policy = SecurityPolicy(grants={"bad": frozenset({Capability.PROCESS})})
    with pytest.raises(CapabilityDenied):
        policy.validate_requested("bad", frozenset({Capability.PROCESS}))
