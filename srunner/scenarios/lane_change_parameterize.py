import carla
import py_trees

from srunner.scenariomanager.scenarioatomics.atomic_behaviors import (
    BasicAgentBehavior,
    KeepVelocity,
    Idle,
    LaneChange,
)
from srunner.scenariomanager.scenarioatomics.atomic_criteria import CollisionTest
from srunner.scenarios.basic_scenario import BasicScenario
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider


class LangeChangeParameterize(BasicScenario):
    def __init__(
        self,
        world,
        ego_vehicles,
        config,
        randomize=False,
        debug_mode=False,
        criteria_enable=True,
        timeout=60,
    ):
        self.timeout = timeout
        self.ego_vehicles = ego_vehicles
        self.other_actors = []
        super(LangeChangeParameterize, self).__init__(
            "AgentScenario",
            ego_vehicles,
            config,
            world,
            debug_mode,
            criteria_enable=criteria_enable,
        )

    def _setup_scenario_trigger(self, config):
        return None

    def _initialize_actors(self, config):
        for actor in config.other_actors:
            vehicle = CarlaDataProvider.request_new_actor(actor.model, actor.transform)
            self.other_actors.append(vehicle)

    def _create_behavior(self):
        root = py_trees.composites.Parallel(
            "Parallel Behavior", policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ALL
        )

        ego_behavior = py_trees.composites.Sequence("ego_seq")
        ego_vehicle_transform: carla.Transform = self.ego_vehicles[0].get_transform()
        target_location = carla.Location(
            x=ego_vehicle_transform.location.x - 150,
            y=ego_vehicle_transform.location.y,
            z=ego_vehicle_transform.location.z,
        )
        ego_behavior.add_child(
            BasicAgentBehavior(
                self.ego_vehicles[0],
                target_location,
                name="BasicAgentBehavior",
                target_speed=int(self.config.other_parameters["behaviors"][0]["target_speed"]),
            )
        )
        ego_behavior.add_child(Idle(duration=30))

        other_behavior = py_trees.composites.Sequence("npc_seq")
        other_behavior.add_child(
            KeepVelocity(
                self.other_actors[0],
                target_velocity=int(self.config.other_parameters["behaviors"][1]["target_velocity"]),
                duration=float(
                    self.config.other_parameters["behaviors"][1]["duration"]
                ),
                name="KeepVelocity",
            )
        )
        other_behavior.add_child(LaneChange(self.other_actors[0], direction="left"))
        other_behavior.add_child(Idle(duration=30))

        root.add_child(ego_behavior)
        root.add_child(other_behavior)

        return root

    def _create_test_criteria(self):
        criteria = []

        for ego in self.ego_vehicles:
            collision_criterion = CollisionTest(ego)
            criteria.append(collision_criterion)

        return criteria

    def __del__(self):
        self.remove_all_actors()
