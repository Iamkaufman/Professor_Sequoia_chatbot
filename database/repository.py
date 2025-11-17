import aiosqlite
from typing import List, Dict, Optional
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "professor_sequoia.db"

class Repository:
    def __init__(self, db_path: str = None):
        self.db_path = str(db_path or DB_PATH)

    async def get_all_pokemon_names(self) -> List[str]:
        """Get all Pokemon names from the database (lowercase)"""
        q = "SELECT LOWER(name) as name FROM pokemon"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(q)
            rows = await cur.fetchall()
            await cur.close()
            return [row['name'] for row in rows]

    async def get_pokemon_by_name(self, name: str) -> Optional[Dict]:
        q = """
        SELECT pokemon_id, name, type1, type2, hp, atk, def, spa, spd, spe, ability1, ability2, ability3, weight
        FROM pokemon WHERE lower(name) = lower(?)
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(q, (name,))
            row = await cur.fetchone()
            await cur.close()
            return dict(row) if row else None

    async def search_pokemon_by_partial(self, substring: str, limit: int = 10) -> List[Dict]:
        q = "SELECT pokemon_id, name, type1, type2 FROM pokemon WHERE lower(name) LIKE lower(?) LIMIT ?"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(q, (f"%{substring}%", limit))
            rows = await cur.fetchall()
            await cur.close()
            return [dict(r) for r in rows]

    async def get_moves_for_pokemon(self, pokemon_id: int) -> List[Dict]:
        q = """
        SELECT m.move_id, m.name, m.type, m.category, m.power, m.acc, m.pp, m.effect
        FROM moves m
        JOIN known_moves km ON km.move_id = m.move_id
        WHERE km.pokemon_id = ?
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(q, (pokemon_id,))
            rows = await cur.fetchall()
            await cur.close()
            return [dict(r) for r in rows]

    async def get_common_usage(self, pokemon_name: str) -> float:
        # If you have a usage table or RegUsage, adapt query here
        q = "SELECT 1.0 as usage FROM pokemon LIMIT 1;"  # fallback stub
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(q)
            row = await cur.fetchone()
            await cur.close()
            return float(row["usage"]) if row else 0.0

    async def query_pokemon_pool(self, exclude_ids: List[int]=None, types_exclude: List[str]=None, limit:int=50) -> List[Dict]:
        exclude_ids = exclude_ids or []
        types_exclude = types_exclude or []
        q = "SELECT pokemon_id, name, type1, type2, hp, atk, def, spa, spd, spe FROM pokemon"
        filters = []
        params = []
        if exclude_ids:
            placeholders = ",".join(["?"] * len(exclude_ids))
            filters.append(f"pokemon_id NOT IN ({placeholders})")
            params.extend(exclude_ids)
        if types_exclude:
            # naive: exclude by type1 or type2 presence
            for t in types_exclude:
                filters.append("type1 != ? AND (type2 IS NULL OR type2 != ?)")
                params.extend([t,t])
        if filters:
            q += " WHERE " + " AND ".join(f"({f})" for f in filters)
        q += " LIMIT ?"
        params.append(limit)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(q, params)
            rows = await cur.fetchall()
            await cur.close()
            return [dict(r) for r in rows]
        
async def get_top_usage(self, regulation_id: str, limit: int = 100) -> List[Dict]:
    """Get top usage Pokémon for a regulation."""
    q = """
    SELECT pokemon_name, usage_percent, rank
    FROM usage_stats
    WHERE regulation_id = ?
    ORDER BY rank
    LIMIT ?
    """
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(q, (regulation_id, limit))
        rows = await cur.fetchall()
        await cur.close()
        return [dict(r) for r in rows]

async def get_top_usage(self, regulation_id: str, limit: int = 100) -> List[Dict]:
    """Get top usage Pokémon for a regulation."""
    q = """
    SELECT pokemon_name, usage_percent, rank
    FROM usage_stats
    WHERE regulation_id = ?
    ORDER BY rank
    LIMIT ?
    """
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(q, (regulation_id, limit))
        rows = await cur.fetchall()
        await cur.close()
        return [dict(r) for r in rows]