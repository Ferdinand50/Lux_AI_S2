import numpy as np
import math
import sys
import os
 
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lux.factory import Factory
from .utils import update_action_queue, absolute_distance, \
    get_lt_x_rubble_on_tiles_around_factory, locate_closest_resource, adjacent_to, adjacent_to_factory
from .robot import RobotM
from . import globals
import logging

MINIMUM_STEPS_WATERING = 100
MIN_WATER_IN_FACTORY = 15
NEED_SUPPORT = [
    'dig_ore',
    'heavy_dig_ore',
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
    transfer_resources_count: int = 0
    charge_power_count: int = 0

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
            elif unit.task == "heavy_dig_ore":
                self.heavy_dig_ore_count += 1
            elif unit.task == 'transfer_resources':
                self.transfer_resources_count += 1
            elif unit.task == 'charge_power':
                self.charge_power_count += 1
            # logging.info(f"\ntasks {self.unit_id}: {unit.unit_id}: {unit.task}")

        # ==========================================================================
        # configuration for unit task assignement
        # ==========================================================================
        # transfer resources
        # =================================
        if self.dig_ice_count > 0 and self.cargo.metal > 200:
            NUM_UNITS_TRANSFER_RESOURCES = 0
        else:
            NUM_UNITS_TRANSFER_RESOURCES = 0
        # =================================
        # dig ice
        # =================================
        if self.heavy_dig_ore_count > 0:
            NUM_UNITS_DIG_ICE = 1
        else:
            NUM_UNITS_DIG_ICE = 0
        # =================================
        # charge power
        # =================================
        if self.dig_ice_count == 1:
            NUM_UNITS_CHARGE_POWER = 1
        elif self.distribute_power_count > 2:
            NUM_UNITS_CHARGE_POWER = 2
        else:
            NUM_UNITS_CHARGE_POWER = 0
        # =================================
        # distribute power and remove rubble
        # =================================
        if self.charge_power_count == 0:
            NUM_UNITS_RM_RUBBLE = 1
            NUM_UNITS_DISTRIBUTE_POWER = 1
        elif self.charge_power_count == 1:
            NUM_UNITS_RM_RUBBLE = 2
            NUM_UNITS_DISTRIBUTE_POWER = 3
        else:
            NUM_UNITS_RM_RUBBLE = 3
            NUM_UNITS_DISTRIBUTE_POWER = 3

        reference_pos = next((unit.pos for unit in self.robots \
            if unit.task == 'heavy_dig_ore'),None)
        ore_distance = absolute_distance(self.pos,locate_closest_resource(self.pos,"ore",reference_pos=reference_pos)[0])
        if ore_distance > 10:
            NUM_HEAVY_DIG_ORE = 0
            NUM_UNITS_DISTRIBUTE_POWER = 0
            # change task of ore digging unit to ice digging
            if self.dig_ice_count == 0:
                unit = next((unit for unit in self.robots \
                    if unit.task == 'heavy_dig_ore'), None)
                if unit is not None:
                    globals.unit_tasks[unit.unit_id]['task'] = 'dig_ice'
                    unit.task = 'dig_ice'
                # assign light unit if the heavy one got destroyed
                else:
                    unit = next((unit for unit in self.robots \
                        if unit.task == 'distribute_power' \
                            or unit.task == 'rm_rubble'),None)
                    if unit is not None:
                        globals.unit_tasks[unit.unit_id]['task'] = 'dig_ice'
                        unit.task = 'dig_ice'
        elif ore_distance > 4:
            NUM_HEAVY_DIG_ORE = 1
            NUM_UNITS_DISTRIBUTE_POWER += 1
        else:
            NUM_HEAVY_DIG_ORE = 1

        # create more rm_rubble and distribute_power units
        if self.power > 800 and self.cargo.metal > 105:
            min_units = min(self.rm_rubble_count,self.distribute_power_count) + 1
            NUM_UNITS_DISTRIBUTE_POWER = min_units
            NUM_UNITS_RM_RUBBLE = min_units
        # ==========================================================================
        # end of configuration
        # ==========================================================================

        if self.support_dig_ice_count == 0 and self.dig_ice_count > 0:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None'),None)
            if unit == None:
                self.build_unit("LIGHT")                
            else:                
                globals.unit_tasks[unit.unit_id]['task'] = 'support_dig_ice'
                unit.task = 'support_dig_ice'                

        # logging.info(f"rubble_count: {self.rm_rubble_count}")
        if self.rm_rubble_count < NUM_UNITS_RM_RUBBLE:
            units = [unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None']
            if len(units) == 0:
                self.build_unit()
            else:               
                for unit in units[:NUM_UNITS_RM_RUBBLE+1]:                                      
                    globals.unit_tasks[unit.unit_id]['task'] = 'rm_rubble'
                    unit.task = 'rm_rubble'        

        if self.distribute_power_count < NUM_UNITS_DISTRIBUTE_POWER:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None'),None)
            if unit == None:
                self.build_unit("LIGHT")
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'distribute_power'
                unit.task = 'distribute_power'

        if self.heavy_dig_ore_count < NUM_HEAVY_DIG_ORE:
            unit = next((unit for unit in self.robots \
                    if unit.unit_type=="HEAVY" and unit.task == 'None'),None)
            if unit == None:
                if self.cargo.metal >= self.env_cfg.ROBOTS["HEAVY"].METAL_COST:
                    self.build_unit("HEAVY")
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'heavy_dig_ore'
                unit.task = 'heavy_dig_ore'

        if self.transfer_resources_count < NUM_UNITS_TRANSFER_RESOURCES:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="LIGHT" and unit.task == 'None'),None)
            if unit == None: 
                self.build_unit()
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'transfer_resources'
                unit.task = 'transfer_resources'
            
        if self.charge_power_count < NUM_UNITS_CHARGE_POWER:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="HEAVY" and unit.task == 'None'),None)
            if unit == None:
                self.build_unit("HEAVY")
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'charge_power'
                unit.task = 'charge_power'

        if self.dig_ice_count < NUM_UNITS_DIG_ICE:
            unit = next((unit for unit in self.robots \
                if unit.unit_type=="HEAVY" and unit.task == 'None'),None)
            if unit == None:
                self.build_unit("HEAVY")                
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'dig_ice'
                unit.task = 'dig_ice'


        # assign tasks to all units which are doing nothing
        jobless_units =[unit for unit in self.robots if unit.task == 'None']
        for unit in jobless_units:
            if unit.unit_type == "LIGHT":
                globals.unit_tasks[unit.unit_id]['task'] = 'distribute_power'
                unit.task = 'distribute_power'
            else:
                globals.unit_tasks[unit.unit_id]['task'] = 'dig_ice'
                unit.task = 'dig_ice'



    def water(self,obs,step):
        if self.cargo.water - super().water_cost(globals.game_state) > MIN_WATER_IN_FACTORY \
            and step > MINIMUM_STEPS_WATERING:
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
                    # if self.power < 75 and adjacent_to_factory(self.pos,unit.pos):
                    #     unit.charge_power(r=0)
                    # else:
                    unit.dig_ore()
                elif unit.task == 'rm_rubble':
                    unit.rm_rubble()
                elif unit.task == 'distribute_power':
                    unit.distribute_power()
                elif unit.task == 'charge_power':
                    unit.charge_power(r=1)
                    pass
                elif unit.task == 'transfer_resources':
                    unit.transfer_resources()


    def improve_task_execution(self):
        for unit in self.robots:
            if unit.task == 'distribute_power':
                adjacent_units = [u for u in self.robots if adjacent_to(unit.pos,u.pos)]
                if len(adjacent_units):
                    unit.distribute_power_advanced(adjacent_units)


    def build_unit(self,unit_type="LIGHT"):
        globals.pickup_power[self.unit_id] = True

        unit_on_spwan = globals.unit_positions.any() and \
             np.any(np.all(self.pos == globals.unit_positions,1))
        if not unit_on_spwan:        
            if unit_type == "HEAVY":
                if self.power >= self.env_cfg.ROBOTS["HEAVY"].POWER_COST:
                    if self.cargo.metal >= self.env_cfg.ROBOTS["HEAVY"].METAL_COST:
                        globals.actions[self.unit_id] = self.build_heavy()
                else:
                    # stop work if factory does not have enough power
                    globals.pickup_power[self.unit_id] = False
            else:
                if self.power >= self.env_cfg.ROBOTS["LIGHT"].POWER_COST and \
                self.cargo.metal >= self.env_cfg.ROBOTS["LIGHT"].METAL_COST:
                    globals.actions[self.unit_id] = self.build_light()
        
        