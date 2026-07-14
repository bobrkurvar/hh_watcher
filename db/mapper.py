import dto
from db import models
from sqlalchemy import inspect
from datetime import datetime

def parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def map_ai_analysis_to_orm(obj: dto.AIAnalysis) -> models.AIAnalysis:
    return models.AIAnalysis(
        vacancy_id=obj.vacancy_id,
        explanation=obj.explanation,
        confidence=obj.confidence,
        is_relevant=obj.is_relevant
    )


def map_ai_analysis_to_dto(obj: models.AIAnalysis) -> dto.AIAnalysis:
    return dto.AIAnalysis(
        vacancy_id=obj.vacancy_id,
        explanation=obj.explanation,
        confidence=obj.confidence,
        is_relevant=obj.is_relevant
    )


def map_vacancy_details_to_orm(obj: dto.VacancyDetails) -> models.VacancyDetails:
    return models.VacancyDetails(
        vacancy_id=None,
        description=obj.description,
        salary_from=obj.salary_from,
        salary_to=obj.salary_to,
        salary_currency=obj.salary_currency,
        experience=obj.experience,
        employment=obj.employment,
        schedule=obj.schedule,
        key_skills=obj.key_skills,
        work_formats=obj.work_formats,
    )


def map_vacancy_details_to_dto(obj: models.VacancyDetails) -> dto.VacancyDetails:
    return dto.VacancyDetails(
        description=obj.description,
        salary_from=obj.salary_from,
        salary_to=obj.salary_to,
        salary_currency=obj.salary_currency,
        experience=obj.experience,
        employment=obj.employment,
        schedule=obj.schedule,
        key_skills=obj.key_skills,
        work_formats=obj.work_formats,
    )

def map_vacancy_to_orm(obj: dto.Vacancy) -> models.Vacancy:
    preview = obj.preview

    return models.Vacancy(
        id=obj.id,
        external_id=preview.id,
        is_hidden=obj.is_hidden,
        title=preview.title,
        url=preview.url,
        employer_name=preview.employer_name,
        published_at=parse_datetime(preview.published_at),
        requirement=preview.requirement,
        responsibility=preview.responsibility,
        query_hits=list(preview.query_hits),
        details=(
            map_vacancy_details_to_orm(obj.details)
            if obj.details is not None
            else None
        ),
        ai_analysis=(
            map_ai_analysis_to_orm(obj.ai_analysis)
            if obj.ai_analysis is not None
            else None
        ),
    )


def map_vacancy_to_dto(obj: models.Vacancy) -> dto.Vacancy:
    unloaded = inspect(obj).unloaded

    details = None
    if "details" not in unloaded and obj.details is not None:
        details = map_vacancy_details_to_dto(obj.details)

    ai_analysis = None
    if "ai_analysis" not in unloaded and obj.ai_analysis is not None:
        ai_analysis = map_ai_analysis_to_dto(obj.ai_analysis)

    return dto.Vacancy(
        id=obj.id,
        is_hidden=obj.is_hidden,
        preview=dto.VacancyPreview(
            id=obj.external_id,
            title=obj.title,
            url=obj.url,
            employer_name=obj.employer_name,
            published_at=obj.published_at,
            requirement=obj.requirement,
            responsibility=obj.responsibility,
            query_hits=set(obj.query_hits),
            hidden=False,
        ),
        details=details,
        ai_analysis=ai_analysis,
    )



class MapperRegistry:
    def __init__(self):
        self._models = {}
        self._to_orm_funcs = {}
        self._to_dto_funcs = {}

    def register(self, dto_cls, orm_model, to_orm, to_dto):
        self._models[dto_cls] = orm_model
        self._to_orm_funcs[dto_cls] = to_orm
        self._to_dto_funcs[orm_model] = to_dto

    def get_model(self, dto_cls):
        return self._models[dto_cls]

    def to_orm(self, dto_obj):
        dto_cls = type(dto_obj)
        func = self._to_orm_funcs.get(dto_cls)
        if not func:
            raise RuntimeError(f"Маппер в ORM не найден для {dto_cls}")
        return func(dto_obj)

    def to_dto(self, orm_obj):
        orm_cls = type(orm_obj)
        func = self._to_dto_funcs.get(orm_cls)
        if not func:
            raise RuntimeError(f"Маппер в Домен не найден для {orm_cls}")
        return func(orm_obj)


registry = MapperRegistry()
registry.register(
    dto_cls=dto.Vacancy,
    orm_model=models.Vacancy,
    to_orm=map_vacancy_to_orm,
    to_dto=map_vacancy_to_dto,
)

registry.register(
    dto_cls=dto.VacancyDetails,
    orm_model=models.VacancyDetails,
    to_orm=map_vacancy_details_to_orm,
    to_dto=map_vacancy_details_to_dto,
)

registry.register(
    dto_cls=dto.AIAnalysis,
    orm_model=models.AIAnalysis,
    to_orm=map_ai_analysis_to_orm,
    to_dto=map_ai_analysis_to_dto,
)