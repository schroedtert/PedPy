from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Dict, List

from shapely.geometry import LineString, Polygon

from report.methods.velocity_calculator import VelocityCalculator


@dataclass(frozen=True)
class ConfigurationMethodCCM:
    """Configuration for method_CCM
    Attributes:
        line_width(float): width of the measurement line (will become a polygon!)
        cut_off_radius (float): max radius of voronoi cells (0 can lead to large polygons only bound
            the geometry)
    """

    line_width: float = 0.0
    cut_off_radius: float = 0.0


@dataclass(frozen=True)
class Configuration:
    """Configuration to be used in the analysis

    Attributes:
        output_directory (pathlib.Path): directory in which to store the results
        trajectory_files (List[pathlib.Path]): trajectory files to be used in the analysis
        geometry_file (pathlib.Path): geometry file to be used in the analysis

        measurement_areas (Dict[int, Polygon]): measurement areas to be used in the analysis
        measurement_lines (Dict[int, LineString]): measurement line to be used in the analysis

        velocity_calculator (VelocityCalculator): VelocityCalculator calculator used in
    """

    output_directory: pathlib.Path
    trajectory_files: List[pathlib.Path]
    geometry_file: pathlib.Path

    measurement_areas: Dict[int, Polygon]
    measurement_lines: Dict[int, LineString]

    velocity_calculator: VelocityCalculator

    config_method_ccm: Dict[int, ConfigurationMethodCCM]
