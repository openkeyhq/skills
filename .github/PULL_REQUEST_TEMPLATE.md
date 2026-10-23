## What changed

## Checklist, for the things a machine cannot check

- [ ] At least three eval cases were written before the skill body, and pass.
- [ ] No time-sensitive text. Volatile facts come from live calls, and any model id or URL cited is in `scripts/live_facts.json`.
- [ ] Public-safe: no real people, no client or customer brands, no internal details, no secrets.
- [ ] Every factual claim about OpenKey was checked against the live docs or API (`scripts/check_live.py` passes).
- [ ] No key appears anywhere, and safety rules are unchanged or stricter. Any loosening is explained below.

## Why any rule was loosened

