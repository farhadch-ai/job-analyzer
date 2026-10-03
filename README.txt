Freelance Job Post Analyzer

This is my first real Python project. I wanted to know what clients on freelance sites actually ask for, so I copied a bunch of public job posts into one big text file and built a tool that reads the mess, pulls out the useful details, and shows me patterns: what kinds of projects come up most, which skills are in demand, and what people tend to pay.

I built it while learning to work with the OpenAI API, so a lot of the decisions below come from things that went wrong the first time.

**Tools used:** Python, OpenAI API, Pydantic, pandas

## What it does

1. Reads one long text file full of pasted job posts (no neat formatting needed).
2. Pulls out details from each post: title, type of project, skills, budget, experience level, and so on.
3. Checks every result against a set of rules, and asks the model to fix its own answer if something is wrong.
4. Cleans up the data (duplicates, different spellings of the same skill, odd budgets).
5. Prints simple stats so I can see where the demand is.

## How it works

The file was too long and messy to split by hand, so I did this instead:

```
messy text file
      |
      v
cut into overlapping slices
      |
      v
ask the model to list every job it sees in each slice (as JSON)
      |
      v
check the JSON with Pydantic, retry up to 3 times if it's wrong
      |
      v
remove jobs that showed up twice because of the overlap
      |
      v
save to CSV -> clean_data.py -> analyze.py
```

**Why overlapping slices?** If I cut the file into separate pieces, a job that sits on the edge gets split in half and lost. Overlapping the slices means that job shows up whole in the next one. The prompt tells the model to skip any job that is cut off at the start of a slice. Duplicates are removed afterward using the first words of each post.

## Files

| File | What it does |
|---|---|
| `schema.py` | Defines the fields I want to extract and the rules for them (Pydantic) |
| `extract_all.py` | Slices the file, calls the model, validates, retries, removes duplicates, saves a CSV |
| `clean_data.py` | Tidies text, merges skill names, flags strange budgets |
| `analyze.py` | Prints project type counts, top skills, and budget stats |
| `test_schema.py` | Tests the schema with fake good and bad replies (free, no API call) |

## What gets extracted

`title`, `project_type`, `skills`, `budget_min`, `budget_max`, `budget_type` (fixed or hourly), `client_problem`, `experience_level`, `posted_ago`, and `source_snippet` (the first few words of the post, which I use to remove duplicates and to find the original text again).

If something isn't in the post, it's left empty. I told the model not to guess.

## Setup

```bash
git clone <your-repo-url>
cd job-analyzer
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then add your OpenAI API key to .env
```

## How to run it

1. Put your job posts in `data/job_01.txt` (this folder isn't uploaded to GitHub).
2. `python extract_all.py`
3. `python clean_data.py`
4. `python analyze.py`



## Cost

One run on a file of about 178,000 characters (around 50 job posts) used roughly 112,000 input tokens and 12,600 output tokens with `gpt-4o-mini`. That works out to a few cents.

## Results

> **[FILL IN after final run and manual check]**

- Jobs found: **[number]**
- I checked **[number]** random rows against the original posts and **[number]** were fully correct.
- Most common project types: **[list]**
- Most requested skills: **[list]**
- Typical budgets: **[fixed median, hourly median, and how many jobs each is based on]**
- What this suggests for choosing a niche: **[1-2 sentences]**



## Limitations

- The sample is small (about 50 posts) and I picked it using my own search terms, so these are patterns, not facts about the whole market.
- Many posts don't mention a budget, so the budget stats only cover some of them.
- The duplicate removal uses the first words of each post, so a job described slightly differently in two slices could be counted twice.
- I copied the posts by hand from public listings and left out client names and contact details. The raw text isn't in this repository.

## Privacy

Only public job posts were used. 

