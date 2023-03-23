import math
from sys import stderr
import numpy as np
from dataclasses import dataclass
from lux.cargo import UnitCargo
from lux.config import EnvConfig
@dataclass
class Factory:
    team_id: int
    unit_id: str
    strain_id: int
    power: int
    cargo: UnitCargo
    pos: np.ndarray
    # lichen tiles connected to this factory
    # lichen_tiles: np.ndarray
    env_cfg: EnvConfig
    robots: list


    def build_units(self,env_cfg):
        # only builds one robot per factory
        if self.power*10 >= env_cfg.ROBOTS["HEAVY"].POWER_COST and \
        self.cargo.metal >= env_cfg.ROBOTS["HEAVY"].METAL_COST:
            globals.actions[self.unit_id] = self.build_heavy()
            #TODO: create robot object
    
        elif self.power*5 >= env_cfg.ROBOTS["LIGHT"].POWER_COST and \
        self.cargo.metal >= env_cfg.ROBOTS["LIGHT"].METAL_COST:
            globals.actions[self.unit_id] = self.build_light()
            #TODO: create robot object

    
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
            # else:
            #     closest_rubble_tiles = locate_closest_rubble_tiles_under_20(self.pos)[0]
            #     on_rubble_tile = locate_closest_rubble_tiles_under_20(self.robots[i].pos)[1]
            #     # logging.warning(on_rubble_tile)
            #     if on_rubble_tile:
            #         update_action_queue(self.robots[i],self.robots[i].dig(repeat=1,n=1))
            #     else:
            #         coord = closest_rubble_tiles[i]
            #         self.robots[i].navigate_to_coordinate(coord)
            #         update_action_queue(self.robots[i],self.robots[i].dig(repeat=1,n=1))

            # logging.info(f"digging robot {self.robots[0].unit_id} action queue: {self.robots[0].action_queue}")



################## unchanged ######################

    def build_heavy_metal_cost(self, game_state):
        unit_cfg = self.env_cfg.ROBOTS["HEAVY"]
        return unit_cfg.METAL_COST
    def build_heavy_power_cost(self, game_state):
        unit_cfg = self.env_cfg.ROBOTS["HEAVY"]
        return unit_cfg.POWER_COST
    def can_build_heavy(self, game_state):
        return self.power >= self.build_heavy_power_cost(game_state) and self.cargo.metal >= self.build_heavy_metal_cost(game_state)
    def build_heavy(self):
        return 1

    def build_light_metal_cost(self, game_state):
        unit_cfg = self.env_cfg.ROBOTS["LIGHT"]
        return unit_cfg.METAL_COST
    def build_light_power_cost(self, game_state):
        unit_cfg = self.env_cfg.ROBOTS["LIGHT"]
        return unit_cfg.POWER_COST
    def can_build_light(self, game_state):
        return self.power >= self.build_light_power_cost(game_state) and self.cargo.metal >= self.build_light_metal_cost(game_state)

    def build_light(self):
        return 0

    def water_cost(self, game_state):
        """
        Water required to perform water action
        """
        owned_lichen_tiles = (game_state.board.lichen_strains == self.strain_id).sum()
        return np.ceil(owned_lichen_tiles / self.env_cfg.LICHEN_WATERING_COST_FACTOR)
    def can_water(self, game_state):
        return self.cargo.water >= self.water_cost(game_state)
    def water(self):
        return 2

    @property
    def pos_slice(self):
        return slice(self.pos[0] - 1, self.pos[0] + 2), slice(self.pos[1] - 1, self.pos[1] + 2)
