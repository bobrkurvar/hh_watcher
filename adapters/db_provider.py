from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)


class DbProvider:
    def __init__(self, url: str):
        self.url = url
        self._engine: AsyncEngine = create_async_engine(url)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine
        )

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @property
    def engine(self):
        return self._engine

    async def close(self) -> None:
        await self._engine.dispose()
