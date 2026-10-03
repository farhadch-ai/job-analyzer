import os, re, json, time
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError
from schema import JobRecord

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"
INPUT_FILE = "data/job_01.txt"
CHUNK_SIZE = 14000    # characters per slice
OVERLAP = 6000        # must be longer than your longest post
MAX_TRIES = 3

ITEM_SCHEMA = json.dumps(JobRecord.model_json_schema(), indent=2)

SYSTEM = f"""You will receive a slice of a messy text file containing many freelance job posts pasted together.
Extract EVERY job post in the text. Return ONLY a JSON object: {{"jobs": [ ... ]}}
Each item must match this JSON schema:
{ITEM_SCHEMA}

Rules:
- One item per job post. Do not merge two posts and do not skip any.
- The text is a slice of a larger file. Skip a post if its beginning is cut off at the very start of the text.
- Use null for anything not stated in the post. Never guess.
- title must be copied exactly as written in the post.
- source_snippet must be the first 8 to 10 words of the job title or description, copied exactly.
  Never use a line about pay, hourly rate, experience level, or estimated time.
- budget_min and budget_max must be numbers only, with no currency symbols or commas.
- For a range like "$10-25/hr", set budget_min to 10 and budget_max to 25. Never pick just one end of a range.
- For a single value like "$500", set both budget_min and budget_max to 500.
- For "up to $500", set budget_min to null and budget_max to 500.
- If the post says pay is negotiable, open, flexible, or to be discussed, with no number,
  set budget_negotiable to true and leave budget_min and budget_max null.
- Copy posted_ago exactly as written, if present.
- Use the allowed values for project_type, budget_type and experience_level exactly as listed.
- If there are no complete job posts in the text, return {{"jobs": []}}.
- Output JSON only, with no extra text."""

tokens = {"in": 0, "out": 0}


def norm(s):
    return re.sub(r"\W+", " ", str(s).lower()).strip()


def chunk_text(text):
    chunks, step, i = [], CHUNK_SIZE - OVERLAP, 0
    while i < len(text):
        chunks.append(text[i:i + CHUNK_SIZE])
        if i + CHUNK_SIZE >= len(text):
            break
        i += step
    return chunks


def call_model(messages):
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=MODEL, messages=messages, temperature=0,
                response_format={"type": "json_object"})
            tokens["in"] += r.usage.prompt_tokens
            tokens["out"] += r.usage.completion_tokens
            return r.choices[0].message.content
        except Exception as e:
            print("  API error, retrying:", e)
            time.sleep(2 ** attempt)
    raise RuntimeError("API failed 3 times")


def extract_chunk(chunk):
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": chunk}]
    valid, errors = [], []
    for attempt in range(MAX_TRIES):
        raw = call_model(messages)
        valid, errors = [], []
        try:
            items = json.loads(raw).get("jobs", [])
        except json.JSONDecodeError as e:
            items, errors = [], [f"Reply was not valid JSON: {e}"]
        for idx, item in enumerate(items):
            try:
                valid.append(JobRecord.model_validate(item))
            except ValidationError as e:
                errors.append(f"Job {idx}: {e}")
        if not errors:
            return valid, []
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content":
             'Some items failed validation. Return the full corrected {"jobs": [...]} list, '
             "including the valid ones.\n" + "\n".join(errors)},
        ]
    return valid, errors


def key_of(record):
    # title + first words of the snippet identify a job, even if budget details differ between slices
    snippet_words = norm(record.source_snippet).split()[:5]
    return norm(record.title) + "|" + " ".join(snippet_words)


def filled(record):
    return sum(v not in (None, [], "", False) for v in record.model_dump().values())


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"File: {len(text)} characters -> {len(chunks)} slices")

    jobs, failed, dropped = {}, [], 0
    for n, chunk in enumerate(chunks, start=1):
        records, errors = extract_chunk(chunk)

        # drop any record whose snippet cannot be found in this slice (possible invention)
        chunk_norm = norm(chunk)
        verified = [r for r in records if norm(r.source_snippet) in chunk_norm]
        dropped += len(records) - len(verified)

        print(f"Slice {n}/{len(chunks)}: {len(verified)} jobs, {len(errors)} errors, "
              f"{len(records) - len(verified)} dropped")
        failed += errors
        for r in verified:
            k = key_of(r)
            if k not in jobs or filled(r) > filled(jobs[k]):   # keep the fuller copy
                jobs[k] = r

    rows = []
    for r in jobs.values():
        d = r.model_dump()
        d["skills"] = ", ".join(d["skills"])
        rows.append(d)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_file = f"results_{stamp}.csv"
    pd.DataFrame(rows).to_csv(out_file, index=False)
    with open(f"failed_{stamp}.json", "w", encoding="utf-8") as f:
        json.dump(failed, f, indent=2)

    print("\n--- SUMMARY ---")
    print("Unique jobs saved:", len(jobs), "->", out_file)
    print("Records dropped (snippet not found in slice):", dropped)
    print("Validation errors left:", len(failed), f"-> failed_{stamp}.json")
    print("Tokens in/out:", tokens["in"], tokens["out"])


if __name__ == "__main__":
    main()