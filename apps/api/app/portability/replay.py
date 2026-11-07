"""恢复备份后、开放服务之前显式重放独立删除清单。"""

import argparse
import asyncio

from app.config import get_settings
from app.database import Database
from app.portability.privacy import purge_expired_journal, replay_deletions


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--purge-expired", action="store_true", help="重放后清理已超过配置备份保留期的最小删除清单"
    )
    args = parser.parse_args()
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.sessions() as db:
            count = await replay_deletions(db, settings)
            print(f"Replayed {count} deletion intents; no credentials or personal names logged.")
            if args.purge_expired:
                print(f"Purged {purge_expired_journal(settings)} expired deletion intents.")
    finally:
        await database.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
