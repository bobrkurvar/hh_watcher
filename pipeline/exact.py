from dto import VacancyPreview
from .filters import apply_soft_filter

import asyncio
import logging

log = logging.getLogger(__name__)


async def collect_vacancies(client, queries: list[str]) -> list[VacancyPreview]:
    unique_vacancies: dict[str, VacancyPreview] = {}

    for query in queries:
        log.debug("Поиск по запросу: %s", query)
        vacancies = await client.get_vacancies(query)
        #log.debug("Найдено вакансий: %s", len(vacancies))

        for vacancy in vacancies:
            existing_vacancy = unique_vacancies.get(vacancy.id)

            if existing_vacancy is None:
                vacancy.hidden = not apply_soft_filter(vacancy)
                unique_vacancies[vacancy.id] = vacancy
                continue

            existing_vacancy.query_hits.update(vacancy.query_hits)
    log.debug("Всего вакансий: %s", len(unique_vacancies))
    return list(unique_vacancies.values())



# async def execute_tasks(
#     client,
#     vacancies_batch: list[VacancyPreview],
#     exception_results: list[VacancyPreview],
#     success_results: list[VacancyPreview]
# ):
#     vacancies_tasks = [asyncio.create_task(client.get_vacancy(vacancy.id)) for vacancy in vacancies_batch]
#     result = await asyncio.gather(*vacancies_tasks, return_exceptions=True)
#     new_batch_size = 0
#     for batch_vacancy, task_res in zip(vacancies_batch, result):
#         if isinstance(task_res, Exception):
#             exception_results.append(batch_vacancy)
#         else:
#             new_batch_size += 1
#             success_results.append(batch_vacancy)
#     vacancies_batch.clear()
#     return new_batch_size

# async def load_batch(client, vacancies: list[VacancyPreview], batch_size: int = 5):
#     success_results, exception_results, vacancies_batch = [], [], []
#     for vacancy in vacancies:
#         vacancies_batch.append(vacancy)
#         if len(vacancies_batch) == batch_size:
#             vacancies_tasks = [asyncio.create_task(client.get_vacancy(vacancy.id)) for vacancy in vacancies_batch]
#             result = await asyncio.gather(*vacancies_tasks, return_exceptions=True)
#             new_batch_size = 0
#             for batch_vacancy, task_res in zip(vacancies_batch, result):
#                 if isinstance(task_res, Exception):
#                     exception_results.append(batch_vacancy)
#                 else:
#                     new_batch_size += 1
#                     success_results.append(task_res)
#             batch_size = new_batch_size or 1
#             vacancies_batch.clear()
#     summary_len = len(success_results) + len(exception_results)
#     if (elems_count := len(vacancies) - summary_len) != 0:
#         success_results += await load_batch(client=client, vacancies=vacancies[summary_len: summary_len+elems_count], batch_size=elems_count)
#
#     if exception_results:
#         success_results += await load_batch(client=client, vacancies=exception_results, batch_size=batch_size)
#     return success_results

async def load_batch(client, vacancies: list[VacancyPreview], batch_size: int = 5, static: bool = False):
    pending, successful_results = vacancies, []
    max_size = batch_size if static else None
    while pending:
        successful_count = 0
        rate_limit_hit = False
        batch = pending[:batch_size]
        items_to_retry = []
        task_to_vacancy = {
            asyncio.create_task(client.get_vacancy(vacancy.id)): vacancy
            for vacancy in batch
        }
        done, pending_tasks = await asyncio.wait(task_to_vacancy.keys(), return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            try:
                result = task.result()
                successful_results.append(result)
                successful_count += 1
            except Exception:
                rate_limit_hit = True
                items_to_retry.append(task_to_vacancy[task])
        for task in pending_tasks:
            task.cancel()
            items_to_retry.append(task_to_vacancy[task])
        # Гасим предупреждения об отмененных задачах - после cancel сами запросы не выполнятся, просто graceful shutdown для cancell
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        if rate_limit_hit:
            max_size = successful_count or 1
        pending = items_to_retry + pending[batch_size:]
        batch_size = max_size if max_size is not None else batch_size + 2
        sleep_time = 1 if rate_limit_hit else 0.3
        await asyncio.sleep(sleep_time)
    return successful_results