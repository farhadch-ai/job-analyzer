import re
import pandas as pd

INPUT = "results_raw.csv"      # copy of your latest results file
OUTPUT = "jobs_clean.csv"

df = pd.read_csv(INPUT)
print("Rows before cleaning:", len(df))


def norm(s):
    return re.sub(r"\W+", " ", str(s).lower()).strip()


# 1. Tidy text columns
for col in ["title", "client_problem", "source_snippet"]:
    df[col] = df[col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

# 2. Remove duplicate jobs (same title), keeping the row with more fields filled in

df["_key"] = df["title"].apply(norm)
df["_filled"] = df.notna().sum(axis=1)
df = df.sort_values("_filled", ascending=False)
dupes = df[df.duplicated("_key", keep="first")]
if len(dupes):
    print("\nDuplicates removed (check that these really are the same job):")
    for t in dupes["title"]:
        print("  -", t)
df = df.drop_duplicates("_key", keep="first").drop(columns=["_key", "_filled"]).sort_index()
print("\nRows after removing duplicates:", len(df))

# 3. Skills: lowercase, merge names for the same thing, drop vague entries
SYNONYMS = {
    "openai": "openai api", "chatgpt": "openai api", "gpt": "openai api", "chatgpt api": "openai api",
    "gpt-4": "openai api", "claude": "claude api", "anthropic": "claude api",
    "js": "javascript", "node": "node.js", "nodejs": "node.js", "reactjs": "react", "react.js": "react",
    "postgres": "postgresql", "make": "make.com", "make.com automation": "make.com",
    "web scraping": "scraping", "scrapers": "scraping", "web scraper": "scraping",
    "llm": "llms", "large language models": "llms", "n8n automation": "n8n",
}
VAGUE = {"ai", "ai development", "ai chatbot", "chatbot", "automation", "development",
         "programming", "software development", "full-stack", "api", "api integration",
         "artificial intelligence", "machine learning", "web development"}


def clean_skills(cell):
    if pd.isna(cell):
        return ""
    out = []
    for s in str(cell).split(","):
        s = SYNONYMS.get(s.strip().lower(), s.strip().lower())
        if s and s not in VAGUE and s not in out:
            out.append(s)
    return ", ".join(out)


df["skills"] = df["skills"].apply(clean_skills)

# 4. Negotiable budgets: fill with the average of real budgets of the same type
df["budget_estimated"] = False
if "budget_negotiable" in df.columns:
    neg = (df["budget_negotiable"].fillna(False).astype(bool)
           & df["budget_min"].isna() & df["budget_max"].isna()
           & df["budget_type"].notna())
    real = df[df["budget_min"].notna() & df["budget_max"].notna()]
    avg = real.groupby("budget_type")[["budget_min", "budget_max"]].mean()   # use .median() if you prefer
    for idx in df[neg].index:
        t = df.loc[idx, "budget_type"]
        if t in avg.index:
            df.loc[idx, "budget_min"] = avg.loc[t, "budget_min"]
            df.loc[idx, "budget_max"] = avg.loc[t, "budget_max"]
            df.loc[idx, "budget_estimated"] = True
    print("Negotiable budgets filled with the average:", int(df["budget_estimated"].sum()))

# 5. Budgets: midpoint of the range, plus flags for suspicious values (flagged, never deleted)
df["budget_mid"] = df[["budget_min", "budget_max"]].mean(axis=1)
df["budget_flag"] = ""
df.loc[df["budget_max"] <= 0, "budget_flag"] = "zero_or_negative"
df.loc[(df["budget_type"] == "hourly") & (df["budget_max"] > 300), "budget_flag"] = "hourly_too_high"
df.loc[(df["budget_type"] == "fixed") & (df["budget_max"] > 20000), "budget_flag"] = "fixed_very_high"
df.loc[df["budget_mid"].notna() & df["budget_type"].isna(), "budget_flag"] = "no_budget_type"

# 6. Turn "posted_ago" text into hours
UNIT_HOURS = {"second": 1 / 3600, "minute": 1 / 60, "hour": 1, "day": 24, "week": 168, "month": 720}


def to_hours(text):
    if pd.isna(text):
        return None
    t = str(text).lower()
    if "last week" in t:
        return 168.0
    if "yesterday" in t:
        return 24.0
    m = re.search(r"(\d+|an?|one)\s+(second|minute|hour|day|week|month)", t)
    if not m:
        return None
    n = 1 if m.group(1) in ("a", "an", "one") else int(m.group(1))
    return round(n * UNIT_HOURS[m.group(2)], 2)


if "posted_ago" in df.columns:
    df["posted_hours"] = df["posted_ago"].apply(to_hours)

# 7. Report
print("\nBudget flags:")
print(df["budget_flag"].replace("", "ok").value_counts())
print("\nMissing values:")
print(df.isna().sum())
print("\nTop 15 skills:")
print(df["skills"].str.split(", ").explode().replace("", pd.NA).value_counts().head(15))
print("\nProject types:")
print(df["project_type"].value_counts())

df.to_csv(OUTPUT, index=False)
print(f"\nSaved {len(df)} rows -> {OUTPUT}")