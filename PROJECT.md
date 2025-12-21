Project: İzmir Wildfire Monitoring & Visualization

Overview
- FastAPI backend and Leaflet.js frontend focused on İzmir.
- Ingests NASA FIRMS active fire detections and visualizes points on a map.
- Combines weather context and a simple spread model to show likely hazard area.
- Extensions: crisis-time routing/automation and pre-ignition early warnings.

Roadmap
1) Active Fires + Spread
- Scheduled FIRMS pulls (10–15 min) with disk cache at `data/firms.json`.
- Baseline spread model (wind sector) per fire; union/overlay for hazard.
- Push updates via SSE/WebSocket (future), client auto-refresh.
- ML track (future): grid-based risk classifier using historical FIRMS + reanalysis.

2) Response Automation (future)
- Layers: shelters/depots, water sources, OSM road graph, hazard polygons.
- Routing: fastest safe path avoiding hazard polygons; ETA and dispatch suggestions.

3) Early Warning (future)
- Daily risk index using meteo features (temp, RH, wind, drought proxy).
- Alerts: webhook/email; dashboard with watch/warning polygons; backtesting.

Immediate Additions (this pass)
- Background poller to keep a cached FIRMS GeoJSON (`data/firms.json`).
- `/api/fires_cached`: serves cached data with metadata and optional refresh.
- `/api/risk` (stub): simple grid over İzmir; risk derived from proximity to cached fires.
- Frontend tweaks to load cached fires and show last update time.

Config (.env)
- `MAP_KEY`: FIRMS API key (already present).
- `FIRMS_POLL_MINUTES` (optional): polling interval in minutes (default 15).

Notes
- Network failures degrade gracefully: endpoints return last cached data if present.
- Caching intentionally simple; a proper store (SQLite/Redis) can replace the file as needed.

