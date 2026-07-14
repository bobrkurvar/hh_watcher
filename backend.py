import asyncio
import threading

from adapters.db_provider import DbProvider
from adapters.llm import GeminiAnalyzer
from adapters.uow import UnitOfWork
from adapters.http_client import HttpClient
from core import conf
from db.mapper import registry
from dto import Vacancy
from use_cases import load_vacancies


class AsyncBackend:
    def __init__(self, queries: list[str]):
        self.queries = queries

        self.loop = asyncio.new_event_loop()
        self.client = None
        self.llm = None
        self._db_provider = None
        self.uow = None

        self.is_ready = threading.Event()

        self.thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
        )
        self.thread.start()

    def _run_event_loop(self) -> None:
        asyncio.set_event_loop(self.loop)

        self.client = HttpClient()
        self.llm = GeminiAnalyzer()
        self._db_provider = DbProvider(url=conf.db_url)
        self.uow = UnitOfWork(
            registry=registry,
            provider=self._db_provider,
        )

        self.is_ready.set()
        self.loop.run_forever()

    def run_task(self, coro, callback) -> None:
        """
        Передаёт корутину в asyncio loop фонового потока.

        Переданный callback тоже вызывается в фоновом потоке.
        Если результат нужен Tkinter, callback должен только положить
        готовый вызов в callback_queue приложения.
        """

        def done_callback(future) -> None:
            try:
                result = future.result()
            except Exception as error:
                result = error

            callback(result)

        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        future.add_done_callback(done_callback)

    def load_vacancies(self, callback) -> None:
        """
        Получает новые вакансии с HH, сохраняет их в БД
        и возвращает вакансии из БД.
        """

        async def task_wrapper():
            return await load_vacancies(
                client=self.client,
                uow=self.uow,
                queries=self.queries,
                llm=self.llm,
            )

        self.run_task(
            task_wrapper(),
            callback,
        )

    def read_vacancies(self, callback) -> None:
        """
        Читает сохранённые вакансии без запросов к HH и Gemini.
        """

        async def task_wrapper():
            async with self.uow:
                return await self.uow.db.read(
                    Vacancy,
                    hidden=False,
                    loaded="ai_analysis",
                )

        self.run_task(
            task_wrapper(),
            callback,
        )

    def update_hidden(
        self,
        vacancy_id: int,
        hidden: bool,
        callback,
    ) -> None:
        async def task_wrapper():
            async with self.uow:
                return await self.uow.db.update(
                    Vacancy,
                    {"id": vacancy_id},
                    hidden=hidden,
                )

        self.run_task(
            task_wrapper(),
            callback,
        )

    async def _shutdown_resources(self) -> None:
        tasks = [
            task
            for task in asyncio.all_tasks()
            if task is not asyncio.current_task()
        ]

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        if self.client is not None:
            await self.client.close()

        if self._db_provider is not None:
            await self._db_provider.close()

    def stop(self) -> None:
        if not self.loop.is_running():
            return

        future = asyncio.run_coroutine_threadsafe(
            self._shutdown_resources(),
            self.loop,
        )

        try:
            future.result(timeout=3.0)
        except TimeoutError:
            print("Таймаут при закрытии ресурсов.")
        except Exception as error:
            print(f"Ошибка при завершении backend: {error}")

        self.loop.call_soon_threadsafe(
            self.loop.stop,
        )

        if self.thread.is_alive():
            self.thread.join(timeout=2.0)