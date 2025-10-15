from __future__ import annotations

import asyncio

from app.services.community_pool_loader import CommunityPoolLoader


async def main() -> None:
    loader = CommunityPoolLoader()
    inserted = await loader.import_to_database()
    print(f"Inserted {inserted} communities into database.")


if __name__ == "__main__":
    asyncio.run(main())

