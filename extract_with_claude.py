"""
Turn the prose research into a validated ImportBundle using the Anthropic API.

The Pydantic schema's JSON schema becomes a forced tool call, so the model must
return exactly the shapes the importer expects. Output is validated before it
touches disk; anything that fails validation surfaces immediately.

    pip install anthropic pydantic
    export ANTHROPIC_API_KEY=...
    python extract_with_claude.py research.md venues.json

IMPORTANT: only extract the venue/screening/affiliation layer this way. Load
teams + the 104-match FIFA fixture list from an authoritative structured source
(don't ask a model to reproduce a schedule from memory). Merge them after.
"""
from __future__ import annotations

import json
import sys

import anthropic
from extraction_schema import ImportBundle

EXTRACTION_GUIDE = """\
You are extracting structured data from a prose guide about World Cup watch
parties. Return ONLY venues, screenings, and per-venue affiliations/policies via
the provided tool. Do not invent teams or the match schedule.

Rules:
- One Venue per distinct physical place. Give each a stable kebab-case slug.
- venue_type: a public square/fan-fest = "plaza"; bowling/arcade = "entertainment";
  food hall = "market"; a boat/pier = "waterfront"; municipal/park watch sites
  = "community" or "park".
- environment: outdoor plazas/parks = "outdoor"; places with both (e.g. a complex
  with indoor bars + an outdoor stage) = "mixed".
- AGE: only set default_min_age when the source states an age limit. If a place is
  all-ages by day but 21+ after a time, set evening_min_age + evening_cutoff and
  leave default_min_age null. Do NOT equate "is a bar" with an age limit.
- COST: "free but registration + lottery + entry not guaranteed" -> cost_type
  "free_lottery", registration_required true, entry_guaranteed false. A table or
  purchase minimum -> "free_minimum". Reserved/paid sections -> "ticketed".
- A venue that "shows every match" -> a policy of type "all_matches" rather than
  one screening per match. "Shows all of {team}'s matches" -> "by_team".
- Affiliations capture supporter hubs (a specific national team or club), which
  is independent of whether that team plays that day.
- Set needs_review true for anything ambiguous, and put the uncertainty in notes.
- Reference matches by their FIFA match number and teams by FIFA code; if you only
  know the matchup, leave match_number out of screenings and flag needs_review.
"""


def extract(text: str) -> ImportBundle:
    client = anthropic.Anthropic()
    tool = {
        "name": "emit_import_bundle",
        "description": "Emit the structured watch-party data.",
        "input_schema": ImportBundle.model_json_schema(),
    }
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=EXTRACTION_GUIDE,
        tools=[tool],
        tool_choice={"type": "tool", "name": "emit_import_bundle"},
        messages=[{"role": "user", "content": text}],
    )
    payload = next(b.input for b in resp.content if b.type == "tool_use")
    return ImportBundle.model_validate(payload)  # raises on bad output


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: python extract_with_claude.py <research.md> <out.json>")
    text = open(sys.argv[1], encoding="utf-8").read()
    bundle = extract(text)
    flagged = sum(v.needs_review for v in bundle.venues) + sum(s.needs_review for s in bundle.screenings)
    open(sys.argv[2], "w", encoding="utf-8").write(bundle.model_dump_json(indent=2))
    print(f"Wrote {len(bundle.venues)} venues, {len(bundle.screenings)} screenings "
          f"({flagged} flagged for review) -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
