import math
from typing import List

import carla
from srunner.scenariomanager.hook import HookBase

class DistanceHook(HookBase):

    def __init__(self, actors: List[carla.Actor]) -> None:
        self.actors = actors

    def _calculate_distance(self, location1: carla.Location, location2: carla.Location):
        return math.sqrt((location1.x - location2.x)**2 + (location1.y - location2.y)**2 + (location1.z - location2.z)**2)

    def execute(self):
        distances = []
        for first_actor_idx in range(len(self.actors)):
            for second_actor_idx in range(first_actor_idx + 1, len(self.actors)):
                distances.append(self._calculate_distance(self.actors[first_actor_idx].get_location(), self.actors[second_actor_idx].get_location()))

        return distances
