import numpy as np
from shapely.geometry import LineString, Point

from report.data.trajectory_data import TrajectoryData


class VelocityCalculator:
    """Calculator for the instantaneous velocities of the pedestrians

    Attributes:
         frame_step (int): gives the size of time interval for calculating the velocity
         measurement_direction (np.ndarray): indicates in which direction the velocity will be projected
         ignore_backward_movement (bool):  indicates whether you want to ignore the movement opposite to
                                           the direction from `set_movement_direction`
    """

    frame_step: int
    measurement_direction: np.ndarray = None
    ignore_backward_movement: bool

    def __init__(
        self, frame_step: int, movement_direction: np.ndarray, ignore_backward_movement: bool
    ):
        self.frame_step = frame_step
        self.measurement_direction = movement_direction
        self.ignore_backward_movement = ignore_backward_movement

    def compute_instantaneous_velocity(
        self,
        trajectory: TrajectoryData,
        agent_id: int,
        frame: int,
    ):
        """Compute the instantaneous velocity of a pedestrian at a specific frame

        Args:
            trajectory (TrajectoryData): trajectory data
            agent_id (int): id of the agent
            frame (int): frame for which the velocity is calculated

        Returns:
            the instantaneous [in meter/second]
        """
        positions = trajectory.get_pedestrian_positions(frame, agent_id, self.frame_step)
        line = LineString(positions)
        time_movement = (len(line.coords) - 1) * 1.0 / trajectory.frame_rate

        if self.measurement_direction is None:
            length = self.compute_length_without_movement_direction(line)
        else:
            length = self.compute_length_with_movement_direction(line)
        speed = length / time_movement

        return speed

    def compute_length_with_movement_direction(
        self,
        movement: LineString,
    ):
        movement_vector = np.array(movement.coords[-1]) - np.array(movement.coords[0])

        projected_length = np.dot(movement_vector, self.measurement_direction) / np.linalg.norm(
            self.measurement_direction
        )

        return np.abs(projected_length)

    def compute_length_without_movement_direction(
        self,
        movement: LineString,
    ):
        return Point(movement.coords[0]).distance(Point(movement.coords[-1]))
