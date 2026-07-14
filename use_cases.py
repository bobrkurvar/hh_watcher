from dto import Vacancy
from pipeline.exact import collect_vacancies_pipeline

async def load_vacancies(client, uow, queries: list[str], llm) -> tuple[Vacancy, ...]:
    await collect_vacancies_pipeline(uow=uow, client=client, queries=queries, llm=llm)
    return await uow.db.read(Vacancy)