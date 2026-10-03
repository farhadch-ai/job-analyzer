import re
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator, model_validator


class JobPost(BaseModel):
    title: str = Field(
        description="Title of the job, copied exactly as written in the text")

    project_type: Literal["scraping", "chatbot", "automation", "data_analysis", "web_app", "other"] = Field(
        description="Best matching type of project")

    skills: List[str] = Field(
        description="Specific tools, languages and technologies mentioned in the post "
                    "(for example Python, n8n, OpenAI API). Do not include vague terms like 'AI' or 'automation'")

    budget_min: Optional[float] = Field(
        default=None,
        description="Lowest budget or rate as a number, or null if not stated")

    budget_max: Optional[float] = Field(
        default=None,
        description="Highest budget or rate as a number, or null if not stated")

    budget_type: Optional[Literal["fixed", "hourly"]] = Field(
        default=None,
        description="fixed or hourly, or null if not stated")

    budget_negotiable: bool = Field(
        default=False,
        description="true only if the post says the pay is negotiable, open, flexible or to be discussed "
                    "and gives no number; otherwise false")

    client_problem: str = Field(
        description="The client's problem in one sentence")

    experience_level: Optional[Literal["beginner", "intermediate", "expert"]] = Field(
        default=None,
        description="Experience level asked for, or null if not stated")

    posted_ago: Optional[str] = Field(
        default=None,
        description="How long ago the job was posted, exactly as written in the text "
                    "(for example '3 hours ago'), or null if not stated")

    @model_validator(mode="after")
    def check_budget_range(self):
        if (self.budget_min is not None and self.budget_max is not None
                and self.budget_min > self.budget_max):
            raise ValueError("budget_min must not be greater than budget_max")
        return self


class JobRecord(JobPost):
    source_snippet: str = Field(
        description="The first 8 to 10 words of this job post's title or description, copied exactly. "
                    "Never use a line about pay, hourly rate, experience level, or estimated time.")

    @field_validator("source_snippet")
    @classmethod
    def snippet_not_metadata(cls, v):
        starts_bad = re.match(
            r"\s*(hourly|fixed|est\.?\s*time|expert|intermediate|entry level|posted|\$)", v, re.I)
        if starts_bad or len(v.split()) < 5:
            raise ValueError(
                "source_snippet must be the first words of the job title or description, "
                "not a pay, experience level, or time line")
        return v