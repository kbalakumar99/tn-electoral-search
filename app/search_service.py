"""
Search service with FTS5 and caching for blazingly fast searches.
Supports exact match, fuzzy search, and location-based filtering.
"""
from typing import List, Dict, Optional
from cachetools import LRUCache, TTLCache
from database import db
import time
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SearchService:
    """High-performance search service with caching."""

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300):
        """
        Initialize search service with caching.

        Args:
            cache_size: Maximum number of cached queries (default: 1000)
            cache_ttl: Time-to-live for cache entries in seconds (default: 300 = 5 minutes)
        """
        # LRU cache for frequently accessed queries
        self.query_cache = LRUCache(maxsize=cache_size)
        # TTL cache to prevent stale data
        self.ttl_cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)

    def _generate_cache_key(self, **kwargs) -> str:
        """Generate cache key from search parameters."""
        return f"{kwargs.get('query', '')}:{kwargs.get('search_type', '')}:{kwargs.get('district', '')}:{kwargs.get('constituency', '')}:{kwargs.get('polling_station', '')}:{kwargs.get('limit', 50)}:{kwargs.get('offset', 0)}"

    async def search(self,
                    query: str,
                    search_type: str = "fuzzy",
                    district: Optional[str] = None,
                    constituency: Optional[str] = None,
                    polling_station: Optional[str] = None,
                    limit: int = 50,
                    offset: int = 0) -> Dict:
        """
        Search for voters with multiple strategies.

        Args:
            query: Search query (name, voter ID, etc.) or '*' for all entries
            search_type: Type of search - "exact", "fuzzy", "voter_id", "prefix"
            district: Optional district filter
            constituency: Optional constituency filter
            polling_station: Optional polling station filter
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            Dictionary with results and metadata
        """
        start_time = time.time()

        # Check cache
        cache_key = self._generate_cache_key(
            query=query, search_type=search_type, district=district,
            constituency=constituency, polling_station=polling_station,
            limit=limit, offset=offset
        )

        if cache_key in self.ttl_cache:
            cached_result = self.ttl_cache[cache_key]
            cached_result['from_cache'] = True
            cached_result['search_time_ms'] = round((time.time() - start_time) * 1000, 2)
            return cached_result

        # Handle wildcard '*' - return all entries
        if query == '*' or not query:
            results = await self._get_all_entries(district, constituency, polling_station, limit, offset)
        # Perform search based on type
        elif search_type == "voter_id":
            results = await self._search_by_voter_id(query, district, constituency, polling_station, limit, offset)
        elif search_type == "exact":
            results = await self._search_exact(query, district, constituency, polling_station, limit, offset)
        elif search_type == "prefix":
            results = await self._search_prefix(query, district, constituency, polling_station, limit, offset)
        else:  # fuzzy (default)
            results = await self._search_fuzzy(query, district, constituency, polling_station, limit, offset)

        # Get total count (without pagination)
        total_count = await self._get_total_count(query, search_type, district, constituency, polling_station)

        response = {
            'query': query,
            'search_type': search_type if query != '*' else 'all',
            'results': results,
            'total_results': total_count,
            'returned_results': len(results),
            'limit': limit,
            'offset': offset,
            'has_more': (offset + len(results)) < total_count,
            'from_cache': False,
            'search_time_ms': round((time.time() - start_time) * 1000, 2)
        }

        # Cache the result
        self.ttl_cache[cache_key] = response

        return response

    def _log_query(self, search_type: str, query: str, params: tuple):
        """Log SQL query for debugging."""
        logger.info(f"🔍 SEARCH [{search_type}]")
        logger.info(f"   SQL: {query}")
        logger.info(f"   PARAMS: {params}")

    async def _search_by_voter_id(self, voter_id: str, district: Optional[str],
                                  constituency: Optional[str], polling_station: Optional[str],
                                  limit: int, offset: int) -> List[Dict]:
        """Search by exact voter ID."""
        query = """
            SELECT * FROM voters_complete
            WHERE voter_id LIKE ?
        """
        params = [f"%{voter_id}%"]

        # Add location filters
        query, params = self._add_location_filters(query, params, district, constituency, polling_station)

        query += " ORDER BY voter_id LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Log the query
        self._log_query("VOTER_ID", query, tuple(params))

        return await db.fetch_all(query, tuple(params))

        return await db.fetch_all(query, tuple(params))

    async def _search_exact(self, name: str, district: Optional[str],
                           constituency: Optional[str], polling_station: Optional[str],
                           limit: int, offset: int) -> List[Dict]:
        """Exact name search."""
        query = """
            SELECT * FROM voters_complete
            WHERE voter_name = ? OR voter_name_tamil = ?
        """
        params = [name, name]

        query, params = self._add_location_filters(query, params, district, constituency, polling_station)

        query += " ORDER BY serial_number LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Log the query
        self._log_query("EXACT", query, tuple(params))

        return await db.fetch_all(query, tuple(params))

    async def _search_prefix(self, prefix: str, district: Optional[str],
                            constituency: Optional[str], polling_station: Optional[str],
                            limit: int, offset: int) -> List[Dict]:
        """Prefix-based search (fast for autocomplete)."""
        query = """
            SELECT * FROM voters_complete
            WHERE voter_name LIKE ? OR voter_name_tamil LIKE ?
        """
        params = [f"{prefix}%", f"{prefix}%"]

        query, params = self._add_location_filters(query, params, district, constituency, polling_station)

        query += " ORDER BY voter_name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Log the query
        self._log_query("PREFIX", query, tuple(params))

        return await db.fetch_all(query, tuple(params))

    async def _search_fuzzy(self, query_text: str, district: Optional[str],
                           constituency: Optional[str], polling_station: Optional[str],
                           limit: int, offset: int) -> List[Dict]:
        """
        Fuzzy full-text search using FTS5.
        Supports partial matches, typos, and relevance ranking.
        """
        # FTS5 doesn't support leading wildcards (*term)
        # Strategy 1: Prefix search (most common)
        # Strategy 2: Use LIKE for contains search as fallback
        
        # Try FTS5 prefix search first
        fts_query = f'"{query_text}"*'  # Prefix: matches "ram" in "ramesh"
        
        sql = """
            SELECT
                v.*,
                voters_fts.rank as relevance_score
            FROM voters_fts
            JOIN voters_complete v ON voters_fts.rowid = v.id
            WHERE voters_fts MATCH ?
        """
        params = [fts_query]

        # Add location filters
        sql, params = self._add_location_filters(sql, params, district, constituency, polling_station)

        sql += " ORDER BY voters_fts.rank, v.voter_name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Log the query
        self._log_query("FUZZY", sql, tuple(params))

        try:
            results = await db.fetch_all(sql, tuple(params))
            if results:
                return results
        except Exception as e:
            logger.warning(f"FTS prefix search failed: {e}")
        
        # Fallback: LIKE-based contains search (slower but more flexible)
        logger.info(f"   🔄 Using fallback LIKE search for contains match...")
        sql = """
            SELECT
                v.*,
                0 as relevance_score
            FROM voters_complete v
            WHERE (
                v.voter_name LIKE ? OR
                v.voter_name_tamil LIKE ? OR
                v.relative_name LIKE ? OR
                v.relative_name_tamil LIKE ? OR
                v.voter_id LIKE ?
            )
        """
        like_pattern = f'%{query_text}%'
        params = [like_pattern, like_pattern, like_pattern, like_pattern, like_pattern]

        # Add location filters
        sql, params = self._add_location_filters(sql, params, district, constituency, polling_station)

        sql += " ORDER BY v.voter_name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Log the query
        self._log_query("FUZZY_LIKE", sql, tuple(params))

        return await db.fetch_all(sql, tuple(params))

    def _add_location_filters(self, query: str, params: List,
                             district: Optional[str], constituency: Optional[str],
                             polling_station: Optional[str]) -> tuple:
        """Add location-based filters to query."""
        if district:
            query += " AND district_name = ?"
            params.append(district)

        if constituency:
            query += " AND constituency_name = ?"
            params.append(constituency)

        if polling_station:
            query += " AND polling_station_name = ?"
            params.append(polling_station)

        return query, params

    async def _get_all_entries(self, district: Optional[str], constituency: Optional[str],
                              polling_station: Optional[str], limit: int, offset: int) -> List[Dict]:
        """Get all entries with filters (no search query)."""
        sql = """
            SELECT 
                v.id,
                v.voter_name,
                v.voter_name_tamil,
                v.relative_name,
                v.relative_name_tamil,
                v.relationship_code,
                v.age,
                v.gender,
                v.voter_id,
                v.serial_number,
                v.house_no,
                d.name as district_name,
                c.name as constituency_name,
                ps.name as polling_station_name
            FROM voters v
            JOIN polling_stations ps ON v.polling_station_id = ps.id
            JOIN constituencies c ON ps.constituency_id = c.id
            JOIN districts d ON c.district_id = d.id
            WHERE 1=1
        """
        params = []
        
        if district:
            sql += " AND d.name = ?"
            params.append(district)
        if constituency:
            sql += " AND c.name = ?"
            params.append(constituency)
        if polling_station:
            sql += " AND ps.name = ?"
            params.append(polling_station)
        
        sql += " ORDER BY v.serial_number LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Log the query
        self._log_query("ALL_ENTRIES", sql, tuple(params))
        
        results = await db.fetch_all(sql, tuple(params))
        return [dict(r) for r in results]

    async def _get_total_count(self, query_text: str, search_type: str,
                              district: Optional[str], constituency: Optional[str],
                              polling_station: Optional[str]) -> int:
        """Get total count of results (for pagination)."""
        # Handle wildcard for all entries
        if query_text == '*' or not query_text:
            sql = "SELECT COUNT(*) as count FROM voters_complete WHERE 1=1"
            params = []
        elif search_type == "voter_id":
            sql = "SELECT COUNT(*) as count FROM voters_complete WHERE voter_id LIKE ?"
            params = [f"%{query_text}%"]
        elif search_type == "exact":
            sql = "SELECT COUNT(*) as count FROM voters_complete WHERE voter_name = ? OR voter_name_tamil = ?"
            params = [query_text, query_text]
        elif search_type == "prefix":
            sql = "SELECT COUNT(*) as count FROM voters_complete WHERE voter_name LIKE ? OR voter_name_tamil LIKE ?"
            params = [f"{query_text}%", f"{query_text}%"]
        else:  # fuzzy
            fts_query = f'"{query_text}"*'
            sql = """
                SELECT COUNT(*) as count
                FROM voters_fts
                JOIN voters_complete v ON voters_fts.rowid = v.id
                WHERE voters_fts MATCH ?
            """
            params = [fts_query]

        sql, params = self._add_location_filters(sql, params, district, constituency, polling_station)

        # Log the count query
        self._log_query("COUNT", sql, tuple(params))

        result = await db.fetch_one(sql, tuple(params))
        count = result['count'] if result else 0
        logger.info(f"   RESULT: {count} total records")
        return count

    async def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get autocomplete suggestions based on prefix."""
        cache_key = f"suggest:{prefix}:{limit}"

        if cache_key in self.ttl_cache:
            return self.ttl_cache[cache_key]

        query = """
            SELECT DISTINCT voter_name
            FROM voters
            WHERE voter_name LIKE ?
            ORDER BY voter_name
            LIMIT ?
        """

        results = await db.fetch_all(query, (f"{prefix}%", limit))
        suggestions = [r['voter_name'] for r in results]

        self.ttl_cache[cache_key] = suggestions
        return suggestions

    async def get_locations(self) -> Dict:
        """Get all available districts, constituencies, and polling stations."""
        cache_key = "locations:all"

        if cache_key in self.ttl_cache:
            return self.ttl_cache[cache_key]

        districts = await db.fetch_all("SELECT name, code FROM districts ORDER BY name")
        constituencies = await db.fetch_all(
            "SELECT c.name, c.code, d.name as district_name FROM constituencies c "
            "JOIN districts d ON c.district_id = d.id ORDER BY d.name, c.name"
        )
        polling_stations = await db.fetch_all(
            "SELECT ps.name, ps.station_number, c.name as constituency_name, d.name as district_name "
            "FROM polling_stations ps "
            "JOIN constituencies c ON ps.constituency_id = c.id "
            "JOIN districts d ON c.district_id = d.id "
            "ORDER BY d.name, c.name, ps.name"
        )

        locations = {
            'districts': districts,
            'constituencies': constituencies,
            'polling_stations': polling_stations
        }

        self.ttl_cache[cache_key] = locations
        return locations

    async def check_data_exists(self, district: Optional[str] = None, 
                               constituency: Optional[str] = None, 
                               polling_station: Optional[str] = None) -> Dict:
        """
        Check if any voter data exists for the given location filters.
        Returns count and existence status.
        """
        cache_key = f"data_exists:{district}:{constituency}:{polling_station}"
        
        if cache_key in self.ttl_cache:
            return self.ttl_cache[cache_key]

        sql = "SELECT COUNT(*) as count FROM voters_complete WHERE 1=1"
        params = []
        
        if district:
            sql += " AND district_name = ?"
            params.append(district)
        if constituency:
            sql += " AND constituency_name = ?"
            params.append(constituency)
        if polling_station:
            sql += " AND polling_station_name = ?"
            params.append(polling_station)
        
        result = await db.fetch_one(sql, tuple(params))
        count = result['count'] if result else 0
        
        response = {
            'exists': count > 0,
            'count': count,
            'district': district,
            'constituency': constituency,
            'polling_station': polling_station
        }
        
        self.ttl_cache[cache_key] = response
        return response

    def clear_cache(self):
        """Clear all caches."""
        self.query_cache.clear()
        self.ttl_cache.clear()


# Global search service instance
search_service = SearchService()
