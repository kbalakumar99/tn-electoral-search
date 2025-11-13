"""
Database module for electoral search system.
Provides async SQLite operations with connection pooling and FTS5 support.
"""
import aiosqlite
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = Path(__file__).parent.parent / "database" / "electoral_data.db"
SCHEMA_PATH = Path(__file__).parent.parent / "config" / "schema.sql"


class Database:
    """Async SQLite database manager with connection pooling."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()  # For FTS operations

    async def initialize(self):
        """Initialize database and create schema if needed."""
        # Enable WAL mode for better concurrent read performance
        conn = await aiosqlite.connect(self.db_path)
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        await conn.execute("PRAGMA temp_store=MEMORY")
        await conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        await conn.commit()
        await conn.close()

        # Create schema
        await self._create_schema()

    async def _create_schema(self):
        """Create database schema from SQL file."""
        if not SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

        async with aiosqlite.connect(self.db_path) as conn:
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            # Remove comments and split by semicolons
            lines = []
            for line in schema_sql.split('\n'):
                line = line.strip()
                if line and not line.startswith('--'):
                    lines.append(line)

            clean_sql = ' '.join(lines)

            # Split by semicolons and filter empty statements
            statements = [s.strip() for s in clean_sql.split(';') if s.strip()]

            # Execute each statement separately
            for statement in statements:
                try:
                    await conn.execute(statement)
                except Exception as e:
                    print(f"Warning executing statement: {e}")
                    print(f"Statement: {statement[:100]}...")

            await conn.commit()

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with context manager."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row

        # Enable optimizations for read-heavy workload
        await conn.execute("PRAGMA query_only=OFF")
        await conn.execute("PRAGMA temp_store=MEMORY")

        try:
            yield conn
        finally:
            await conn.close()

    async def execute(self, query: str, params: tuple = None):
        """Execute a single query."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            await conn.commit()
            return cursor

    async def execute_many(self, query: str, params_list: list):
        """Execute multiple queries in a batch."""
        async with self.get_connection() as conn:
            await conn.executemany(query, params_list)
            await conn.commit()

    async def fetch_one(self, query: str, params: tuple = None):
        """Fetch a single row."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = None):
        """Fetch all rows."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def fetch_paginated(self, query: str, params: tuple = None, limit: int = 50, offset: int = 0):
        """Fetch paginated results."""
        paginated_query = f"{query} LIMIT ? OFFSET ?"
        all_params = (*params, limit, offset) if params else (limit, offset)
        return await self.fetch_all(paginated_query, all_params)

    async def rebuild_fts_index(self):
        """Rebuild the FTS5 index safely without corruption risk."""
        async with self._lock:  # Prevent concurrent FTS operations
            async with self.get_connection() as conn:
                try:
                    # Use transaction for atomic rebuild
                    await conn.execute("BEGIN IMMEDIATE")
                    
                    # Safe rebuild using FTS5 'rebuild' command (preferred method)
                    try:
                        await conn.execute("INSERT INTO voters_fts(voters_fts) VALUES('rebuild')")
                        logger.info("✅ FTS index rebuilt using 'rebuild' command")
                    except Exception as rebuild_error:
                        logger.warning(f"FTS rebuild command failed: {rebuild_error}, using manual sync...")
                        
                        # Fallback: Drop and recreate FTS table safely
                        await conn.execute("DROP TABLE IF EXISTS voters_fts")
                        await conn.execute("""
                            CREATE VIRTUAL TABLE voters_fts USING fts5(
                                voter_name, voter_name_tamil, relative_name, relative_name_tamil,
                                voter_id, serial_number, house_no,
                                content='voters', content_rowid='id'
                            )
                        """)
                        
                        # Sync all existing data
                        await conn.execute("""
                            INSERT INTO voters_fts(rowid, voter_name, voter_name_tamil, relative_name,
                                                  relative_name_tamil, voter_id, serial_number, house_no)
                            SELECT id, voter_name, voter_name_tamil, relative_name,
                                   relative_name_tamil, voter_id, serial_number, house_no
                            FROM voters
                        """)
                        logger.info("✅ FTS index rebuilt using manual sync")
                    
                    # Optimize the rebuilt index
                    await conn.execute("INSERT INTO voters_fts(voters_fts) VALUES('optimize')")
                    await conn.commit()
                    logger.info("✅ FTS index optimized")
                    
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"❌ FTS rebuild failed: {e}")
                    raise

    async def optimize(self):
        """Optimize database for better performance."""
        async with self.get_connection() as conn:
            await conn.execute("PRAGMA optimize")
            await conn.execute("VACUUM")
            await conn.commit()

    async def get_stats(self):
        """Get database statistics."""
        stats = {}

        async with self.get_connection() as conn:
            # Count records in each table
            cursor = await conn.execute("SELECT COUNT(*) as count FROM districts")
            row = await cursor.fetchone()
            stats['districts'] = row['count']

            cursor = await conn.execute("SELECT COUNT(*) as count FROM constituencies")
            row = await cursor.fetchone()
            stats['constituencies'] = row['count']

            cursor = await conn.execute("SELECT COUNT(*) as count FROM polling_stations")
            row = await cursor.fetchone()
            stats['polling_stations'] = row['count']

            cursor = await conn.execute("SELECT COUNT(*) as count FROM voters")
            row = await cursor.fetchone()
            stats['voters'] = row['count']

            # Database size
            cursor = await conn.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            row = await cursor.fetchone()
            stats['db_size_bytes'] = row['size']
            stats['db_size_mb'] = round(row['size'] / (1024 * 1024), 2)

        return stats


# Global database instance
db = Database()
