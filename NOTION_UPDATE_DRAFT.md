# Milestone update — Fragilee interface, evidence and risk-tree explanations

## Completed

- The landing page has been reduced to a single “Let’s roll” screen with one primary action. Pricing, statistics, industry marquees and the other long homepage sections are removed.
- The signed-in interface now shares the landing page’s cream, ink and coral visual theme; the desktop sidebar remains dark.
- The risk-tree outline is smaller and collapsed by default. A selected node explains its direction and strength in the model score, shows the input value where applicable, and states that a model association is not proof of causation.
- The failure-story matcher now requires an exact industry match or at least two meaningful idea-term matches. It ranks stronger matches first and newer linked sources break ties. It no longer pads an empty result with generic failures.
- A free OpenAlex retrieval path now searches the latest six months of scholarly works for the selected industry tags and generic risk-tree node, then widens to seven years if needed. It returns up to three abstract-level matches from journal venues OpenAlex lists in DOAJ or CWTS Core, excludes future-dated records and caches results for six hours. Founder notes are not sent outside Fragilee. Venue-list status is a screening signal rather than a quality guarantee.
- Added the missing `PyJWT[crypto]` dependency to the backend requirements.

## Limits and follow-up

The research flow is extractive RAG: it retrieves works and shows source text, but it does not use an LLM to generate a causal explanation. OpenAlex is a research-paper index rather than a live startup-news feed; some narrow combinations may have no relevant work. Readers should inspect each source’s methods and publication venue. None of these sources proves the fate of an individual startup.

The app depends on backend network access for live OpenAlex retrieval. It needs no paid search key and no database migration. The existing Supabase context migration was already run.

## Verification

Backend test suite, frontend lint/type check, and production build were run locally. Backend tests: 157 passed (3 warnings). Focused frontend ESLint, TypeScript check, and production build passed. The Notion connector was unavailable in this session, so this file is a copy-ready update rather than a page already saved in Notion.
