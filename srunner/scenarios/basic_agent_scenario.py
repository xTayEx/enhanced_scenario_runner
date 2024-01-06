import carla
import py_trees

from srunner.scenariomanager.scenarioatomics.atomic_behaviors import BasicAgentBehavior
from srunner.scenariomanager.scenarioatomics.atomic_criteria import CollisionTest
from srunner.scenarios.basic_scenario import BasicScenario
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider


class AgentScenario(BasicScenario):
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
        super(AgentScenario, self).__init__(
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
            # vehicle.set_simulate_physics(enabled=False)

    def _create_behavior(self):
        behavior = py_trees.composites.Sequence("Seq")
        ego_vehicle_transform: carla.Transform = self.ego_vehicles[0].get_transform()
        target_location = carla.Location(
            ego_vehicle_transform.location.x + 100,
            ego_vehicle_transform.location.y,
            ego_vehicle_transform.location.z,
        )
        behavior.add_child(BasicAgentBehavior(self.ego_vehicles[0], target_location))

        return behavior

    def _create_test_criteria(self):
        criteria = []

        for ego in self.ego_vehicles:
            collision_criterion = CollisionTest(ego)
            criteria.append(collision_criterion)

        return criteria

    def __del__(self):
        self.remove_all_actors()
