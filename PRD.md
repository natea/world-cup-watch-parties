# PRD: Massachusetts World Cup 2026 Watch-Party Finder

**Status:** Draft
**Date:** June 15, 2026
**Owner:** Nate (Jazkarta)

---

## 1. Summary

A web application that helps people find where to watch the 2026 FIFA Men's World Cup across Massachusetts. The tournament runs roughly June 11 to July 19, 2026, with seven matches at Gillette Stadium in Foxborough and hundreds of associated viewing options statewide: a flagship FIFA Fan Festival on Boston City Hall Plaza, dozens of free municipal watch parties, soccer bars aligned to specific national teams and clubs, brewery and waterfront screenings, hotel programming, and family-friendly community events.

The information exists but is scattered across news articles, city press releases, venue pages, and event platforms, in prose that is hard to scan and impossible to filter. This product collects that landscape into one structured dataset and presents it three ways: as a schedule, on a map, and organized around the team or teams a person wants to follow, with filters for the practical constraints that actually drive a viewing decision (is it family-friendly, is it free, is it indoor or outdoor, what kind of venue is it).

## 2. Problem statement

A fan in Greater Boston who wants to watch a specific match faces three distinct questions, and no existing source answers all three at once:

1. **When and what is on.** What matches are playing today or this weekend, and at what local time.
2. **Where to go.** Which nearby venues are showing the match they care about, and how far each is.
3. **Who they will be watching with.** Whether a venue draws a particular national-team or club crowd, which for many fans is the entire point.

On top of those, the choice is gated by constraints that published guides bury in paragraph text: whether children are welcome, whether there is a cover charge or a guaranteed seat, and whether it is an outdoor plaza or a packed indoor pub. Today, answering all of this means reading several long articles and cross-referencing them by hand. The information also changes quickly, since much of this event was organized only weeks before kickoff.

## 3. Background and context

The 2026 tournament has an unusually large footprint in Massachusetts:

- **Gillette Stadium ("Boston Stadium")** hosts seven matches: five group-stage games (June 13, 16, 19, 23, 26), a Round of 32 (June 29), and a Quarterfinal (July 9). Eight nations are scheduled to play in Foxborough during the group stage, including France and England.
- **The FIFA Fan Festival** on Boston City Hall Plaza (June 12 to 27) is the central public viewing hub, free but capacity-capped at 5,000 per session, with registration and a lottery for popular matches and no guaranteed entry.
- **State and municipal programs** funded free, family-friendly watch parties across at least 25 communities (Cambridge, Revere, Chelsea, Quincy, Worcester, Brockton, Lexington, Everett, Lowell, and more), many tailored to local diaspora communities.
- **Soccer bars and supporter hubs** anchor specific fan communities (for example a Scottish pub serving as Tartan Army HQ, a France supporters' bar, club home bars for Liverpool, Arsenal, Real Madrid, Tottenham, and Manchester United).

This richness is the opportunity and the problem: there is far more happening than any one article conveys, and the variety is exactly what makes structured filtering valuable.

## 4. Goals and non-goals

### Goals

- Let a user answer "where can I watch *this* match near me" in seconds.
- Support three first-class views over one dataset: chronological (schedule), geographic (map), and team-centric ("the team or teams I want to watch").
- Provide filters that map to real decision criteria: family-friendly, free vs paid, indoor vs outdoor, and venue type.
- Distinguish "a venue showing a match my team is in" from "a venue that is a supporter hub for my team," and let the user mean either.
- Keep the dataset current and trustworthy, with source provenance on every record and a clear path to correct entries quickly.

### Non-goals (for the initial release)

- Ticketing, reservations, or payment. The product links out; it does not transact.
- Real-time crowd or capacity data (for example live Fan Festival lottery status).
- User accounts, social features, or personalized recommendations.
- Coverage beyond Massachusetts.
- Editorial content or match commentary; this is a finder, not a media site.

## 5. Target users

- **The casual fan** who knows the team they want to watch and wants the nearest good option, fast.
- **The supporter** who wants to be with their country's or club's crowd, and cares more about atmosphere than distance.
- **The parent or group organizer** who needs a family-friendly, all-ages, ideally outdoor option and wants bars excluded from results.
- **The visitor** in town for a match at Gillette who wants viewing options before or after, or on non-match days.

## 6. Core concept: one model, three projections

The central design insight is that the schedule, map, and team views are **not three different data structures**. They are three projections of a single underlying record. Designing them as separate data shapes would create duplication and drift; designing them as queries over one model keeps them consistent for free.

The atomic, attendable unit is a **Screening**: a specific venue showing a specific match in a specific time window. A venue alone cannot drive a schedule, and a match alone cannot drive a map, but the join of the two drives all three views:

- **Schedule view** = screenings ordered by match kickoff, grouped by day.
- **Map view** = venues that have at least one screening passing the active filters; each pin surfaces that venue's relevant screening.
- **Team view** = the screenings of matches a chosen team plays in, and/or the screenings at venues affiliated with that team.

Every filter is then a constraint applied to that one query rather than a property of a bespoke view.

## 7. Functional requirements

### 7.1 Views

- **Schedule.** A day-grouped, time-ordered list of screenings. Must handle multiple matches per day and per venue. Must display local kickoff time correctly (data stored in UTC, rendered in local time).
- **Map.** Plot venues with coordinates; show only venues with a screening matching current filters; support distance-from-a-point sorting (user location or a chosen anchor such as downtown Boston). For the initial dataset size (roughly 150 venues), a bounding-box prefilter plus a Haversine distance calculation is sufficient; PostGIS is a later upgrade, not a launch requirement.
- **By team ("alliance").** The user selects one or more teams to follow. The view resolves to the screenings of that team's matches. Once the knockout bracket resolves, a followed team's newly scheduled matches must appear automatically, without manual data edits.

### 7.2 Filters

- **Family-friendly.** See Section 8 for why this is not a simple flag. The user-facing filter should be able to compose two separable levers: "minors are welcome at this screening's time" and "exclude bars."
- **Free vs paid.** A simple toggle on the surface, backed by a richer cost model underneath (see Section 8).
- **Indoor vs outdoor.** Includes venues that are both.
- **Venue type.** Bar/pub, brewery, restaurant, plaza/fan-fest, park, community space, hotel, entertainment (bowling/arcade), market/food hall, waterfront/boat, university, stadium.
- **Region.** Greater Boston, Cambridge/Somerville, North Shore, South Shore, MetroWest, Foxborough/Gillette, Worcester/Central, Other.

Filters must be composable, and the map/schedule/team views must all honor the same active filter set.

## 8. Data model and key learnings

The model has five core entities plus two supporting ones. The most valuable output of the design dialog was identifying three filters that *look* like booleans but are not, and modeling the underlying facts instead. Encoding these correctly at the schema level is what prevents subtle, hard-to-debug wrong answers later.

### 8.1 Entities

- **Team.** Reference data: name, FIFA code, flag, ranking, group, confederation.
- **Match.** The canonical FIFA fixture: stage, group, kickoff (UTC), host city and stadium, home and away teams, and (critically) nullable teams with placeholder labels and a bracket slot.
- **Venue.** The physical place: type, indoor/outdoor environment, address, city, region, coordinates, and the underlying facts that feed the family-friendly predicate (serves alcohol, default minimum age, evening minimum age, evening cutoff time), plus capacity, food, website, and data-quality fields.
- **Screening.** The atomic attendable unit joining a venue and a match at a time, with cost type, registration and entry-guarantee flags, an optional screening-specific age override, and provenance.
- **VenueAffiliation.** A supporter relationship: this venue is a hub for a given national team or club. Many-to-many and time-boundable.
- **ScreeningPolicy.** A rule for venues that show many or all matches, which materializes into concrete Screening rows.

### 8.2 Learning 1: "team" has two distinct meanings

A team appears in the model in two unrelated ways, and conflating them produces the wrong results:

1. **The match features the team** (France is playing). This is derived from `Match`.
2. **The venue is a supporter hub for the team** (the France bar), which is true regardless of whether France plays that day. This is a `VenueAffiliation`.

"Where can I watch France" and "take me to the France crowd" are different queries returning different sets, so affiliation is its own entity, not a column on the match. Affiliation is also many-to-many on the venue side, because one bar can be both a national-team HQ and a club home bar, and it is time-boundable, because some venues convert their allegiance just for the tournament.

### 8.3 Learning 2: family-friendly is time-dependent, and is not "not a bar"

"Family-friendly" and "exclude bars" are two different ideas the original request bundled together. More importantly, family-friendliness is not a stable property of a venue: several venues are all-ages by day and 21+ after a cutoff time (for example a bowling-and-bar venue that flips at 8pm). Therefore it is a predicate over **(venue, screening time)**, not a venue flag. The model stores the underlying facts (default minimum age, an optional evening minimum age, and the evening cutoff) and computes family-friendliness per screening. This correctly shows a 3pm all-ages screening at a venue that becomes 21+ at night, and hides the 9pm one.

### 8.4 Learning 3: free vs paid is not a boolean

The single most prominent venue in the dataset, the FIFA Fan Festival, is "free, but registration required, by lottery, with entry not guaranteed." That is a distinct state from free-and-open, which is distinct from ticketed, which is distinct from free-entry-with-a-purchase-minimum. Cost is modeled as an enumeration (free-open, free-registration, free-lottery, free-minimum, ticketed) plus explicit registration and entry-guarantee flags. A simple free/paid toggle is derived on top of this, so the surface stays simple while the data stays honest.

### 8.5 Learning 4: knockout fixtures exist before their teams do

The Round of 32 and Quarterfinal at Gillette had no opponents assigned during the group stage. `Match` therefore allows null teams alongside placeholder labels ("Winner Group C") and a stable bracket slot. This lets a "follow my team" feature light up a team's later matches automatically once the bracket resolves, instead of requiring a painful mid-tournament retrofit.

### 8.6 Learning 5: do not hand-author thousands of screenings

Many bars simply "show every match," or "show all of one team's matches." Rather than authoring one screening per match by hand, a `ScreeningPolicy` captures the rule (all matches, by team, or a specific set) and materializes it into concrete Screening rows. Re-running materialization after the bracket resolves makes by-team policies pick up newly scheduled fixtures. Generated screenings are flagged as such, so every view treats authored and generated screenings uniformly.

### 8.7 Other modeling choices

- Indoor/outdoor is a three-value field (indoor, outdoor, mixed) because venues like large complexes and waterfront sites are genuinely both.
- Coordinates are stored as decimals with a simple distance calculation, deferring PostGIS until scale or query complexity justifies it.
- Times are stored UTC and rendered local.

## 9. Data acquisition and pipeline

The dataset is the hard part of this product, and the key decision is to treat its two halves differently.

### 9.1 Split reference data from venue data

- **Reference data (teams and the ~104-match fixture list)** is small, fixed, and correctness-critical. A wrong kickoff time poisons every screening derived from it. This data should come from an authoritative structured source or be entered once by hand. It should **not** be extracted from prose by a language model, which can occasionally fabricate a time or matchup.
- **Venue, screening, affiliation, and policy data** is large, messy, and scattered across paragraphs. This is exactly what LLM-assisted extraction is good at.

The two halves are merged into one import payload keyed by FIFA code and match number.

### 9.2 Extraction emits the import contract, not free text

A single Pydantic schema defines the import payload and serves as the extraction contract. Its JSON schema is handed to the model as a forced tool call, so the output is shape-valid by construction and is validated again before it touches disk. The extraction prompt encodes the judgment calls the source prose leaves ambiguous: a plaza is not a bar, "free plus lottery" maps to the correct cost state, "shows every match" becomes a policy rather than many rows, and an all-ages-by-day venue gets an evening cutoff rather than a flat age limit.

### 9.3 Human review is part of the loop

Because the event is fast-moving and the source text is ambiguous in places, extraction produces a first draft, not the final load. Every record carries source provenance and a `needs_review` flag; the extractor sets the flag on anything uncertain (a missing time, a mixed indoor/outdoor venue, an unstated age policy). A reviewer corrects the flagged subset in the Django admin, and the corrected payload re-imports cleanly.

### 9.4 Idempotent import

Every loader upserts by a natural key (team by FIFA code, match by fixture number, venue by slug, screening by venue-plus-match-plus-time). Re-running the import is safe and never duplicates; a corrected export simply overwrites the prior load. The import finishes by materializing policies, so a venue's "shows every match" rule fans out into concrete screenings and all three views populate.

## 10. Technical architecture

- **Backend:** Django. The data model lives in the ORM; the three views are queryset methods, and the filters are composable queryset filters over the Screening spine.
- **API:** Django REST Framework, exposing endpoints that map almost one-to-one onto the queryset methods (a schedule endpoint, a map endpoint, and a screenings endpoint that accepts team and filter parameters). This layer is the next build step.
- **Frontend:** A separate client consuming the API, rendering the schedule list, an interactive map, and the team-centric view.
- **Data tooling:** A Pydantic import/extraction schema, an LLM extraction script (Anthropic API with a forced-tool-call contract), and an idempotent Django management command for loading validated payloads.

## 11. Risks, caveats, and open questions

- **Data freshness.** Hours, venues, and even which matches a place shows can change late. The product needs a low-friction correction path and visible "last updated" provenance. A periodic re-extraction or a lightweight submission flow may be warranted.
- **Knockout uncertainty.** Opponents for late-tournament dates are unknown until the bracket resolves; the UI must handle TBD matchups gracefully and update automatically.
- **Family-friendly accuracy.** The time-varying age logic is correct in the model, but depends on the source data actually capturing evening cutoffs. Venues without a stated policy should be flagged rather than guessed.
- **Backend portability.** The database-level family-friendly filter relies on comparing an extracted time to a column, which is verified on PostgreSQL; on some backends the per-row Python predicate is the fallback. PostgreSQL is the assumed production database.
- **Coverage gaps.** Some fan communities are underrepresented in published sources (for example dedicated Portugal or Mexico supporter hubs). The model supports them; the data may need targeted sourcing.
- **Scope discipline.** Distance search, real-time capacity, and accounts are explicit non-goals for v1 and should stay deferred.

## 12. Roadmap

1. **Schema and import (done in prototype).** Django models, the Pydantic contract, the idempotent importer, and the LLM extraction script, validated end-to-end against a sample dataset that exercises the edge cases.
2. **Reference data load.** Teams and the full fixture list from an authoritative source.
3. **Full extraction and review.** Run extraction over the research corpus, review flagged records, and load the complete dataset.
4. **API layer.** DRF serializers and endpoints for the three views with composable filters.
5. **Frontend.** Schedule, map, and team views consuming the API.
6. **Freshness loop.** A repeatable update path before and during the tournament.

## 13. Appendix: glossary

- **Screening:** one venue showing one match at one time; the atomic unit.
- **Supporter hub / affiliation:** a venue associated with a national team or club, independent of any single match.
- **Policy:** a rule (all matches / by team / specific) that materializes into screenings.
- **Materialize:** expand a policy into concrete screening rows.
- **needs_review:** a per-record flag marking data the extractor was unsure about, for human verification.
