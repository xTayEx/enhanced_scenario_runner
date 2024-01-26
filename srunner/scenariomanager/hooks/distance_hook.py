import math

import carla
from srunner.scenariomanager.hooks.hook import HookBase


class DistanceHook(HookBase):
    def __init__(self) -> None:
        self._results = []

    @property
    def results(self):
        return self._results

    def _calculate_distance(self, location1: carla.Location, location2: carla.Location):
        return math.sqrt(
            (location1.x - location2.x) ** 2
            + (location1.y - location2.y) ** 2
            + (location1.z - location2.z) ** 2
        )

    def execute(self, actors: carla.ActorList):
        for first_actor_idx in range(len(actors)):
            for second_actor_idx in range(first_actor_idx + 1, len(actors)):
                self._results.append(
                    self._calculate_distance(
                        actors[first_actor_idx].get_location(),
                        actors[second_actor_idx].get_location(),
                    )
                )
