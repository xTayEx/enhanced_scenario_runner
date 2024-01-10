from typing import Union
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

import carla
import py_trees
from py_trees.composites import Selector, Sequence, Parallel

from srunner.scenariomanager.scenarioatomics.atomic_behaviors import (
    BasicAgentBehavior,
    KeepVelocity,
    Idle,
    LaneChange,
)
from srunner.scenariomanager.scenarioatomics.atomic_criteria import CollisionTest
from srunner.scenarios.basic_scenario import BasicScenario
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from utils import normalize_xml_attr


class LLMScenario(BasicScenario):
    def __init__(
        self,
        world,
        ego_vehicles,
        config,
        bt_path,
        randomize=False,
        debug_mode=False,
        criteria_enable=True,
        timeout=60,
    ):
        self.timeout = timeout
        self.ego_vehicles = ego_vehicles
        self.other_actors = []
        self.bt_path = bt_path
        super(LLMScenario, self).__init__(
            "LLMScenario",
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

    def _get_node_class_by_name(self, name: str):
        return {
            "LaneChange": LaneChange,
            "KeepVelocity": KeepVelocity,
            "Sequence": Sequence,
            "Selector": Selector,
            "Parallel": Parallel,
        }[name]

    def _create_behavior_helper(
        self, cur_node: Element, cur_container: Union[Selector, Sequence, Parallel]
    ):
        if len(cur_node) == 0:
            return
        for child in cur_node:
            child.attrib = normalize_xml_attr(attrs=child.attrib)
            if child.tag in {"Sequence", "Selector", "Parallel"}:
                saved_container = cur_container
                cur_container = self._get_node_class_by_name(child.tag)(**child.attrib)
                self._create_behavior_helper(child, cur_container)
                cur_container = saved_container
            else:
                child_node = self._get_node_class_by_name(child.tag)(
                    actor=self.other_actors[0], **child.attrib
                )
                cur_container.add_child(child_node)
                self._create_behavior_helper(child, cur_container)

    def _create_behavior(self):
        with open(self.bt_path, "r", encoding="utf-8") as bt_f:
            bt_xml = bt_f.read()

        root_container = Parallel(policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ALL)
        xml_instance = ET.fromstring(bt_xml)

        ego_behavior = py_trees.composites.Sequence("ego_seq")
        ego_vehicle_transform: carla.Transform = self.ego_vehicles[0].get_transform()
        target_location = carla.Location(
            x=ego_vehicle_transform.location.x - 180,
            y=ego_vehicle_transform.location.y,
            z=ego_vehicle_transform.location.z,
        )
        ego_behavior.add_child(
            BasicAgentBehavior(
                self.ego_vehicles[0],
                target_location,
                name="BasicAgentBehavior",
                target_speed=20,
            )
        )

        # create other vehicle's behavior tree
        xml_instance.attrib = normalize_xml_attr(attrs=xml_instance.attrib)

        other_behavior: Union[
            Sequence, Selector, Parallel
        ] = self._get_node_class_by_name(xml_instance.tag)(**xml_instance.attrib)
        self._create_behavior_helper(xml_instance, other_behavior)
        other_behavior.add_child(Idle(30))

        root_container.add_child(ego_behavior)
        root_container.add_child(other_behavior)
        py_trees.display.print_ascii_tree(root_container)

        return root_container

    def _create_test_criteria(self):
        criteria = []

        for ego in self.ego_vehicles:
            collision_criterion = CollisionTest(ego)
            criteria.append(collision_criterion)

        return criteria

    def __del__(self):
        self.remove_all_actors()
