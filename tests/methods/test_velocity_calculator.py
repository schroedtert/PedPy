import math
from dataclasses import dataclass

import numpy as np
import pytest
from shapely.geometry import LineString, Point

from report.methods.velocity_calculator import VelocityCalculator


@dataclass
class TrajectoryDataMock:
    frame_rate: float

    def get_pedestrian_positions(self):
        pass


@pytest.mark.parametrize(
    "agent_positions, fps, expected_speed",
    [
        ([Point(0, 0), Point(0, 0)], 1, 0.0),
        ([Point(0, 0), Point(0, 0)], 10, 0.0),
        ([Point(0, 0), Point(0, 1)], 1, 1.0),
        ([Point(0, 0), Point(1, 1)], 1, 2 ** 0.5),
        ([Point(-10, 10), Point(10, -10)], 10, 800 ** 0.5 * 10),
        ([Point(10, -10), Point(-10, 10)], 10, 800 ** 0.5 * 10),
    ],
)
def test_compute_instantaneous_velocity_no_movement_direction_not_ignore_backwards(
    mocker, agent_positions, fps, expected_speed
):
    traj = TrajectoryDataMock(fps)

    vc = VelocityCalculator(10, None, False)
    mocker.patch.object(traj, "get_pedestrian_positions", return_value=agent_positions)
    velocity = vc.compute_instantaneous_velocity(traj, 0, 1)
    assert velocity == expected_speed


@pytest.mark.parametrize(
    "length, direction",
    [
        (5, np.array([1, 0])),
        (3, np.array([0, 1])),
        (1, np.array([-1.5, 4.2])),
        (0.25, np.array([3.25, 10.0])),
        (0.0, np.array([3.25, 10.0])),
    ],
)
def test_compute_length_with_movement_direction(length, direction):
    start = np.array([5, -6])

    for angle in range(0, 360, 30):
        theta = np.deg2rad(angle)
        expected_length = np.abs(length * math.cos(theta))

        # rotate movement by angle with direction as original
        rot = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
        movement_vector = np.dot(rot, direction)
        movement_vector = length * (movement_vector / np.linalg.norm(movement_vector))

        end = start + movement_vector
        vc = VelocityCalculator(10, direction, False)

        movement = LineString([start, end])
        computed_length = vc.compute_length_with_movement_direction(movement)

        assert expected_length == pytest.approx(computed_length)
