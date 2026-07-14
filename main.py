import asyncio
from adapters.http_client import HHClient
from literals.query_keywords import SEARCH_QUERIES
from pipeline.exact import collect_vacancies_pipeline
from core.logger import setup_logging

setup_logging()


async def main() -> None:
    client = HHClient()

    try:
        vacancies = await collect_vacancies_pipeline(
            client=client, queries=SEARCH_QUERIES
        )
    finally:
        await client.close()

    print("\n--- Итог ---")
    print(f"Уникальных вакансий: {len(vacancies)}")


if __name__ == "__main__":
    asyncio.run(main())
