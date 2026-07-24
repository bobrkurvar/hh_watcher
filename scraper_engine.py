import asyncio
from functools import partial
import logging
from dto import VacancyPreview
from exceptions import RateLimitError, ResourceNotFoundError

log = logging.getLogger(__name__)


async def get_vacancies(client, urls: list[str], batch_size: int = 10, **params):
    tasks_to_run = [partial(client.get_vacancies, url, **params) for url in urls]
    batches = await execute_batch(tasks_to_run, batch_size, static=False)
    return [vacancy for batch in batches for vacancy in batch]


async def get_vacancies_details(client, previews: list[VacancyPreview], batch_size: int = 10):
    async def exact_with_context(vacancy: VacancyPreview):
        return vacancy, await client.get_vacancy(vacancy.id)

    factories = [partial(exact_with_context, preview) for preview in previews]
    return await execute_batch(factories, batch_size=batch_size, static=True)




async def execute_batch(factories: list, batch_size: int = 10, static: bool = False):
    pending = factories
    successful_results = []

    max_size = batch_size if static else None

    while pending:
        successful_count = 0
        rate_limit_hit = False
        items_to_retry = []

        batch = pending[:batch_size]

        results = await asyncio.gather(
            *(factory() for factory in batch),
            return_exceptions=True,
        )

        for factory, result in zip(batch, results):
            if isinstance(result, RateLimitError):
                rate_limit_hit = True
                items_to_retry.append(factory)

            elif isinstance(result, Exception):
                log.warning(
                    "Ошибка выполнения задачи %s: %s",
                    factory,
                    result,
                    exc_info=(type(result), result, result.__traceback__),
                )

            else:
                successful_results.append(result)
                successful_count += 1

        if rate_limit_hit:
            max_size = successful_count or 1

        pending = items_to_retry + pending[batch_size:]
        batch_size = max_size if max_size is not None else batch_size + 2
        sleep_time = 1 if rate_limit_hit else 0.3
        await asyncio.sleep(sleep_time)

    return successful_results

