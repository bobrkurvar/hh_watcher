from dto import VacancyPreview
from .filters import apply_soft_filter

from scraper_engine import get_vacancies
import logging

log = logging.getLogger(__name__)


async def collect_vacancies(client, queries: list[str]) -> list[VacancyPreview]:
    unique_vacancies: dict[str, VacancyPreview] = {}
    vacancies = await get_vacancies(client=client, urls=queries, batch_size=30)
    for vacancy in vacancies:
        existing_vacancy = unique_vacancies.get(vacancy.id)
        if existing_vacancy is None:
            vacancy.hidden = not apply_soft_filter(vacancy)
            unique_vacancies[vacancy.id] = vacancy
        else:
            existing_vacancy.query_hits.update(vacancy.query_hits)
    log.debug("Всего вакансий: %s", len(unique_vacancies))
    return list(unique_vacancies.values())



