"""
Turn prose research into a validated ImportBundle using the Anthropic API.

The Pydantic schema's JSON schema becomes a forced tool call, so the model must
return exactly the shapes the importer expects. Output is validated before it
touches disk; anything that fails validation surfaces immediately.

    uv sync --extra extract
    export ANTHROPIC_API_KEY=...
    python manage.py extractwithclaude research.md venues.json

IMPORTANT: only extract the venue/screening/affiliation layer this way. Load
teams + the FIFA fixture list from an authoritative structured source via
`loadreferencedata` (don't ask a model to reproduce a schedule from memory).
Merge them after. This command is deferred-use in v1 — the app seeds from
sample_data.json — but is wired in so the full corpus run is a single command.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from events.import_contract import ImportBundle

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


def extract(text: str, model: str = "claude-sonnet-4-6") -> ImportBundle:
    import anthropic  # imported lazily; only needed for the extract pipeline

    client = anthropic.Anthropic()
    tool = {
        "name": "emit_import_bundle",
        "description": "Emit the structured watch-party data.",
        "input_schema": ImportBundle.model_json_schema(),
    }
    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        system=EXTRACTION_GUIDE,
        tools=[tool],
        tool_choice={"type": "tool", "name": "emit_import_bundle"},
        messages=[{"role": "user", "content": text}],
    )
    payload = next(b.input for b in resp.content if b.type == "tool_use")
    return ImportBundle.model_validate(payload)  # raises on bad output


class Command(BaseCommand):
    help = "Extract a validated ImportBundle from prose research using the Anthropic API."

    def add_arguments(self, parser):
        parser.add_argument("research_path", help="Prose research input (.md/.txt).")
        parser.add_argument("out_path", help="Where to write the validated JSON bundle.")
        parser.add_argument("--model", default="claude-sonnet-4-6")

    def handle(self, *args, **opts):
        try:
            text = open(opts["research_path"], encoding="utf-8").read()
        except OSError as exc:
            raise CommandError(f"Could not read research input: {exc}")

        try:
            bundle = extract(text, model=opts["model"])
        except ImportError:
            raise CommandError(
                "The anthropic package is not installed. Run: uv sync --extra extract"
            )

        flagged = sum(v.needs_review for v in bundle.venues) + sum(
            s.needs_review for s in bundle.screenings
        )
        with open(opts["out_path"], "w", encoding="utf-8") as fh:
            fh.write(bundle.model_dump_json(indent=2))
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(bundle.venues)} venues, {len(bundle.screenings)} screenings "
                f"({flagged} flagged for review) -> {opts['out_path']}"
            )
        )
