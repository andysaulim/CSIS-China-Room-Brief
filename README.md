# CSIS China Room Engagement Brief

A weekly internal email, sent Tuesday mornings to CSIS staff, on what China watchers, Congress and CSIS itself did on China last week, and what CSIS has coming. It is AI-enabled: the bottom banner says so, and Brian Hart (bhart@csis.org) is the contact for errors.

The top follows the CSIS comms email template: a "For internal use only" strip, then the 600 x 200 CSIS banner with CHINA ROOM ENGAGEMENT BRIEF in the label box. The whole email sits in a fixed 680px table, so forwarding or replying does not stretch it.

## Sections

| # | Section | How it is made | Source | At most |
|---|---------|----------------|--------|---------|
| 1 | Talk Around Town | Automated; Brian approves | Trending topics from a sweep of Brian's list of influential China accounts on X, written to a Google Sheet tab where Brian marks Approve or Reject | 3 |
| 2 | Heard on the Hill | Automated | Congress.gov (hearings, new bills), committee releases, and Congress coverage from approved outlets only, each with a link | 5 |
| 3 | CSIS Impact | Automated + hybrid | Research: last week's China-tagged CSIS publications from csis.org, one line each. Engagements: last week's Google Form submissions on policy engagements, one line each | 5 |
| 4 | In the Works @ CSIS | Human | Brian's China Room sheet: the next five items by date; TBD when a date is not set; link to the full tracker | 5 |
| 5 | On the Horizon | Hybrid | Brian's AI-enabled calendar sheet: the next five items by date within 30 days; view-only link to the full calendar | 5 |

## Weekly schedule (ET)

| When | What | Who |
|------|------|-----|
| Sun 8 pm | `weekly.py sweep`: reads the X accounts, pulls the week's posts, groups them into topics, writes up to eight candidates to the "Talk Around Town" tab of the approvals sheet | GitHub Actions |
| Mon morning | Marks each candidate Approve or Reject in the Status column; may edit Topic and Summary | Brian |
| Mon 12 pm | `weekly.py draft`: builds every section, saves `issues/YYYY-MM-DD.json`, emails the draft to `DRAFT_TO` | GitHub Actions |
| Mon afternoon | Reviews the draft; edits the issue JSON in GitHub's web editor if needed | Brian, Nina |
| Tue morning | Actions > Run workflow > mode `send`: re-reads approvals and sheets, emails `BRIEF_TO` | Nina or Brian |

If no topic is approved by Monday noon, the draft shows the top unreviewed candidates so Brian can see them; the send never includes a topic that is not marked Approve. To keep a hand edit through a re-run, list its field under `"keep"` in the issue JSON (for example `"keep": ["heard_on_the_hill"]`).

Checks (empty sections, missing or redirect links, out-of-week dates, over-long lines, banned words) print in the run log and are saved under `"qa"` in the issue JSON. They are not in the email.

## Setup

### Google sheets

Make a Google Cloud service account, create a JSON key, and store the whole key file as the `GOOGLE_SERVICE_ACCOUNT_JSON` secret. The run prints the account's email when a sheet is not shared with it. Share with that email:

- the X accounts sheet, the In the Works sheet, the On the Horizon sheet, the engagement form's response sheet: Viewer
- the approvals sheet: Editor (the sweep adds the "Talk Around Town" tab itself)

Sheet layouts are read by header name, so columns can move. Calendar sheets need a Date, Name (or Title) column; Description, Type, Status and Link are used when present. Blank, TBD or TBC dates print as TBD; a month without a day ("11/2026") prints TBD under that month. The X accounts sheet needs a column headed Handle, Account, Username or X, holding @names or x.com links.

### X posts

Talk Around Town reads posts through an Apify actor (`APIFY_TOKEN`; `APIFY_ACTOR` defaults to `apidojo~tweet-scraper`). This scrapes X, which X's terms do not allow, and it can break without notice. `x_sweep.posts()` is the only code that knows about Apify, so moving to the X API is a one-function change.

### Secrets (Settings > Secrets and variables > Actions)

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID` | Claude API key; the workspace ID only if the key is not workspace-scoped |
| `GMAIL_USER`, `GMAIL_APP_PASS`, `GMAIL_FROM` | Sending account |
| `DRAFT_TO` | Brian, Nina, Andy |
| `BRIEF_TO` | The distribution list (the draft list during tests) |
| `CONGRESS_API_KEY` | Free key from api.data.gov |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | The service account key file, whole |
| `APIFY_TOKEN`, `APIFY_ACTOR` | Apify API token; actor id (optional) |
| `X_ACCOUNTS_URL` | Brian's X accounts sheet |
| `APPROVALS_SHEET_URL` | The sheet that gets the "Talk Around Town" tab |
| `ENGAGEMENTS_URL` | The engagement Google Form's response sheet |
| `WORKS_URL` | Brian's In the Works sheet |
| `HORIZON_URL` | Brian's On the Horizon sheet |
| `CHINA_ROOM_CALENDAR_URL`, `HORIZON_VIEW_URL` | Optional view-only links for the two buttons; default to the sheets' own pages |
| `TRACKER_URL` | Fallback: one workbook whose tabs feed both calendars (the old ER tracker) |

Heard on the Hill links only to .gov sites, the priority outlets in `brief/config.py`, and `HILL_ALLOWED` in the same file; add comms' approved source list there.

## Local preview

    python build_sample.py --tracker data/CSIS_US_China_Tracker.xlsx

renders `samples/engagement_sample.json` into `out/sample_draft_*.html` and `out/sample_final_*.html`.

## Privacy

Keep the repository private: the calendars list unannounced CSIS work and the approvals sheet names accounts. `data/` and `out/` are git-ignored, sheet links live in secrets, and `issues/*.json` holds only the drafted copy. Do not publish `site/` to a public host.
