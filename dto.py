from dataclasses import dataclass

@dataclass
class VacancyPreview:
    id: str
    title: str
    url: str
    employer_name: str | None
    published_at: str | None
    requirement: str | None
    responsibility: str | None
    query_hits: set[str]
    hidden: bool = False

    @classmethod
    def from_api(
        cls,
        payload: dict,
        query: str,
    ) -> "VacancyPreview":
        employer = payload.get("employer") or {}
        snippet = payload.get("snippet") or {}

        return cls(
            id=payload["id"],
            title=payload["name"],
            url=payload["alternate_url"],
            employer_name=employer.get("name"),
            published_at=payload.get("published_at"),
            requirement=snippet.get("requirement"),
            responsibility=snippet.get("responsibility"),
            query_hits={query},
        )


@dataclass(slots=True)
class VacancyDetails:
    id: str
    title: str
    description: str

    employer_name: str | None
    published_at: str | None

    salary_from: int | None
    salary_to: int | None
    salary_currency: str | None

    experience: str | None
    employment: str | None
    schedule: str | None

    key_skills: list[str]
    work_formats: list[str]

    @classmethod
    def from_api(cls, payload: dict[str, ...]) -> "VacancyDetails":
        employer = payload.get("employer") or {}
        salary = payload.get("salary") or {}
        experience = payload.get("experience") or {}
        employment = payload.get("employment") or {}
        schedule = payload.get("schedule") or {}

        return cls(
            id=payload["id"],
            title=payload["name"],
            description=payload.get("description") or "",
            employer_name=employer.get("name"),
            published_at=payload.get("published_at"),
            salary_from=salary.get("from"),
            salary_to=salary.get("to"),
            salary_currency=salary.get("currency"),
            experience=experience.get("name"),
            employment=employment.get("name"),
            schedule=schedule.get("name"),
            key_skills=[
                skill["name"]
                for skill in payload.get("key_skills", [])
                if skill.get("name")
            ],
            work_formats=[
                work_format["name"]
                for work_format in payload.get("work_format", [])
                if work_format.get("name")
            ],
        )