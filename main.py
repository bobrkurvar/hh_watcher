import asyncio
from desktop_app import App
from backend import AsyncBackend
from core.logger import setup_logging
from literals.search_keywords import SEARCH_QUERIES

setup_logging()

async def main():
    backend = AsyncBackend(queries=SEARCH_QUERIES)
    app = App(backend=backend)
    app.mainloop()
    backend.stop()

if __name__ == "__main__":
    asyncio.run(main())