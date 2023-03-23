import sys
import os
 
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lux.factory import Factory
from .utils import locate_closest_rubble_tiles_under_20, update_action_queue
from .robot import RobotM
from . import globals
import logging

class FactoryM(Factory):
    robots: list


    def build_units(self,env_cfg):
        # only builds one robot per factory
        if self.power*10 >= env_cfg.ROBOTS["HEAVY"].POWER_COST and \
        self.cargo.metal >= env_cfg.ROBOTS["HEAVY"].METAL_COST:
            # logging.info(f"Building heavy robot")
            globals.actions[self.unit_id] = self.build_heavy()
        elif self.power*5 >= env_cfg.ROBOTS["LIGHT"].POWER_COST and \
        self.cargo.metal >= env_cfg.ROBOTS["LIGHT"].METAL_COST:
            globals.actions[self.unit_id] = self.build_light()
            # logging.info(f"Building light robot")

    
    def water(self,obs,env_cfg):
        # if self.water_cost(globals.game_state) <= self.cargo.water -(150-obs["real_env_steps"]):
        
        if self.cargo.water >50:
            globals.actions[self.unit_id] = super().water()

        


    def command_units(self,env_cfg):

        for i in range(len(self.robots)):
            # logging.warning(i)
            # logging.info(f"digging robot {self.robots[0].unit_id} action queue: {self.robots[0].action_queue}")
            if i == 0:        
                self.robots[i].dig_nonstop()
            elif i == 1:
                self.robots[i].support_digging_robot(self.robots[0])
            # remove rubble around the factory
            else:
                closest_rubble_tiles = locate_closest_rubble_tiles_under_20(self.pos)[0]
                on_rubble_tile = locate_closest_rubble_tiles_under_20(self.robots[i].pos)[1]
                # logging.warning(on_rubble_tile)
                if on_rubble_tile:
                    update_action_queue(self.robots[i],self.robots[i].dig(repeat=1,n=1))
                else:
                    coord = closest_rubble_tiles[i]
                    self.robots[i].navigate_to_coordinate(coord)
                    update_action_queue(self.robots[i],self.robots[i].dig(repeat=1,n=1))

            # logging.info(f"digging robot {self.robots[0].unit_id} action queue: {self.robots[0].action_queue}")


