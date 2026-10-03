import pandas as pd

df = pd.read_csv("jobs_clean.csv")
df["budget_flag"] = df["budget_flag"].fillna("")
df["budget_estimated"] = df["budget_estimated"].fillna(False).astype(bool)
total = len(df)
print("Jobs analyzed:", total)


def explode_skills(frame):
    return (frame["skills"].fillna("").str.split(", ")
            .explode().replace("", pd.NA).dropna())


# 1. Project types
print("\n1. PROJECT TYPES")
counts = df["project_type"].value_counts()
print(pd.DataFrame({"jobs": counts, "percent": (counts / total * 100).round(1)}))

# 2. Most requested skills
print("\n2. TOP 20 SKILLS (number of jobs mentioning each)")
skill_counts = explode_skills(df).value_counts()
print(skill_counts.head(20))
skill_counts.to_csv("top_skills.csv", header=["jobs"])

# 3. Budgets (flagged and estimated budgets are left out)
print("\n3. BUDGETS")
print("No budget stated:", int(df["budget_mid"].isna().sum()), "of", total)
print("Negotiable (average filled in, not used below):", int(df["budget_estimated"].sum()))
budget = df[(df["budget_flag"] == "") & (~df["budget_estimated"])].dropna(subset=["budget_mid", "budget_type"])
print("Jobs used for budget stats:", len(budget))

print("\nBy payment type (median values):")
by_type = budget.groupby("budget_type").agg(
    jobs=("budget_mid", "count"),
    median_min=("budget_min", "median"),
    median_max=("budget_max", "median"),
    median_mid=("budget_mid", "median"),
    lowest=("budget_min", "min"),
    highest=("budget_max", "max"),
).round(1)
print(by_type)

print("\nBy payment type and project type (groups under 3 jobs are weak evidence):")
by_both = budget.groupby(["budget_type", "project_type"]).agg(
    jobs=("budget_mid", "count"),
    median_mid=("budget_mid", "median"),
    lowest=("budget_min", "min"),
    highest=("budget_max", "max"),
).round(1)
by_both["note"] = by_both["jobs"].apply(lambda n: "few jobs" if n < 3 else "")
print(by_both)

# 4. Top skills inside the 3 biggest project types
print("\n4. TOP SKILLS PER PROJECT TYPE")
for t in df["project_type"].value_counts().head(3).index:
    sub = df[df["project_type"] == t]
    print(f"\n'{t}' ({len(sub)} jobs):")
    print(explode_skills(sub).value_counts().head(8))

# 5. Experience level
print("\n5. EXPERIENCE LEVEL")
print(df["experience_level"].value_counts(dropna=False))
exp_budget = budget.groupby(["budget_type", "experience_level"]).agg(
    jobs=("budget_mid", "count"), median_mid=("budget_mid", "median")).round(1)
print("\nMedian budget by experience level:")
print(exp_budget)

# 6. How fresh are the posts
if "posted_hours" in df.columns:
    print("\n6. POSTED TIME")
    print("Median hours since posting:", df["posted_hours"].median())
    print("Posted within 24 hours:", int((df["posted_hours"] <= 24).sum()), "of", int(df["posted_hours"].notna().sum()))

# 7. Real client problems from the biggest project type
top_type = df["project_type"].value_counts().index[0]
pool = df[df["project_type"] == top_type]
print(f"\n7. SAMPLE CLIENT PROBLEMS ('{top_type}')")
for p in pool.sample(min(8, len(pool)), random_state=1)["client_problem"]:
    print("-", p)