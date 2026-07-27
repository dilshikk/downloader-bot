import asyncpg


class FavoritesDataBaseActions:

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def add_favorite(self, tg_id: int, file_id: str, title: str):
        query = """
            INSERT INTO favorites(tg_id, file_id, title)
            VALUES($1, $2, $3)
            ON CONFLICT (tg_id, file_id) DO NOTHING
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, tg_id, file_id, title)

    async def remove_favorite(self, tg_id: int, file_id: str):
        query = """
            DELETE FROM favorites WHERE tg_id = $1 AND file_id = $2
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, tg_id, file_id)

    async def is_favorite(self, tg_id: int, file_id: str) -> bool:
        query = """
            SELECT 1 FROM favorites WHERE tg_id = $1 AND file_id = $2
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, tg_id, file_id)
            return row is not None

    async def get_favorites(self, tg_id: int) -> list:
        query = """
            SELECT file_id, title, created_at FROM favorites
            WHERE tg_id = $1
            ORDER BY created_at DESC
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, tg_id)
