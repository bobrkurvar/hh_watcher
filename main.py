import asyncio

from dto import VacancyPreview
from filters_regex import find_title_reject_reason
from http_client import HHClient
from query_keywords import SEARCH_QUERIES



async def collect_vacancies(
    client: HHClient,
    queries: list[str],
) -> dict[str, VacancyPreview]:
    unique_vacancies: dict[str, VacancyPreview] = {}

    for query in queries:
        print(f"Поиск по запросу: {query}")

        vacancies = await client.get_vacancies(query)

        print(f"Найдено вакансий: {len(vacancies)}")

        for vacancy in vacancies:
            existing_vacancy = unique_vacancies.get(vacancy.id)

            if existing_vacancy is None:
                unique_vacancies[vacancy.id] = vacancy
                continue

            existing_vacancy.query_hits.update(vacancy.query_hits)

    return unique_vacancies


def apply_title_filter(
    vacancies: dict[str, VacancyPreview],
) -> tuple[list[VacancyPreview], list[tuple[VacancyPreview, str]]]:
    candidates: list[VacancyPreview] = []
    rejected: list[tuple[VacancyPreview, str]] = []

    for vacancy in vacancies.values():
        reason = find_title_reject_reason(vacancy.title)

        if reason is None:
            candidates.append(vacancy)
            continue

        rejected.append((vacancy, reason))

    return candidates, rejected


async def main() -> None:
    client = HHClient()

    try:
        unique_vacancies = await collect_vacancies(
            client=client,
            queries=SEARCH_QUERIES,
        )
    finally:
        await client.close()

    candidates, rejected = apply_title_filter(unique_vacancies)

    print("\n--- Итог ---")
    print(f"Уникальных вакансий: {len(unique_vacancies)}")
    print(f"Отклонено title-фильтром: {len(rejected)}")
    print(f"Осталось для следующего этапа: {len(candidates)}")

    print("\n--- Отклонённые вакансии ---")

    for vacancy, reason in rejected:
        print(f"- [{reason}] {vacancy.title}")

    print("\n--- Кандидаты ---")

    for vacancy in candidates[:50]:
        query_hits = ", ".join(sorted(vacancy.query_hits))
        employer = vacancy.employer_name or "Не указан"

        print(
            f"\n{vacancy.title}"
            f"\nКомпания: {employer}"
            f"\nНайдена по: {query_hits}"
            f"\nСсылка: {vacancy.url}"
        )


if __name__ == "__main__":
    asyncio.run(main())

