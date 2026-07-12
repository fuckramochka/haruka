# Competitor gap: Haruka Engine vs coddrago/Heroku and classic userbots

Research date: 2026-07-12.

## What Heroku does well

coddrago/Heroku is a Hikka-derived, developer-oriented **finished userbot**. Its
strengths are a large compatible module ecosystem, fast updates, modern Telegram
layer, inline forms/galleries/lists, setup UI, database backup, targeted security
rules and easy VPS/hosting installation.

## Why Haruka must not copy it

Heroku, Hikka and Dragon optimize for commands and account automation. Haruka is
an embeddable personality/cognition engine. Copying hundreds of commands would
turn it into the wrong product and inherit supply-chain risk from unrestricted
third-party modules.

## The 10x direction implemented in 0.3

| Axis | Classic userbot | Haruka Engine 0.3 |
| --- | --- | --- |
| Product boundary | finished account automation | embeddable engine with replaceable transports |
| Extension model | dynamic Python modules | versioned manifests, dependencies, collision checks, lifecycle |
| Security | warnings and targeted rules | deny-by-default capabilities + explicit trust for dangerous rights |
| Telegram | one client/fork | MTProto protocol + Bot API 10.1 + TDLib/test adapter contract |
| Intelligence | command-response | persistent people/self/world memory, emotion, goals, lore and initiative |
| Eventing | direct handlers | priority event bus, wildcard subscriptions, timeouts, failure reports |
| Processing | monolithic handlers | composable middleware pipeline with stop reasons and shared context |
| Reliability | restart on failure | circuit breaker, bounded scans, retries, graceful shutdown |
| Operations | logs | counters, gauges and latency snapshots |
| Supply chain | remote code installation | source digest verification and capability review primitives |

## Deliberately not copied

- unrestricted `.eval`/`.terminal` behavior;
- silent remote module execution;
- global mutable registries without dependency validation;
- a web installer coupled to one deployment provider;
- command packs unrelated to cognition.

Sources:
- https://github.com/coddrago/Heroku
- https://github.com/hikariatama/hikka
- https://github.com/Dragon-Userbot/Dragon-Userbot
- https://core.telegram.org/bots/api-changelog
- https://core.telegram.org/api/terms
