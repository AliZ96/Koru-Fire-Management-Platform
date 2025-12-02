Add İzmir administrative boundary GeoJSON here to show the real border on the map.

File path
- Place the file as `static/data/izmir.geojson`

Format
- Valid GeoJSON with a Polygon or MultiPolygon geometry in WGS84 (EPSG:4326)
- Example top-level shape:
  {
    "type": "FeatureCollection",
    "features": [ { "type": "Feature", "geometry": { "type": "MultiPolygon", "coordinates": [ ... ] }, "properties": { } } ]
  }

How to obtain
- OpenStreetMap boundaries (via Overpass Turbo export as GeoJSON)
- GADM or other open administrative datasets

Fallback
- If `izmir.geojson` is missing, the app will draw a simple bounding box so the UI still works.

