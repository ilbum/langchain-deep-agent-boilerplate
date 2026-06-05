# Flight Search Agent — Design Proposal

## Goal

A deep agent that browses airline websites (Delta, United, JetBlue), searches for
flights matching user-supplied criteria, and writes a structured comparison report
to a Google Doc.

---

## Key clarification: login is not required

Flight search on all three airlines is fully public — prices and schedules are
visible without an account. Login only matters for award/miles pricing or saved
traveller profiles. Skipping it eliminates credential management, session
expiry, and MFA complexity entirely.

**The real challenges, ranked:**

1. **Anti-bot detection (hardest)** — Delta uses Akamai Bot Manager, United uses
   Cloudflare. They fingerprint canvas/WebGL rendering, mouse movement patterns,
   keyboard event cadence, user-agent + header consistency, and IP reputation.
   A naive Playwright session gets blocked within seconds on Delta.

2. **Dynamic UI variance** — Each airline's search form, date picker, and results
   page has a completely different DOM structure. The agent needs to adapt visually
   rather than rely on hardcoded selectors.

3. **Price load timing** — Results arrive via AJAX in stages. The agent must wait
   for the page to settle before extracting, or it reads partial/stale prices.

---

## Browser tool options

| Tool | Fit | Notes |
|------|-----|-------|
| **Playwright** | Good — already in `pyproject.toml` | Raw control, fast; needs `playwright-stealth` plugin and manual LangChain tool wrapping |
| **browser-use** | Best fit for LLM control | LLM-native Python library built on Playwright; exposes `click`, `type`, `extract_content` as natural tool calls; handles DOM understanding automatically |
| **Browserbase / Steel.dev** | Best anti-bot story | Cloud browser infra with residential IPs + pre-warmed sessions; adds cost and external dependency but sidesteps fingerprinting |

**Recommendation:** Start with `browser-use` + `playwright-stealth` (local, free,
already aligned with the project's Python/async stack). If anti-bot blocking
proves persistent on Delta/United, swap the Playwright backend for Browserbase
without changing agent logic — the tool interface stays the same.

---

## Proposed architecture

```
User: "Find me flights JFK→LAX, July 10–12, economy"
        │
        ▼
Main orchestrator (think_tool)
        │
        ├── [parallel] airline-searcher  →  delta.com
        ├── [parallel] airline-searcher  →  united.com
        └── [parallel] airline-searcher  →  jetblue.com
                │
                │  Each returns structured text:
                │  - Cheapest option per day
                │  - Fastest non-stop per day
                │  - 2–3 alternatives with price + duration
                ▼
        report-writer  →  Google Doc (existing subagent)
```

Each `airline-searcher` subagent receives:
- Airline URL
- Origin / destination
- Date range
- Cabin class
- What to extract (cheapest, fastest, N alternatives)

It browses, waits for results to load, extracts the relevant rows, and returns
structured plain text. No files written — output is inline in the task result.

---

## Open questions (decide before building)

**1. Search parameters**
- Fixed origin/destination per agent run, or user-supplied per invocation?
- One-way or round-trip?
- Specific dates or a flexible range ("any day in a given week")?

**2. Browser backend**
- Start local (Playwright + stealth) and accept some blocking risk?
- Or invest in Browserbase from day one for cleaner anti-bot handling?

**3. `browser-use` vs raw Playwright tools**
- `browser-use` is higher-level; the agent drives it more naturally via tool calls.
- Raw Playwright tools give more precise control but require more wrapper code.
- Worth evaluating `browser-use` against the existing `deepagents` tool pattern.

**4. Report format**
- Same `create_google_doc` pattern (plain text, one doc per run)?
- Or a more structured layout — table of flights, one section per airline,
  sortable by price/duration?

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Delta/United blocking Playwright | High | `playwright-stealth`; fall back to Browserbase |
| Airline UI changes break extraction | Medium | Visual/semantic extraction via `browser-use` rather than CSS selectors |
| Price changes between search and report | Low | Timestamp each extraction; note "prices as of HH:MM" in report |
| Parallel sessions trigger rate limits | Low–Medium | Add jitter between subagent starts; limit to one session per airline |
