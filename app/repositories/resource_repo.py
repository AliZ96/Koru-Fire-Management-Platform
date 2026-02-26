from sqlalchemy import text
from sqlalchemy.orm import Session


class ResourceRepository:

    def __init__(self, db: Session):
        self.db = db

    def find_nearest(self, lat: float, lon: float, limit: int = 5):
        query = text("""
            SELECT id, name, type,
            ST_Distance(
                location,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) AS distance
            FROM resources
            ORDER BY location <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            LIMIT :limit
        """)

        result = self.db.execute(query, {
            "lat": lat,
            "lon": lon,
            "limit": limit
        })

        return [dict(row) for row in result]
