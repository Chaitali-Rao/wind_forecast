"""Central configuration. Everything tunable lives here or in env vars."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))

# Elexon Insights API (public, no key needed)
ELEXON_BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")

# The challenge only covers purchase decisions made in January 2026,
# i.e. for delivery days 2026-01-01 .. 2026-01-31 (UK local dates).
DELIVERY_START = "2026-01-01"
DELIVERY_END = "2026-01-31"

# Local timezone of the GB power market.
MARKET_TZ = "Europe/London"

# ASSUMPTION: the day-ahead decision is made at 09:00 UK time on D-1.
# (GB day-ahead auctions close around 09:20-09:50 on D-1; 09:00 leaves a safety margin.)
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:00")

# WINDFOR publishes forecasts with a horizon of up to several days. Only the
# first 48h matter for a D-1 decision, so we drop anything beyond that.
MAX_HORIZON_HOURS = 48
# Publish window fetched from Elexon (a few days before January for the 1st Jan decision).
PUBLISH_FETCH_FROM = os.getenv("PUBLISH_FETCH_FROM", "2025-12-28")
PUBLISH_FETCH_TO = os.getenv("PUBLISH_FETCH_TO", "2026-01-31")

# If true and no cached files exist, try to download from Elexon on startup.
LIVE_FETCH_ON_START = os.getenv("LIVE_FETCH_ON_START", "false").lower() == "true"
# Set true in hosted deployments so missing cached data fails loudly instead of
# presenting synthetic demo values as a functioning production deployment.
REQUIRE_REAL_DATA = os.getenv("REQUIRE_REAL_DATA", "false").lower() == "true"
