# CSIS China Room Brief

A weekly internal email on US-China relations, sent Friday mornings to CSIS staff. Around 900 to 1,200 words, a four to five minute read. The top follows the CSIS comms email template (the "Released This Week" send): a "For internal use only" band, a grey preheader strip with Read online and Past issues, then a 600 x 200 banner. A navy band in the same color closes the issue with the contact line for questions (Nina Prieur, nprieur@csis.org). Inside, it borrows the [China Daily Brief](https://github.com/andysaulim/Daily-China-Digest)'s section bars and item cards so the two read as one family.

| # | Section | Half | Drafted by | Items | Comes from |
|---|---------|------|------------|-------|------------|
| 0 | Editor's Note | top | Agent, rewritten by the coordinator | 1 | The week's sources |
| 1 | Week at a Glance | ahead | Agent, rewritten by the coordinator | 3 | Calendar entries for the seven days after the issue (ER sheet, daily brief Upcoming, Congress.gov); a news item only if it names a date in that week |
| 2 | Heard on the Hill | back | Agent, rewritten by the coordinator | 3-6, plus lists | Congress.gov hearings and new bills, committee releases (Select Committee on the CCP, HFAC, SFRC, armed services, banking, CECC, USCC), then Congress items in the daily brief |
| 3 | In the News | back | Agent | 5 | Top five China stories in priority outlets, under the outlet's own headline |
| 4 | Research Roundup | back | Agent | 2-6 | Think-tank and CRS feeds; each page is opened for its authors and opening text; institution in its own column |
| 5 | In the Works @ CSIS | ahead | Tracker | up to 5 | `CSIS Activities` tab |
| 6 | On the Horizon | ahead | Tracker | up to 6 | `Global Events` and `Policy Developments` tabs |

The back half runs on black section bars, the ahead half on navy, and an In this issue row under the date line links to each section.

## Weekly schedule (ET)

| When | What | Who |
|------|------|-----|
| Wed 5 pm | Tracker updated for Friday's issue | Comms coordinator and interns |
| Thu 12 pm | `weekly.py draft`: reads the past Friday through Thursday, drafts the copy, saves `issues/YYYY-MM-DD.json`, emails the draft | GitHub Actions |
| Thu noon | Reads the "Checks before send" box at the top of the draft: outlet mix, repeated events, Google redirect links, Hill sourcing, research summaries that restate titles, prose tells | Comms coordinator |
| Thu afternoon | Rewrites Editor's Note, Week at a Glance and Heard on the Hill in `issues/YYYY-MM-DD.json` (GitHub's web editor works) | Comms coordinator |
| Fri 8 am | Final review | Nina Prieur |
| Fri 9 am | `weekly.py send`, run from the Actions tab | Coordinator |

## How a run works

```
Thursday draft
  collect   China Daily Brief archive (7 issues) + outlets' own headlines (og:title)
            + think-tank and CRS feeds + the ER tracker
  compose   one Claude call; the model cites source ids, never URLs, so every
            link in the brief is one the collector found (claude-opus-5-5,
            server-side fallback on a policy decline)
  render    draft email with the coordinator's notes  ->  DRAFT_TO
Friday send
  render    final email from the edited copy + a fresh tracker pull  ->  BRIEF_TO
  archive   site/: YYYY-MM-DD.html, index.html, archive.html, archive.json
```

```
weekly.py             draft and send
brief/collect.py      daily archive, outlet headlines, research feeds, tracker download
brief/congress.py     China-related hearings and new bills from the Congress.gov API
brief/compose.py      Claude drafting with source ids and a JSON schema
brief/issue.py        assembles the issue for the template
brief/render.py       the email template, draft and final modes
brief/archive.py      web copy and archive page
brief/mailer.py       Gmail SMTP, recipients in BCC
brief/tracker.py      reads and audits the tracker workbook
brief/config.py       priority outlets, ranked
build_sample.py       Issue 0 from saved copy (samples/), house and Smart Brevity versions
```

## Setup for the first run

Repository secrets (Settings > Secrets and variables > Actions):

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | API key, ideally created inside a Console workspace |
| `ANTHROPIC_WORKSPACE_ID` | Only if the key is not scoped to a workspace: that workspace's ID |
| `GMAIL_USER`, `GMAIL_APP_PASS`, `GMAIL_FROM` | Same sending account as the daily brief |
| `DRAFT_TO` | Nina, the coordinator, Andy |
| `BRIEF_TO` | During test runs, the same people as `DRAFT_TO` |
| `TRACKER_URL` | Direct download link to the tracker, e.g. `https://drive.google.com/uc?export=download&id=<file id>` |
| `CONGRESS_API_KEY` | Free key from api.data.gov; feeds the Hearings and New legislation lists in Heard on the Hill |
| `CHINA_ROOM_CALENDAR_URL` | Optional: the link Full calendar should open |

`CHINA_ROOM_WEB_BASE` (a repository variable) turns on Read online and Past issues once the archive has a home. Until then those links are left out rather than broken, and each run's web copy is kept as an Actions artifact for 90 days.

Test runs: draft Thu Oct 8 for Fri Oct 9, then Oct 15/16 and Oct 22/23, sent only to the test list. Go live Oct 30 if those hold up.

## Design

The default design is `briefing`: each section a white card on a grey ground under a navy header with a count, a By the numbers strip under the masthead, Source Sans 3 with an Arial fallback (benchmark: Semafor and Bloomberg newsletters). Two alternates stay selectable with `BRIEF_THEME` (or `build_sample.py --theme`): `newsroom` (Axios AM / Playbook) and `pubs` (CSIS publications, Libre Baskerville on parchment).

## Writing style

`--style house` (the default) is plain prose held to Smart Brevity's length rules: headlines under 60 characters, one or two sentences an item, no bold labels. `--style brevity` adds the Axios signposts and bullets. Issue 0 is built both ways in `samples/`.

## Privacy

This repository is public. The tracker lists unannounced CSIS work, so `data/` and `out/` are git-ignored, the tracker link lives in a secret, and In the Works is rendered only into the email and the Actions artifact. `issues/*.json` holds only the drafted news copy. Making the repository private removes the remaining exposure. Do not publish `site/` to a public host while In the Works carries unannounced titles.

## Before the first live run

- Convert the tracker from .xlsx to a native Google Sheet; the tracker audit lists 47 problems (dates typed as text, empty link columns, a broken Master View formula).
- Sheet facts to correct: Shangri-La Dialogue is listed Mar 1 (normally late May or June); Munich Security Conference Mar 12 (normally mid-February); the NPC row says "20th CCP National Congress cycle" (the next congress is the 21st); "Competittion" in the biotech row.
- The sheet says the US-China truce was extended to Jan 10; the daily brief's calendar still says its suspensions lapse Nov 10. One of them is wrong.
- The banner is a stand-in until External Relations supplies one in the house banner set.
