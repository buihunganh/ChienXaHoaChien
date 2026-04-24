from dataclasses import dataclass
from src.utils.constants import FUEL_COST_PER_PIXEL, GRAVITY, WIND_MAX

@dataclass(frozen=True)
class MapConfig:
    id: int
    name: str
    description: str
    bg_image: str | None
    terrain_image: str | None
    thumbnail_image: str | None
    wind_mag_min: float
    wind_mag_max: float
    gravity: float
    fuel_cost: float

MAP_CATALOGUE: dict[int, MapConfig] = {
    1: MapConfig(
        id=1,
        name="Plains",
        description="Standard battlefield with lush grass.",
        bg_image="bg/plain",
        terrain_image=None,
        thumbnail_image="bg/plain",
        wind_mag_min=0.0,
        wind_mag_max=WIND_MAX,
        gravity=GRAVITY,
        fuel_cost=FUEL_COST_PER_PIXEL,
    ),
    2: MapConfig(
        id=2,
        name="Sea",
        description="Strong ocean winds on a pirate ship.",
        bg_image="bg/sea",
        terrain_image=None,
        thumbnail_image="bg/sea",
        wind_mag_min=WIND_MAX * 0.5,
        wind_mag_max=WIND_MAX,
        gravity=GRAVITY,
        fuel_cost=FUEL_COST_PER_PIXEL,
    ),
    3: MapConfig(
        id=3,
        name="Outer Space",
        description="Low gravity, jagged lunar terrain, no wind.",
        bg_image="bg/space",
        terrain_image=None,
        thumbnail_image="bg/space",
        wind_mag_min=0.0,
        wind_mag_max=0.0,
        gravity=300.0,
        fuel_cost=FUEL_COST_PER_PIXEL,
    ),
    4: MapConfig(
        id=4,
        name="Locked Map",
        description="Soon...",
        bg_image=None,
        terrain_image=None,
        thumbnail_image=None,
        wind_mag_min=0.0,
        wind_mag_max=WIND_MAX,
        gravity=GRAVITY,
        fuel_cost=FUEL_COST_PER_PIXEL,
    ),
    5: MapConfig(
        id=5,
        name="Locked Map",
        description="Soon...",
        bg_image=None,
        terrain_image=None,
        thumbnail_image=None,
        wind_mag_min=0.0,
        wind_mag_max=WIND_MAX,
        gravity=GRAVITY,
        fuel_cost=FUEL_COST_PER_PIXEL,
    ),
    6: MapConfig(
        id=6,
        name="Locked Map",
        description="Soon...",
        bg_image=None,
        terrain_image=None,
        thumbnail_image=None,
        wind_mag_min=0.0,
        wind_mag_max=WIND_MAX,
        gravity=GRAVITY,
        fuel_cost=FUEL_COST_PER_PIXEL,
    ),
}

def get_map_config(level_id: int) -> MapConfig:
    return MAP_CATALOGUE.get(level_id, MAP_CATALOGUE[1])
