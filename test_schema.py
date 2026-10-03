from pydantic import ValidationError
from schema import JobPost

replies = {
    "good": """{"title": "Scrape store prices", "project_type": "scraping",
                "skills": ["Python", "BeautifulSoup"], "budget_amount": 150,
                "budget_type": "fixed", "client_problem": "Needs competitor prices tracked daily",
                "experience_level": "intermediate"}""",

    "wrong_values": """{"title": "Scrape store prices", "project_type": "web scraping",
                "skills": ["Python"], "budget_amount": "about 150",
                "budget_type": "fixed", "client_problem": "Needs prices tracked"}""",

    "missing_boxes": """{"project_type": "scraping", "skills": ["Python"]}""",
}

for name, reply in replies.items():
    print(f"--- {name} ---")
    try:
        job = JobPost.model_validate_json(reply)
        print("VALID:", job.title, "|", job.project_type, "|", job.budget_amount)
    except ValidationError as e:
        print("INVALID")
        print(e)