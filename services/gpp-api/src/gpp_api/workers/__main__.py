"""Worker entry point."""

import asyncio

from gpp_api.workers.worker import run_worker

if __name__ == "__main__":
    asyncio.run(run_worker())
