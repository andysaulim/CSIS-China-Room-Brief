# CSIS China Room Brief

A weekly email on US-China relations, sent Tuesday mornings. About 1,000 to 1,500 words, a five to seven minute read, built to the length of Axios AM or POLITICO Playbook. It borrows its section bars, item cards and date chips from the [China Daily Brief](https://github.com/andysaulim/Daily-China-Digest) so the two read as one family. The top follows the CSIS comms email template (the "Released This Week" send): a grey preheader strip, then a 600 x 200 banner. `assets/banner_china_room.png` is a stand-in until External Relations supplies a banner in the house set; for a live send it needs a public URL (the Pardot file host). Issue 0 is built in two writing styles from the same sources: `samples/issue0_copy_house.json` and `samples/issue0_copy_brevity.json` (Axios Smart Brevity).

The brief has two halves. **The Week That Was** looks back seven days. **The Week Ahead** looks forward.

| # | Section | Half | Written by | Items | Words | Comes from |
|---|---------|------|------------|-------|-------|------------|
| 0 | Editor's Note | lede | Comms coordinator | 1 | 60-80 | |
| 1 | Week at a Glance | ahead | Comms coordinator | 3 | ~150 | Candidates pulled from the tracker and from forward-looking daily headlines |
| 2 | Heard on the Hill | back | Comms coordinator | 3-5 | ~180 | Congress-related daily headlines, pulled as candidates |
| 3 | In the News | back | Agent | 8-12 | ~150 | The week's top China stories in priority outlets: headline, outlet and date, no summary |
| 4 | Research Roundup | back | Agent | 2-5 | ~150 | Think-tank and CRS publications (needs the daily change below) |
| 5 | In the Works @ CSIS | ahead | Sheet | 2-4 | ~110 | `CSIS Activities` tab of the ER tracker |
| 6 | On the Horizon | ahead | Sheet | 4-6 | ~80 | `Global Events` and `Policy Developments` tabs, linked to the full calendar |

An In this issue row under the date line links to each section, and the look-back half runs on black bars, the look-ahead half on navy. The issue closes with a contact line for questions (Nina Prieur, nprieur@csis.org). The outlet list and its ranking live in `brief/config.py`.

## Weekly schedule (ET)

| When | What | Who |
|------|------|-----|
| Fri 5 pm | Tracker updated and frozen for Tuesday's issue | Comms coordinator and interns |
| Mon 10 am | Agent reads the past Monday through Sunday of daily briefs and the tracker, then drafts In the News, Research Roundup and the calendar sections, plus candidate lists for the human sections | GitHub Actions |
| Mon noon | Draft lands with Nina | Agent |
| Mon afternoon | Editor's Note, Week at a Glance and Heard on the Hill written into the draft | Comms coordinator |
| Tue 8 am | Final review | Comms director |
| Tue 9 am | Send | Agent |

A Monday federal holiday moves the whole cycle one day later. The first one is Oct 12 (Columbus Day), the second issue's draft day.

## What is here

```
brief/config.py       priority outlets (ranked), section budgets, source URLs
brief/tracker.py      reads the ER tracker workbook; audits it for problems
brief/daily_feed.py   reads the China Daily Brief ledger and archive
brief/render.py       issue -> table-based HTML email, draft and final modes
brief/archive.py      web copy, index.html, archive.html, archive.json
samples/              Issue 0 copy, every line traced to a source
build_sample.py       builds the Issue 0 sample from real inputs
```

Run the sample:

```bash
pip install -r requirements.txt
python build_sample.py --tracker data/CSIS_US_China_Tracker.xlsx \
  --ledger path/to/Daily-China-Digest/published_ledger.json --out out/
```

This writes `out/draft_2026-10-06.html` (the Monday-noon copy with the coordinator's notes and candidate lists), `out/email_2026-10-06.html` (what readers get), `out/site/` (web copy and archive) and `out/tracker_audit.txt`. The written sections come from `samples/issue0_copy.json`.

**This repository is public.** The tracker lists CSIS reports and events that have not been announced, so `data/` and `out/` are git-ignored. Do not commit the workbook or a rendered issue. Moving the repository to private would remove the risk outright.

## Build steps

1. **Fix the tracker.** Convert the Drive file from .xlsx to a native Google Sheet; the Master View formula is frozen in the .xlsx copy. `tracker_audit.txt` lists 47 problems, most of them dates typed as text and empty link columns. A proposed one-tab layout is below.
2. **Change the daily brief** (in `Daily-China-Digest`):
   - Write each day's validated digest to `public/data/YYYY-MM-DD.json`. Today `digest.json` is overwritten every morning and the ledger keeps only 14 days of headline and URL.
   - Keep the Tier 2 and Tier 3 items (81 think-tank feeds, 18 journals) in that daily file. The daily stopped publishing them, so Research Roundup has nothing to read until this lands.
   - Add a CRS feed. The Congress.gov API (`/crsreport`) is free with a key.
3. **Write `compose.py`**: one Claude call over the week's daily files that clusters stories, picks In the News and Research Roundup, and returns the issue JSON `render.py` takes. It carries the daily's rules forward: every item traces to a collected article, no claim from memory.
4. **Add the workflow**: Monday 10 am draft, Tuesday 9 am send, Gmail SMTP as in the daily.
5. **First full dummy issue** by Friday, Oct 9.

## Read online and past issues

`brief/archive.py` writes each issue to `site/` the way the daily does: `YYYY-MM-DD.html`, `index.html` for the latest, `archive.html` and `archive.json`. Set `CHINA_ROOM_WEB_BASE` to wherever `site/` is served and the email's Read online and Past issues links point there. Serving it on GitHub Pages from this repository would make In the Works public, so either host the archive somewhere access-controlled (csis.org, an intranet page) or drop unannounced items from the web copy.

## Paywalled outlets

NYT, WSJ and The Atlantic block article text. The daily already handles this: it reads the RSS headline and the page's meta description, and writes only from those. That is enough to choose a story and link it. Item copy for those outlets stays inside what the headline and description say.

## Proposed tracker layout

One tab, one row per item, filtered views in place of separate tabs:

| Column | Example | Note |
|--------|---------|------|
| Start date | 2026-11-16 | A real date cell, never text |
| End date | 2026-11-18 | Blank for single-day items |
| Date firm? | Confirmed / Month TBC | Replaces "11/2026 TBC" typed in the date cell |
| Section | In the Works / On the Horizon | Drives where it appears |
| Type | Report, Event, Summit, Deadline, Hearing, Data release | Required |
| Title | Report or event title | |
| Program / scholars | Program; lead scholar | In the Works only |
| One line for the brief | Up to 25 words | Written by a person, so the brief never runs a pasted paragraph |
| Link | csis.org or the event page | Required before an item runs |
| Public yet? | Yes / Embargoed | Embargoed items never render |
| Owner | Initials | |
| Last updated | Date | |
