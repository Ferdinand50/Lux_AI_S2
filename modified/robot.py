import sys
import os
 
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
 
import math
import numpy as np
import numpy.typing as npt
from math import ceil
from lux.unit import Unit
from lux.utils import direction_to
from .utils import update_action_queue, \
    locate_closest_factory, append_to_action_queue, locate_closest_resource \
    ,adjacent_to, get_action_queue_head, get_units_next_action, \
    on_factory, dijkstra, get_path, direction_array_delta, \
    get_lt_x_rubble_on_tiles_around_factory, get_enemy_factory_tiles, \
    absolute_distance, locate_closest_factory_tile, find_most_desperate_unit, \
    get_empty_adjoining_tile, get_adjoining_tiles
from . import globals
import logging

ICE_DIG_POWER_PICKUP = 125

MIN_SPARE_FACTORY_POWER = 200
MIN_SPARE_POWER_DISTRIBUTE_UNIT = 30
MIN_SPARE_POWER_RM_RUBBLE = 55
MIN_RESOURCES_IN_UNIT = 50
TRANSFER_POWER_AMOUNT = 120
MIN_POWER_PICKUP_DISTRIBUTE_UNIT = 50
DISTRIBUTE_POWER_PICKUP_MIN = 50
RM_RUBBLE_POWER_PICKUP = 50
ICE_DIG_POWER_TRANSFER = 145
MIN_ORE_IN_CARGO = 15
NEED_SUPPORT = [
    'dig_ore',
    'dig_ice'    
]

class RobotM(Unit):
    # description of the unit task
    task: str
    # number states how many units have been assigned 
    # the same task before this unit
    task_rank: int        
    # list of units which need help to fullfil their task
    units_assisting: list
    # attributes helps other units to support
    moving_destination: npt.NDArray
    # does the unit already get help
    receiving_help: bool = False
        

    def action_queue_cost(self):
        cost = self.env_cfg.ROBOTS[self.unit_type].ACTION_QUEUE_POWER_COST
        return cost

    def bind_to_closest_factory(self):
        closest_factory = locate_closest_factory(self.pos)[0]
        closest_factory.robots.append(self)


    def navigate_to_coordinate(self,dst_node_org,repeat=0):        
        dst_node = np.copy(dst_node_org)
       # navigate next to dst_node if dst_node is occupied by ally unit
        if np.any(np.all(dst_node == globals.unit_positions,1)):            
            direction = direction_to(dst_node,self.pos)
            dst_node += direction_array_delta(direction)

        # abort if dst_node is the same as the current position
        if np.all(self.pos == dst_node):
            return -1

        self.moving_destination = dst_node

        graph = (np.copy(globals.game_state.board.rubble) \
            * self.env_cfg.ROBOTS[self.unit_type].RUBBLE_MOVEMENT_COST).astype(int)
        graph += self.env_cfg.ROBOTS[self.unit_type].MOVE_COST
        # graph = math.floor(np.copy(globals.game_state.board.rubble) \
        #     * self.env_cfg.ROBOTS[self.unit_type].RUBBLE_MOVEMENT_COST)
        # logging.warning(graph)
        # consider ally units and enemy factories on board
        obstacles = get_enemy_factory_tiles()
        obstacles = np.append(obstacles,globals.unit_positions).reshape((-1,2))
        for obstacle in obstacles:
            graph[tuple(obstacle)] = 2047483647

        # add close opponent units as obstacle to the graph
        obstacles = np.empty((0,2),dtype=int)
        opp_units = globals.game_state.units[globals.opp_player].values()
        # close_opp_units = [opp_u for opp_u in opp_units \
        #     if absolute_distance(self.pos,opp_u.pos) < 4]
        for opp_u in opp_units:
            dangerous_tiles = get_adjoining_tiles(opp_u.pos)
            dangerous_tiles.append(opp_u.pos)
            obstacles = np.append(obstacles,dangerous_tiles).reshape((-1,2))
        for obstacle in obstacles:
            graph[tuple(obstacle)] = 1047483647

        distances, prev_node = dijkstra(graph,tuple(dst_node),tuple(self.pos))
        path = get_path(distances,prev_node,tuple(dst_node),tuple(self.pos))

        directions = []
        prev_pos = path[0]
        for p in path[1:]:
            directions.append(direction_to(np.array(prev_pos),np.array(p)))
            prev_pos = p
        directions.append(-1)

        pickup_amount = self.env_cfg.ROBOTS[self.unit_type].BATTERY_CAPACITY - self.power
        # factory_tile = locate_closest_factory_tile(self.pos)        
        # if np.all(factory_tile == self.pos) and 0 < pickup_amount:
        #     action = super().pickup(4,pickup_amount)
        #     update_action_queue(self,action)

        # shorten the action queue to avoid a action queue length > 20
        n = 1
        for i,d in enumerate(directions[:-1]):
            if d == directions[i+1]:
                n += 1
            else:
                factory_tile = locate_closest_factory_tile(path[i-(n-1)])
                # logging.warning(f"id: {self.unit_id}, n: {n}")
                if np.all(path[i-(n-1)] == factory_tile) and self.power < (130 if self.unit_type == "LIGHT" else 300) \
                    and pickup_amount > 0:                     
                    action = super().pickup(4,pickup_amount)
                    update_action_queue(self,action)

                    if (self.cargo.ice) > 0: 
                        action = super().transfer(0,0,self.cargo.ice)
                        update_action_queue(self,action)
                    if self.cargo.ore > 0:
                        action = super().transfer(0,1,self.cargo.ore)
                        update_action_queue(self,action)

                action = super().move(d,repeat=repeat,n=n)
                append_to_action_queue(self,action)
                n = 1

                # pickup power if standing on factory anyway
                # if np.all(path[i] == factory_tile) and self.power < (130 if self.unit_type == "LIGHT" else 300) \
                #     and n <= 3 and pickup_amount > 0:
                #     action = super().pickup(4,pickup_amount)
                #     update_action_queue(self,action)

        if len(directions) and self.power >= \
            super().move_cost(globals.game_state,directions[0]) + self.action_queue_cost():
            idx = [np.argwhere(np.all(globals.unit_positions == self.pos,1,))][0]
            np.delete(globals.unit_positions, idx)
            globals.unit_positions = np.append(globals.unit_positions,path[1]).reshape((-1,2))
            

    def total_move_cost(self,dst_node_org):
        dst_node = np.copy(dst_node_org)        

        graph = (np.copy(globals.game_state.board.rubble) \
            * self.env_cfg.ROBOTS[self.unit_type].RUBBLE_MOVEMENT_COST).astype(int)
        graph += self.env_cfg.ROBOTS[self.unit_type].MOVE_COST
        # consider ally units and enemy factories on board
        obstacles = get_enemy_factory_tiles()
        obstacles = np.append(obstacles,globals.unit_positions).reshape((-1,2))
        for obstacle in obstacles:
            graph[tuple(obstacle)] = 2047483647

        # add close opponent units as obstacle to the graph
        obstacles = np.empty((0,2),dtype=int)
        opp_units = globals.game_state.units[globals.opp_player].values()
        close_opp_units = [opp_u for opp_u in opp_units \
            if absolute_distance(self.pos,opp_u.pos) < 4]
        for opp_u in close_opp_units:
            dangerous_tiles = get_adjoining_tiles(opp_u.pos)
            dangerous_tiles.append(opp_u.pos)
            obstacles = np.append(obstacles,dangerous_tiles).reshape((-1,2))
        for obstacle in obstacles:
            graph[tuple(obstacle)] = 1047483647


        distances, prev_node = dijkstra(graph,tuple(dst_node),tuple(self.pos))
        path = get_path(distances,prev_node,tuple(dst_node),tuple(self.pos))
        # logging.warning(f"path: {path}, id: {self.unit_id}")
        total_move_cost = sum([self.move_cost_at_dst(p) for p in path[1:]])
        # logging.info(f"total move cost: {total_move_cost}")
        # logging.info(f"path: {path}")        
        return total_move_cost


    def move_cost_at_dst(self,dst):
        board = globals.game_state.board
        if dst[0] < 0 or dst[1] < 0 or dst[1] >= len(board.rubble) or dst[0] >= len(board.rubble[0]):
            logging.warning(f"Warning, tried to get move cost for going off the map")
            return None
        factory_there = board.factory_occupancy_map[dst[0], dst[1]]
        if factory_there not in globals.game_state.teams[self.agent_id].factory_strains and factory_there != -1:
            logging.warning(f"Warning, tried to get move cost for going onto a opposition factory")
            return None
        rubble_at_dst = board.rubble[tuple(dst)]
        return math.floor(self.unit_cfg.MOVE_COST + self.unit_cfg.RUBBLE_MOVEMENT_COST * rubble_at_dst)


    def calculate_free_cargo(self):
        free_cargo = self.env_cfg.ROBOTS[self.unit_type].CARGO_SPACE
        free_cargo -= (self.cargo.ice+self.cargo.ore+self.cargo.water+self.cargo.metal)
        return free_cargo
    
    def transfer_resources(self):
        # always transfer all resources to factory
        pass


    # def dig_ore(self):
    #     [closest_ore_tile, on_ore_tile] = locate_closest_resource(self.pos,"ore")
    #     closeest_factory_tile = locate_closest_factory(self.pos)[1]
    #     # pick up power if standing on factory
    #     if on_factory(self.pos,closeest_factory_tile):
    #         action = super().pickup(4,ORE_DIG_POWER_PICKUP,repeat=1,n=1)
    #         update_action_queue(self,action)
    #     # if not on ore tile navigate now 
    #     if not on_ore_tile:
    #         self.navigate_to_coordinate(closest_ore_tile,repeat=1)
    #     # dig for some time
    #     # for i in range(10):
    #     else:
    #         update_action_queue(self,super().dig(repeat=1,n=10))
    #     if self.cargo.ore > MIN_ORE_IN_CARGO:
    #         self.navigate_to_coordinate(closeest_factory_tile,repeat=1)
    #     if on_factory(self.pos,closeest_factory_tile):
    #         action = super().transfer(0,1,self.cargo.ore,repeat=1,n=1)
    #         update_action_queue(self,action)

    def recalculate_task(self):
        if self.task == 'dig_ice':
            self.dig_ice()
        elif self.task == 'dig_ore':
            self.dig_ore()
        elif self.task == 'support_dig_ice':
            self.support_dig_ice(self.units_assisting[0])
        elif self.task == 'rm_rubble':
            self.rm_rubble()


    def dig_ore(self):
        [closest_ore_tile, on_ore_tile] = locate_closest_resource(self.pos,"ore")
        closeest_factory_tile = locate_closest_factory(self.pos)[1]
        # pick up power and transfer resources if standing on factory
        if on_factory(self.pos,closeest_factory_tile):
            pickup_amount = self.env_cfg.ROBOTS[self.unit_type].BATTERY_CAPACITY - self.power
            action = super().pickup(4,pickup_amount)
            append_to_action_queue(self,action)
            if self.cargo.ore > 0:
                action = super().transfer(0,1,self.cargo.ore)
                append_to_action_queue(self,action)
        
        # dig ore
        if on_ore_tile:
            update_action_queue(self,super().dig(repeat=0,n=10))
        # navigate to factory
        if self.calculate_free_cargo() == 0:
            self.navigate_to_coordinate(closeest_factory_tile)
         # navgigate to ore tile
        elif not on_ore_tile:
            self.navigate_to_coordinate(closest_ore_tile)


        

    def support_dig_ice(self,digging_robot):        
        # try to get the next action digging_robot is executing
        digging_robot_action = get_units_next_action(digging_robot)[0]
        # if unit is next to the digging robot and the digging robot is standing still
        if adjacent_to(self.pos,digging_robot.pos) and digging_robot_action != 0:
             # transfer power to digging robot
            if self.power >= self.action_queue_cost():
                direction = direction_to(self.pos,digging_robot.pos)
                action = super().transfer(direction,4,ICE_DIG_POWER_TRANSFER, repeat=1)
                update_action_queue(self,action)

            #transfer resources to factory and pickup power
            closest_factory_tile = locate_closest_factory(self.pos)[1]
            if adjacent_to(self.pos,closest_factory_tile):
                if self.power >= self.action_queue_cost():
                    action = super().pickup(4,ICE_DIG_POWER_PICKUP,repeat=1)
                    update_action_queue(self,action)
                    direction = direction_to(self.pos,closest_factory_tile)
                    action = super().transfer(direction,0,self.cargo.ice,repeat=1)
                    update_action_queue(self,action)

            # transfer resources to supporting robot
            # if digging_robot.power >= self.action_queue_cost():
            #     direction = direction_to(digging_robot.pos,self.pos)                
            #     action = super().transfer(direction,0,self.calculate_free_cargo(),repeat=1)
            #     update_action_queue(digging_robot,action)


        # navigate to digging robot
        # FOR FUTURE: UNIT COLLISION (has heavy enough power to move next turn) 
        else:
            direction = direction_to(digging_robot.pos,self.pos)
            pos_next_to_digging_robot = digging_robot.pos + \
                direction_array_delta(direction)
            self.navigate_to_coordinate(pos_next_to_digging_robot)

        
        

    def dig_ice(self):        
        host_factory_id = globals.unit_tasks[self.unit_id]['host_factory']
        host_factory = globals.factory_units[host_factory_id]
        closest_resource_tile = \
            locate_closest_resource(self.pos,"ice",reference_pos=host_factory.pos)[0]

        # navigate towards resource tile
        self.navigate_to_coordinate(closest_resource_tile)    
        # start digging 
        if self.power >= self.action_queue_cost():      
            # add digging action 5 times, because even repeat = 1 will repeat the action of 
            # finishing it, but will reset n to 1, which is inefficient, since the roboter should 
            # transfer at least the max cargo space of a supporting (light) robot or even more if 
            # it (digging heavy robot) stands next to the factory               
            append_to_action_queue(self,super().dig(repeat=1,n=1))                    
            append_to_action_queue(self,super().dig(repeat=1,n=1))                    
            append_to_action_queue(self,super().dig(repeat=1,n=1))                    
            append_to_action_queue(self,super().dig(repeat=1,n=1))                    
            append_to_action_queue(self,super().dig(repeat=1,n=1))
            direction = direction_to(closest_resource_tile,host_factory.pos)                
            action = super().transfer(direction,0,self.calculate_free_cargo(),repeat=1)
            update_action_queue(self,action)                  
       
            


    def rm_rubble(self):
        closest_factory_tile = locate_closest_factory_tile(self.pos)
        rubble_tiles = get_lt_x_rubble_on_tiles_around_factory(closest_factory_tile,self.pos)
        # pick up power
        

        def handle_error():
            self.task = 'None'
            del globals.unit_tasks[self.unit_id]

        if self.power < MIN_SPARE_POWER_RM_RUBBLE:
            # logging.warning(f"power: {self.power} (robot.py)")
            self.navigate_to_coordinate(closest_factory_tile)
                # pickup power if there
                # pickup_amount = self.env_cfg.ROBOTS[self.unit_type].BATTERY_CAPACITY - self.power        
                # action = super().pickup(4,pickup_amount,repeat=0)
                # update_action_queue(self,action)
        # navigate to rubble tile and dig                
        elif len(rubble_tiles):
            # change the target rubble tile as long as the target rubble tile 
            # is occupied by a ally unit
            i = 0        
            while np.any(np.all(globals.unit_positions == rubble_tiles[i],1)):
                i += 1
                # change the task of unit if no more rubble_tiles are available
                if i == len(rubble_tiles):
                    handle_error()
                    return -1
                
            # navigote to tile
            self.navigate_to_coordinate(rubble_tiles[i])   
            # calculate how many steps are needed to remove rubble from tile
            rubble_map = globals.game_state.board.rubble
            rubble_value = rubble_map[tuple(rubble_tiles[i])]
            n = max(1,ceil(rubble_value / self.env_cfg.ROBOTS[self.unit_type].DIG_RUBBLE_REMOVED))
            update_action_queue(self,super().dig(n=n))
        else:
            handle_error()
        

    def distribute_power(self):
        host_factory_id = globals.unit_tasks[self.unit_id]['host_factory']
        host_factory = globals.factory_units[host_factory_id]
        factory_pos = locate_closest_factory_tile(self.pos)

        # pick up power
        pickup_amount = self.env_cfg.ROBOTS[self.unit_type].BATTERY_CAPACITY - self.power
        if on_factory(host_factory.pos,self.pos) and pickup_amount > 0:
            action = super().pickup(4,pickup_amount)
            update_action_queue(self,action)

        # navigate to unit which is in need (has the fewest power, but move forward if it is moving)
        units_in_need = [unit for unit in host_factory.robots if unit.task in NEED_SUPPORT]
        # if len(units_in_need) == 0:
        #     self.task = 'None'
        #     globals.unit_tasks[self.unit_id]['task'] = 'None'    
        #     return -1 
        unit = find_most_desperate_unit(self,units_in_need)

        # remove rubble if there is no work to do yet
        if unit is None:
            if self.power < 90: # and not on_factory(self.pos,host_factory.pos):
                self.navigate_to_coordinate(factory_pos)
            else:
                self.rm_rubble()
            return -1 

        if self.power > (self.total_move_cost(unit.pos) * 2) \
            + self.total_move_cost(factory_pos) + 30:
            # WARNING: not working like, since it gets resetted next step, move this to globals.init_once
            unit.receiving_help = True
            # navigigate to unit and supply power and pickup resources
            pos_next_to = get_empty_adjoining_tile(self.pos,unit.pos)
            # abort mission if there is free tile next to the unit
            if pos_next_to is None:
                return -1
            if self.navigate_to_coordinate(pos_next_to) == -1:
                # transfer resources to assisting unit (self) if the units cargo
                # reaches the threshold "MIN_RESOURCES_IN_UNIT", so its worth
                # to update the units action queue
                if max(unit.cargo.ice, unit.cargo.ore) > MIN_RESOURCES_IN_UNIT:
                    direction = direction_to(unit.pos,self.pos)
                    transfer_resource = 0 if unit.cargo.ice > unit.cargo.ore else 1
                    transfer_amount = self.calculate_free_cargo()
                    action = unit.transfer(direction,transfer_resource,transfer_amount)
                    update_action_queue(unit,action,overwrite=True)

                # transfer power to unit
                next_action = get_units_next_action(unit)
                if next_action[0] != 0:
                    direction = direction_to(self.pos,unit.pos) 
                    # calculate how much power should be transfered 
                    requested_transfer_amount = \
                        (self.env_cfg.ROBOTS[unit.unit_type].BATTERY_CAPACITY-unit.power) + 5
                    available_power = (self.power - self.total_move_cost(factory_pos)) - 5
                    transfer_amount = min(available_power,requested_transfer_amount)
                    # logging.info(f"id: {self.unit_id}, req_trans_amount: {requested_transfer_amount} trans_amount: {transfer_amount}")
                    if transfer_amount > 0:
                        action = super().transfer(direction,4,transfer_amount)
                        update_action_queue(self,action,overwrite=True)
        # navigate to host factory, pickup power and transfer ice/ ore to factory
        else:
            unit.receiving_help = False
            pickup_amount = self.env_cfg.ROBOTS[self.unit_type].BATTERY_CAPACITY - self.power
            if self.navigate_to_coordinate(factory_pos) == -1 and pickup_amount > 1:
                action = super().pickup(4,pickup_amount)
                update_action_queue(self,action)

            direction = direction_to(self.pos,host_factory.pos)
            if (self.cargo.ice) > 0: 
                action = super().transfer(direction,0,self.cargo.ice)
                update_action_queue(self,action)
            if self.cargo.ore > 0:
                action = super().transfer(direction,1,self.cargo.ore)
                update_action_queue(self,action)
                
        



        