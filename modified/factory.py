import numpy as np
import math
import sys
import os
 
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lux.factory import Factory
from .utils import update_action_queue, \
    get_lt_x_rubble_on_tiles_around_factory, locate_closest_resource
from .robot import RobotM
from . import globals
import logging

MIN_WATER_IN_FACTORY = 15
NEED_SUPPORT = [
    'dig_ore',
    'dig_ice',

]


class FactoryM(Factory):
    robots: list
    dig_ice_count: int = 0
    dig_ore_count: int = 0
    heavy_dig_ore_count: int = 0
    support_dig_ice_count: int = 0
    rm_rubble_count: int = 0
    distribute_power_count: int = 0

    def assign_tasks(self):
        # self.dig_ice_count = 0
        # self.dig_ore_count = 0
        # self.support_dig_ice_count = 0
        for unit in self.robots:        
            if unit.task == "dig_ice":
                self.dig_ice_count += 1
            elif unit.task == "dig_ore":
                self.dig_ore_count += 1
            elif unit.task == "support_dig_ice":
                self.support_dig_ice_count += 1
            elif unit.task == "rm_rubble":
                self.rm_rubble_count += 1
            elif unit.task == 'distribute_power':
                self.distribute_power_count += 1
            elif unit.task == "heaby_dig_ore":
                self.heaby_dig_ore_count += 1

        # ==========================================================================
        # configuration for unit task assignement
        # ==========================================================================
        # NUM_UNITS_RM_RUBBLE = 1
        NUM_UNITS_RM_RUBBLE = \
            min(0,len(get_lt_x_rubble_on_tiles_around_factory(self.pos)))        
        NUM_UNITS_DISTRIBUTE_POWER = min(3,len([unit for unit in self.robots \
            if unit.task in NEED_SUPPORT]))        

        if self.support_dig_ice_count == 0 and self.dig_ice_count > 0:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None'),None)
            if unit == None:
                self.build_unit("LIGHT")                
            else:                
                globals.unit_tasks[unit.unit_id]['task'] = 'support_dig_ice'
                unit.task = 'support_dig_ice'                

        if (self.dig_ore_count+self.heavy_dig_ore_count) == 0:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None'),None)
            if unit == None:               
                self.build_unit("LIGHT")
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'dig_ore'
                unit.task = 'dig_ore'
        elif self.heavy_dig_ore_count == 0:
            unit = next((unit for unit in self.robots \
                    if unit.unit_type=="HEAVY" and unit.task == 'None'),None)
            if unit == None:
                if self.cargo.metal >= self.env_cfg.ROBOTS["HEAVY"].METAL_COST:
                    logging.info("testtest factpry-py")
                    self.build_unit("HEAVY")
            else:
                logging.info("djfaölksdjf factpry-py")
                globals.unit_tasks[unit.unit_id]['task'] = 'heavy_dig_ore'
                unit.task = 'heavy_dig_ore'
                # change task of light unit digging ore to distribute power
                light_unit = next((unit for unit in self.robots \
                    if unit.unit_type=="LIGHT" and unit.task == 'dig_ore'))
                if light_unit is not None:
                    globals.unit_tasks[light_unit.unit_id]['task'] = 'distribute_power'
                    light_unit.task = 'distribute_power'

        if self.distribute_power_count < NUM_UNITS_DISTRIBUTE_POWER:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None'),None)
            if unit == None:
                self.build_unit("LIGHT")
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'distribute_power'
                unit.task = 'distribute_power'

        if self.rm_rubble_count < NUM_UNITS_RM_RUBBLE:
            logging.info("aösdfknaösdfjpaosdi")
            units = [unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None']
            if len(units) == 0:
                self.build_unit()
            else:               
                for unit in units[:NUM_UNITS_RM_RUBBLE]:                                      
                    globals.unit_tasks[unit.unit_id]['task'] = 'rm_rubble'
                    unit.task = 'rm_rubble'
        # elif self.rm_rubble_count > NUM_UNITS_RM_RUBBLE:
        #     units = [unit for unit in self.robots \
        #         if unit.task == 'rm_rubble']
        #     for unit in units:
        #         globals.unit_tasks[unit.unit_id]['task'] = 'attack'
        #         unit.task = 'attack'


        if self.dig_ice_count == 0:
            # FOR FUTURE IMPLEMENTATION: decide which robot should farm ice based on distance
            # closest_ice_tile = locate_closest_resource(self.pos,"ice")[0]
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="HEAVY" and unit.task == 'None'),None)
            if unit == None:
                self.build_unit("HEAVY")                
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'dig_ice'
                unit.task = 'dig_ice'



    def water(self,obs):
        if self.cargo.water - super().water_cost(globals.game_state) > MIN_WATER_IN_FACTORY:
            globals.actions[self.unit_id] = super().water()                    


    def execute_tasks(self):
        for unit in self.robots:     
            if len(unit.action_queue) == 0:       
                if unit.task == "dig_ice":
                    unit.dig_ice()
                elif unit.task == "support_dig_ice" and self.dig_ice_count > 0:
                    dig_ice_unit = next(u for u in self.robots if u.task == 'dig_ice')
                    unit.units_assisting = [dig_ice_unit]
                    unit.support_dig_ice(dig_ice_unit)
                elif unit.task == "dig_ore" or unit.task == "heavy_dig_ore":
                    unit.dig_ore()
                elif unit.task == 'rm_rubble':
                    unit.rm_rubble()
                elif unit.task == 'distribute_power':
                    unit.distribute_power()

    def build_unit(self,unit_type="LIGHT"):
        # only builds one robot per factory
        unit_on_spwan = globals.unit_positions.any() and \
             np.any(np.all(self.pos == globals.unit_positions,1))
        if not unit_on_spwan:
            if unit_type == "HEAVY":
                if self.power >= self.env_cfg.ROBOTS["HEAVY"].POWER_COST and \
                self.cargo.metal >= self.env_cfg.ROBOTS["HEAVY"].METAL_COST:
                    globals.actions[self.unit_id] = self.build_heavy()
            else:
                if self.power >= self.env_cfg.ROBOTS["LIGHT"].POWER_COST and \
                self.cargo.metal >= self.env_cfg.ROBOTS["LIGHT"].METAL_COST:
                    globals.actions[self.unit_id] = self.build_light()
        