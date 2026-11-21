# Phase 1 Explained - "The Foundation"

*Read-aloud friendly. No technical background needed.*

## The big picture

We are building **CloudDesk Support**, a helper for customer-support staff. When a customer writes in
with a problem, the system will investigate, suggest a fix, and ask a human to approve anything risky,
such as a refund.

Phase 1 does **not** touch tickets yet. Think of building a restaurant: before any cooking, you need a
building, power, a front door, a security camera and a way to check the kitchen is open. That is Phase 1.

## The four pieces we built

| # | Piece | Everyday analogy | What it does |
|---|---|---|---|
| P1-1 | **Settings and logging** | The building's control panel and a diary | All options (demo mode, which AI to use) live in one place. Everything the system does is written down in a tidy, searchable diary. |
| P1-2 | **Health checks and request ID** | An "Open / Closed" sign and a parcel tracking number | Anyone can ask "are you alive?" and "are you ready?". Every visit gets a unique tracking number. |
| P1-3 | **Offline test harness** | A practice kitchen | Automated checks run on a laptop with no internet, no paid AI and no real database, so they are fast and free. |
| P1-4 | **Makefile and `.env.example`** | A one-page instruction card and a blank settings form | Short commands such as `make test`, and a template listing every setting with no secrets in it. |

## How a request travels (simple story)

1. Someone (or a monitoring tool) knocks on the door: "Are you alive?"
2. A **receptionist** stamps the visit with a tracking number. If the visitor brought a safe one, it is reused. If not, a new one is made.
3. A **gatekeeper** checks the visitor comes from an allowed website.
4. The **health desk** answers "OK", or "Degraded" with the reason, never revealing passwords.
5. The answer returns with the tracking number attached, and the diary records it.

## Why this matters (talking points)

- **Everything is traceable.** The tracking number appears in every diary line, so a problem can be followed end to end.
- **Secrets stay secret.** Passwords never appear in answers or logs. The template contains blanks only.
- **Safe to demo.** The default "fake AI" mode needs no account and costs nothing.
- **Quality from day one.** 25 automated checks pass before any feature exists.

## Honest status

- Done: settings, logging, health, tracking numbers, tests, Makefile, template.
- Not yet: the "ready" check only inspects configuration. It does not yet open real database, cache or AI connections.
- Not yet: seed, ingest, demo, MCP, smoke and terraform commands are placeholders that say "not implemented yet".
- Not yet: no containers, cloud deployment, tickets or AI agents. Those come in later phases.

## One-sentence summary

*"Phase 1 built the safe, observable, testable base that every later feature plugs into."*
