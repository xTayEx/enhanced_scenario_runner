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
        if not cur_node:
            return
        for child in cur_node:
            if child.tag in {"Sequence", "Selector", "Parallel"}:
                saved_container = cur_container
                cur_container_class = self._get_node_class_by_name(child.tag)
                if child.tag == "Parallel":
                    cur_container = cur_container_class(
                        Policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE
                    )
                else:
                    cur_container = cur_container_class()
                self._create_behavior_helper(child, cur_container)
                cur_container = saved_container
            else:
                cur_container.add_child(
                    self._get_node_class_by_name(child.tag, **child.attrib)
                )
                self._create_behavior_helper(child, cur_container)

    def _create_behavior(self):
        with open(self.bt_path, "r", encoding="utf-8") as bt_f:
            bt_xml = bt_f.read()

        xml_instance = ET.fromstring(bt_xml)
        return self._create_behavior_helper(
            xml_instance, self._get_node_class_by_name(xml_instance.tag)
        )

    def _create_test_criteria(self):
        criteria = []

        for ego in self.ego_vehicles:
            collision_criterion = CollisionTest(ego)
            criteria.append(collision_criterion)

        return criteria

    def __del__(self):
        self.remove_all_actors()
