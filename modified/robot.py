import sys
import os
 
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
 
from lux.unit import Unit
from lux.utils import direction_to
from .utils import navigate_from_to, update_action_queue, \
    locate_closest_factory, locate_closest_ice_tile, locate_closest_ore_tile, \
    locate_closest_resource, adjacent_to, get_action_queue_head, get_units_next_action, \
    locate_closest_rubble_tiles_under_20
from . import globals
import logging

POWER_PICK_UP_AMOUNT = 125
TRANSFER_POWER_AMOUNT = 131

class RobotM(Unit):

    def action_queue_cost(self):
        cost = self.env_cfg.ROBOTS[self.unit_type].ACTION_QUEUE_POWER_COST
        return cost

    def bind_to_closest_factory(self):
        closest_factory = locate_closest_factory(self.pos)[0]
        closest_factory.robots.append(self)


    def navigate_to_coordinate(self,target_pos):
        direction_orders = navigate_from_to(self.pos,target_pos)
        if direction_orders[0] != 0:
            action = self.move(direction_orders[0],repeat=0,n=direction_orders[1])
            update_action_queue(self,action)
        if direction_orders[2] != 0:
            action = self.move(direction_orders[2],repeat=0,n=direction_orders[3])
            update_action_queue(self,action)    
    

    def navigate_to_factory(self,game_state):
        [closest_factory_tile,adjacent_to_factory] = locate_closest_factory(game_state,self.pos)[1:2]
        if not adjacent_to_factory:
            self.navigate_to_coordinate(closest_factory_tile)
        return adjacent_to_factory


    def navigate_to_ice_tile(self,game_state):
        [closest_ice_tile, on_ice_tile] = locate_closest_ice_tile(game_state,self.pos)
        if not on_ice_tile:
            self.navigate_to_coordinate(self,closest_ice_tile)
        return on_ice_tile


    def navigate_to_ore_tile(self,game_state):
        [closest_ore_tile, on_ore_tile] = locate_closest_ore_tile(game_state,self.pos)
        if not on_ore_tile:
            self.navigate_to_coordinate(self,closest_ore_tile)
        return on_ore_tile
        

    def calculate_free_cargo(self):
        free_cargo = self.env_cfg.ROBOTS[self.unit_type].CARGO_SPACE
        free_cargo -= (self.cargo.ice+self.cargo.ore+self.cargo.water+self.cargo.metal)
        return free_cargo
    
    def transfer_resources(self):
        # always transfer all resources to factory
        pass


    def support_digging_robot(self,digging_robot):
        
        # try to get the next action digging_robot is executing
        digging_robot_action = get_units_next_action(digging_robot)
        # if unit is next to the digging robot and the digging robot is standing still
        if adjacent_to(self.pos,digging_robot.pos) and digging_robot_action != 0:
             # transfer power to digging robot
            if self.power >= self.action_queue_cost():
                direction = direction_to(self.pos,digging_robot.pos)
                action = super().transfer(direction,4,TRANSFER_POWER_AMOUNT, repeat=1)
                update_action_queue(self,action)

            #transfer resources to factory and pickup power
            closest_factory_tile = locate_closest_factory(self.pos)[1]
            if adjacent_to(self.pos,closest_factory_tile):
                if self.power >= self.action_queue_cost():
                    action = super().pickup(4,POWER_PICK_UP_AMOUNT,repeat=1)
                    update_action_queue(self,action)
                    direction = direction_to(self.pos,closest_factory_tile)
                    action = super().transfer(direction,0,self.cargo.ice,repeat=1)
                    update_action_queue(self,action)

            # transfer resources to supporting robot
            if digging_robot.power >= self.action_queue_cost():
                direction = direction_to(digging_robot.pos,self.pos)                
                action = super().transfer(direction,0,self.calculate_free_cargo(),repeat=1)
                update_action_queue(digging_robot,action)


        # navigate to digging robot
        # FOR FUTURE: UNIT COLLISION (has heavy enough power to move next turn) 
        else:
            self.navigate_to_coordinate(digging_robot.pos)

        
        

    def dig_nonstop(self):
        [closest_resource_tile, on_resource_tile] = locate_closest_resource(self.pos,"ice")
        if on_resource_tile:
            # start digging 
            if self.power >= self.action_queue_cost():      
                # add digging action 5 times, because even repeat = 1 will repeat the action of 
                # finishing it, but will reset n to 1, which is inefficient, since the roboter should 
                # transfer at least the max cargo space of a supporting (light) robot or even more if 
                # it (digging heavy robot) stands next to the factory               
                update_action_queue(self,super().dig(repeat=1,n=1))                    
                update_action_queue(self,super().dig(repeat=1,n=1))                    
                update_action_queue(self,super().dig(repeat=1,n=1))                    
                update_action_queue(self,super().dig(repeat=1,n=1))                    
                update_action_queue(self,super().dig(repeat=1,n=1))                    
        else:
            # navigate towards resource tile
            self.navigate_to_coordinate(closest_resource_tile)


    def remove_surrounding_rubble(self):
        pass

    


    # def collect_ice(self,game_state):
    #     free_cargo = self.calculate_free_cargo()
    #     logging.info(f"free_cargo: {free_cargo}")
    #     if free_cargo > 900:
    #         # POSSIBLE BUG: is unit.unit_id the same as for unit_id, unit in unit.items()???
    #         on_ice_tile = self.navigate_to_ice_tile(game_state)
    #         # if already there, start digging
    #         if on_ice_tile:
    #             self.dig(game_state)
    #     else:
    #         logging.info(f"robot is returning to factory to deliver ice")
    #         # go to factory if unit.cargo is full and transfer ice if already there
    #         adjacent_to_factory = self.navigate_to_factory(game_state)
    #         # if already there, transfer resources
    #         if adjacent_to_factory:
    #             if self.power >= self.action_queue_cost(game_state):
    #                 update_action_queue(self,self.transfer(0,0,self.cargo.ice,repeat=0))

    def collect_ice(self,game_state):
            on_ice_tile = self.navigate_to_ice_tile(game_state)
            if on_ice_tile:
                self.dig(game_state)


    def collect_ore(self,game_state):
            on_ore_tile = self.navigate_to_ore_tile(game_state)
            if on_ore_tile:
                self.dig(game_state)
        
    

    # def collect_ore(self,game_state):
    #     free_cargo = self.calculate_free_cargo()
    #     if free_cargo > 0:
    #         # POSSIBLE BUG: is unit.unit_id the same as for unit_id, unit in unit.items()???
    #         on_ore_tile = self.navigate_to_ore_tile(game_state)
    #         # if already there, start digging
    #         if on_ore_tile:
    #             self.dig(game_state)
    #     else:
    #         adjacent_to_factory = self.navigate_to_factory(game_state)
    #         if adjacent_to_factory:
    #             if self.power >= self.action_queue_cost(game_state):
    #                 update_action_queue(self.unit_id,self.transfer(0,0,self.cargo.ore)) 
    #                 # WARNING: missing parameter?!


    