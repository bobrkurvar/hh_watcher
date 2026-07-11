from dto import VacancyPreview
from .filters import apply_soft_filter

from scraper_engine import get_vacancies
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


async def collect_vacancies(client, queries: list[str]) -> list[VacancyPreview]:
    unique_vacancies: dict[str, VacancyPreview] = {}
    areas = await client.get_areas()
    area_id = find_area_id(areas=areas, city_name="Воронеж")
    if area_id is None:
        raise ValueError("Город Воронеж не найден в справочнике HH")
    vacancies = await get_vacancies(client=client, urls=queries, batch_size=30, static=True, area_id=area_id)
    for vacancy in vacancies:
        existing_vacancy = unique_vacancies.get(vacancy.id)
        if existing_vacancy is None:
            vacancy.hidden = not apply_soft_filter(vacancy)
            unique_vacancies[vacancy.id] = vacancy
        else:
            existing_vacancy.query_hits.update(vacancy.query_hits)
    log.debug("Всего вакансий: %s", len(unique_vacancies))
    return list(unique_vacancies.values())



