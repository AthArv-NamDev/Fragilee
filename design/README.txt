Fragilee v2 design (22 Oct 2026)

out/*.html  the mockups (open in a browser; v2-new-analysis.html is interactive)
samples.json  real API responses used as sample data: stage1 (Low), stage2 (High, mixed), stage2_high (Critical), plus /v1/meta
*.py  the generator: common.py (tokens, ring, static tree), pages_result.py, pages_flow.py, pages_other.py
Rebuild: python3 pages_result.py ; python3 pages_flow.py ; python3 pages_other.py   (writes into out/)
render.py  optional preview with WeasyPrint (not a browser: chip heights and button widths look off in it, so trust a real browser)

Done: result (level 2 + level 1), new-analysis flow (both levels), dashboard, landing, sign-in, settings.
Not done: design-system v2 page, interactive plex-tree prototype, a real-browser review, Figma import.
