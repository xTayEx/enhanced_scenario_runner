from random import choice

from srunner.scenariomanager.hooks.hook import HookBase

class DummyHook(HookBase):

    def __init__(self) -> None:
        pass

    def execute(self):
        test_words = ["carla", "simulator", "hello", "world"]
        return choice(test_words)
