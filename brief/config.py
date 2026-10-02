"""Fixed inputs for the CSIS China Room Brief: outlets, section budgets, sources."""

# Priority outlets, in the order and groupings the comms team supplied
# (Oct 2026). Group number is the rank used to order In the News candidates:
# a story carried by group 1 outranks the same story carried by group 9.
PRIORITY_OUTLETS = [
    (1,  "New York Times",      ["nytimes.com"]),
    (1,  "Wall Street Journal", ["wsj.com"]),
    (1,  "Washington Post",     ["washingtonpost.com"]),
    (2,  "Bloomberg",           ["bloomberg.com"]),
    (2,  "Financial Times",     ["ft.com"]),
    (3,  "Reuters",             ["reuters.com"]),
    (3,  "Associated Press",    ["apnews.com"]),
    (4,  "The Atlantic",        ["theatlantic.com"]),
    (4,  "Foreign Affairs",     ["foreignaffairs.com"]),
    (4,  "Foreign Policy",      ["foreignpolicy.com"]),
    (4,  "The Economist",       ["economist.com"]),
    (4,  "The New Yorker",      ["newyorker.com"]),
    (4,  "Vox",                 ["vox.com"]),
    (5,  "New York Post",       ["nypost.com"]),
    (6,  "POLITICO",            ["politico.com"]),
    (6,  "Axios",               ["axios.com"]),
    (6,  "Semafor",             ["semafor.com"]),
    (6,  "NOTUS",               ["notus.org"]),
    (6,  "Punchbowl News",      ["punchbowl.news"]),
    (7,  "CBS News",            ["cbsnews.com"]),
    (7,  "NBC News",            ["nbcnews.com"]),
    (7,  "CNBC",                ["cnbc.com"]),
    (7,  "ABC News",            ["abcnews.go.com", "abcnews.com"]),
    (8,  "CNN",                 ["cnn.com"]),
    (8,  "Fox News",            ["foxnews.com", "foxbusiness.com"]),
    (8,  "MS NOW",              ["ms.now", "msnbc.com"]),
    (8,  "BBC",                 ["bbc.com", "bbc.co.uk"]),
    (9,  "PBS",                 ["pbs.org"]),
    (9,  "NPR",                 ["npr.org"]),
    (9,  "Marketplace",         ["marketplace.org"]),
    (9,  "WIRED",               ["wired.com"]),
    (10, "Los Angeles Times",   ["latimes.com"]),
    (10, "Boston Globe",        ["bostonglobe.com"]),
    (10, "Chicago Tribune",     ["chicagotribune.com"]),
    (11, "The Bulwark",         ["thebulwark.com"]),
    (11, "The Hill",            ["thehill.com"]),
    (12, "The Guardian",        ["theguardian.com"]),
    (12, "C-SPAN",              ["c-span.org"]),
    (12, "Forbes",              ["forbes.com"]),
    (12, "Washington Examiner", ["washingtonexaminer.com"]),
    (12, "Washington Times",    ["washingtontimes.com"]),
    (13, "Breaking Defense",    ["breakingdefense.com"]),
    (13, "Defense News",        ["defensenews.com"]),
    (13, "Defense One",         ["defenseone.com"]),
    (14, "Vanity Fair",         ["vanityfair.com"]),
    (14, "Rolling Stone",       ["rollingstone.com"]),
    (14, "Business Insider",    ["businessinsider.com"]),
    (14, "TIME",                ["time.com"]),
    (14, "USA Today",           ["usatoday.com"]),
    (14, "Newsweek",            ["newsweek.com"]),
]

_DOMAIN_INDEX = {d: (rank, name) for rank, name, ds in PRIORITY_OUTLETS for d in ds}


def outlet_for(host: str):
    """(rank, outlet name) for a URL host, or None if it is not a priority outlet.

    Matches the registrable domain exactly, so cn.nytimes.com (NYT Chinese)
    and asia.nikkei.com do not pass as their parents.
    """
    host = (host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return _DOMAIN_INDEX.get(host)


# Word budget per section. Total lands near 1,000 words, a 4 to 5 minute read
# at 230 words a minute, which is Axios AM / POLITICO Playbook length.
SECTIONS = [
    # key,              title,                 half,     owner,  items,   words
    ("editors_note",    "Editor's Note",       "lede",   "human", (1, 1), 80),
    ("week_at_a_glance","Week at a Glance",    "ahead",  "human", (3, 3), 150),
    ("heard_on_the_hill","Heard on the Hill",  "back",   "human", (3, 5), 180),
    ("in_the_news",     "In the News",         "back",   "ai",    (4, 6), 250),
    ("research_roundup","Research Roundup",    "back",   "ai",    (2, 5), 150),
    ("in_the_works",    "In the Works @ CSIS", "ahead",  "sheet", (2, 4), 110),
    ("on_the_horizon",  "On the Horizon",      "ahead",  "sheet", (4, 6), 80),
]

TARGET_WORDS = 1000

# Where the weekly reads its look-back material. The China Daily Brief already
# collects 269 feeds, resolves Google News links and reads past paywalls to the
# meta description, so the weekly consumes its output instead of re-collecting.
DAILY_REPO_RAW = "https://raw.githubusercontent.com/andysaulim/Daily-China-Digest/main"
DAILY_LEDGER = DAILY_REPO_RAW + "/published_ledger.json"
DAILY_ARCHIVE = DAILY_REPO_RAW + "/public/archive.json"
DAILY_SITE = "https://andysaulim.github.io/Daily-China-Digest"

# Words that mark a ledger item as Congress-related, for the Heard on the Hill
# candidate list the comms coordinator writes from.
HILL_PATTERN = (r"\b(senat\w*|congress\w*|house speaker|speaker johnson|lawmaker\w*|"
                r"bill|hearing|committee|caucus|rep\.|sen\.|select committee|ndaa)\b")

# Taiwan and other legislatures that the Hill pattern would otherwise catch.
NOT_HILL_PATTERN = r"\b(KMT|DPP|Legislative Yuan|Diet|National Assembly|LegCo|NPC)\b"
