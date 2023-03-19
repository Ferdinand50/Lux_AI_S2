import sys
import os
 
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from typing import List
from lux.factory import Factory
from .robot import RobotM
from . import globals
import logging

class FactoryM(Factory):
    robots: list


    def build_units(self,env_cfg):
        # only builds one robot per factory
        if self.power*10 >= env_cfg.ROBOTS["HEAVY"].POWER_COST and \
        self.cargo.metal >= env_cfg.ROBOTS["HEAVY"].METAL_COST:
            globals.actions[self.unit_id] = self.build_heavy()
        elif self.power*5 >= env_cfg.ROBOTS["LIGHT"].POWER_COST and \
        self.cargo.metal >= env_cfg.ROBOTS["LIGHT"].METAL_COST:
            globals.actions[self.unit_id] = self.build_light()


    def command_units(self,env_cfg):

        for i in range(len(self.robots)):
            # logging.warning(i)
            # logging.info(f"digging robot {self.robots[0].unit_id} action queue: {self.robots[0].action_queue}")
            if i == 0:        
                self.robots[i].dig_nonstop()
            elif i == 1:
                self.robots[i].support_digging_robot(self.robots[0])

            # logging.info(f"digging robot {self.robots[0].unit_id} action queue: {self.robots[0].action_queue}")


