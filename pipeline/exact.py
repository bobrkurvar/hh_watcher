from dto import VacancyPreview, VacancyDetails, Vacancy
from .filters import passes_vacancy_preview_filter, passes_vacancy_details_filter

from scraper_engine import get_vacancies, get_vacancies_details
import logging

log = logging.getLogger(__name__)


def find_area_id(areas: list[dict], city_name: str) -> str | None:
    for area in areas:
        if area["name"].casefold() == city_name.casefold():
            return area["id"]
        found_id = find_area_id(area.get("areas", []), city_name)
        if found_id is not None:
            return found_id
    return None


async def collect_vacancies_previews(client, queries: list[str]) -> list[VacancyPreview]:
    unique_vacancies: dict[str, VacancyPreview] = {}
    areas = await client.get_areas()
    area_id = find_area_id(areas=areas, city_name="Воронеж")
    if area_id is None:
        raise ValueError("Город Воронеж не найден в справочнике HH")
    vacancies = await get_vacancies(
        client=client, urls=queries, batch_size=10, area_id=area_id
    )
    for vacancy in vacancies:
        existing_vacancy = unique_vacancies.get(vacancy.id)
        if existing_vacancy is None:
            vacancy.hidden = not passes_vacancy_preview_filter(vacancy)
            unique_vacancies[vacancy.id] = vacancy
        else:
            existing_vacancy.query_hits.update(vacancy.query_hits)
    log.debug("Всего вакансий: %s", len(unique_vacancies))
    return list(unique_vacancies.values())


async def collect_vacancies_pipeline(uow, client, queries: list[str], llm) -> list[Vacancy]:
    previews = await collect_vacancies_previews(client=client, queries=queries)
    async with uow:
        vacancies_in_db = await uow.db.read(Vacancy)
    vacancies_in_db_ids = set(vacancy.preview.id for vacancy in vacancies_in_db)
    all_vacancies, previews_to_detail, pending_to_analysis = [], [], []
    for preview in previews:
        if preview.id not in vacancies_in_db_ids:
            if preview.hidden:
                all_vacancies.append(Vacancy(preview=preview, is_hidden=True))
            else:
                previews_to_detail.append(preview)
    result = await get_vacancies_details(client=client, previews=previews_to_detail, batch_size=30)
    for preview, details in result:
        is_hidden = not passes_vacancy_details_filter(
            title=preview.title,
            description=details.description,
            key_skills=details.key_skills,
        )
        vacancy = Vacancy(preview=preview, details=details, is_hidden=is_hidden)
        all_vacancies.append(vacancy)
        if not is_hidden:
            pending_to_analysis.append(vacancy)
    analyses = await llm.analyze_vacancies(vacancies=pending_to_analysis)
    for vacancy, analysis in zip(pending_to_analysis, analyses):
        if analysis is None:
            log.critical("Нет анализа для данной работы: %s", vacancy)
            vacancy.is_hidden = True
            continue
        vacancy.ai_analysis = analysis
        vacancy.is_hidden = not analysis.is_relevant
    if all_vacancies:
        async with uow:
            await uow.db.create(seq_data=all_vacancies)

    return all_vacancies


