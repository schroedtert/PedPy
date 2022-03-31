from dataclasses import dataclass
from typing import List

from shapely.geometry import LineString, Polygon


@dataclass
class Geometry:
    walls: List[LineString]

    def get_as_polygon(self) -> Polygon:
        coords = []
        for wall in self.walls:
            coords += wall.coords

        return Polygon(coords)
