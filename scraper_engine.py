import asyncio
from functools import partial
import logging
from dto import VacancyPreview

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
    # tasks_to_run = [
    #     partial(client.get_vacancy, vac.id)
    #     for vac in vacancies
    # ]
    # такого рода фабрики передаются в cors потому что при cancel корутина умирает
    pending, successful_results = factories, []
    max_size = batch_size if static else None
    while pending:
        successful_count, rate_limit_hit, items_to_retry, batch = (
            0,
            False,
            [],
            pending[:batch_size],
        )
        task_to_factory = {asyncio.create_task(factory()): factory for factory in batch}
        done, pending_tasks = await asyncio.wait(
            task_to_factory.keys(), return_when=asyncio.FIRST_EXCEPTION
        )
        for task in done:
            try:
                result = task.result()
                successful_results.append(result)
                successful_count += 1
            except Exception:
                rate_limit_hit = True
                items_to_retry.append(task_to_factory[task])
        for task in pending_tasks:
            task.cancel()
            items_to_retry.append(task_to_factory[task])
        # Гасим предупреждения об отмененных задачах - после cancel сами запросы не выполнятся, просто graceful shutdown для cancell
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        if rate_limit_hit:
            max_size = successful_count or 1
            log.debug("max request size: %s", max_size)
        pending = items_to_retry + pending[batch_size:]
        batch_size = max_size if max_size is not None else batch_size + 2
        sleep_time = 2 if rate_limit_hit else 1
        await asyncio.sleep(sleep_time)
    return successful_results
