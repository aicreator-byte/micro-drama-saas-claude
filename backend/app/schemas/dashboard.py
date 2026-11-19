"""Dashboard stats (future-dev 2f).

Real counts from the DB for the current user — the dashboard page used to
hardcode Characters/Locations/Episodes to 0.
"""
from pydantic import BaseModel


class DashboardStats(BaseModel):
    projects: int
    characters: int
    locations: int
    episodes: int
