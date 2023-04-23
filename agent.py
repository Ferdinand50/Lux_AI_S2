from lux.kit import obs_to_game_state, GameState
from lux.config import EnvConfig
from lux.utils import direction_to, my_turn_to_place_factory
from modified.utils import update_action_queue, locate_closest_factory, get_units_next_action, \
    direction_array_delta, get_unit_actions, get_adjoining_tiles, defeat_unit, \
    absolute_distance, get_enemy_factory_tiles, simple_locate_closest_resource_
from modified.factory import FactoryM
from modified.robot import RobotM
from modified import globals
import numpy as np
import sys
import logging

logging.basicConfig(filename="Logs/agent.log", level=logging.INFO)


"""
CONSTANT VARIABLES
"""
FACTORY_WATER_LIMIT = 15
FACTORY_ICE_LIMIT = 60
FACTORY_MINIMUM_ICE_WATER_PROD = 12
ROBOT_POWER_LIMIT = 20
# minimum amount of resources for robot to directly go to endangered factory instead of farm more resources 
# when factory runs out of water
LIGHT_ROBOT_WATER_ICE_THRESHOLD = 20 
HEAVY_ROBOT_WATER_ICE_THRESHOLD = 100

# factory parameters
# ice to water 100/turn 4:1
# ore to metal 50/turn 5:1



class Agent():
    def __init__(self, player: str, env_cfg: EnvConfig) -> None:
        self.player = player
        self.opp_player = "player_1" if self.player == "player_0" else "player_0"
        np.random.seed(0)
        self.env_cfg: EnvConfig = env_cfg
            


############# Factory placement functions ##########################################

    #returns middle point of fatory position
    def factory_placement(self, step: int, obs, remainingOverageTime: int = 60):
        if step == 0:
            # bid 0 to not waste resources bidding and declare as the default faction
            return dict(faction="AlphaStrike", bid=0)
        else:
            game_state = obs_to_game_state(step, self.env_cfg, obs)
            # factory placement period

            # how much water and metal you have in your starting pool to give to new factories
            water_left = game_state.teams[self.player].water
            metal_left = game_state.teams[self.player].metal

            # how many factories you have left to place
            factories_to_place = game_state.teams[self.player].factories_to_place
            # whether it is your turn to place a factory
            my_turn_to_place = my_turn_to_place_factory(game_state.teams[self.player].place_first, step)
            if factories_to_place > 0 and my_turn_to_place:
                # we will spawn our factory in a random location with 150 metal and water if it is our turn to place

                potential_spawns = np.array(list(zip(*np.where(obs["board"]["valid_spawns_mask"] == 1))))
                no_rubble_spawns = np.array(list(zip(*np.where(obs["board"]["rubble"] == 0))))

                #gets postions around the ice_grids
                #init ice tile maps
                ice_map_array = game_state.board.ice
                ice_tile_locations_right = np.argwhere(ice_map_array == 1)
                ice_tile_locations_left = np.argwhere(ice_map_array == 1)
                ice_tile_locations_up= np.argwhere(ice_map_array == 1)
                ice_tile_locations_down= np.argwhere(ice_map_array == 1)

                # TODO: add more directions F: factory middle point, I: ice tile
                #  **F**
                #  *****
                #  F*I*F
                #  *****
                #  **F**

                ice_tile_locations_right[:, 0] = ice_tile_locations_right[:, 0] + 2
                ice_tile_locations_left[:, 0]= ice_tile_locations_left[:,0] - 2
                ice_tile_locations_up[:, 1] = ice_tile_locations_up[:, 1] - 2
                ice_tile_locations_down[:, 1]= ice_tile_locations_down[:, 1] + 2    
                # merge arrays
                ice_tile_spawns_1 = np.concatenate((ice_tile_locations_right, ice_tile_locations_left), axis=0)
                ice_tile_spawns_2 = np.concatenate((ice_tile_locations_up, ice_tile_locations_down), axis=0)
                ice_tile_spawns = np.concatenate((ice_tile_spawns_1, ice_tile_spawns_2), axis=0)

                # 2. spawn location which are possible close to ice
                best_ice_locations = np.array([x for x in set(tuple(x) for x in potential_spawns) & set(tuple(x) for x in ice_tile_spawns)])
            
                if(len(best_ice_locations)==0):
                    # logging.warning("[WARNING] there is no spawn location close to ice. Therefore random factory location")
                    spawn_loc = potential_spawns[np.random.randint(0, len(potential_spawns))]
                else:
                    ore_map_array = game_state.board.ore
                    distance_to_ore = [absolute_distance(x,simple_locate_closest_resource_\
                        (x,ore_map_array)) for x in best_ice_locations]
                    spawn_loc = best_ice_locations[np.argmin(distance_to_ore)]

                # # 1. spawn location which are possible close to ice and no rubble is placed 
                # best_ice_no_rubble_locations = np.array([x for x in set(tuple(x) for x in best_ice_locations) & set(tuple(x) for x in no_rubble_spawns)])
                
                # #if no location with zero rubble avalible choosen random 
                # if(len(best_ice_no_rubble_locations)==0):
                #     # logging.info("there is no spawn location close to ice and without 0 rubble")
                # else:
                #     # logging.info("Best factory location is choosen")
                #     spawn_loc = best_ice_no_rubble_locations[np.random.randint(0, len(best_ice_no_rubble_locations))]

                # logging.info(f"factory spawn location: {spawn_loc}")
                return dict(spawn=spawn_loc, metal=150, water=150)
            
            return dict()


############# Factory placement functions ##########################################

    def avoid_unit_collision(self, units,tmp):
        board = np.zeros((48,48))
        # ==========================================================================
        # ally unit collision avoidance
        # ==========================================================================
        for unit in units.values():
            action = get_units_next_action(unit)
            if action[0] != 0 or (action[0] == 0 and action[1] == 0):
                board[tuple(unit.pos)] = 1

        for unit in units.values():            
            action = get_units_next_action(unit)        
            if action[0] == 0 and action[1] != 0:
                dst_tile = unit.pos + globals.move_deltas[action[1]]
                if board[tuple(dst_tile)] == 1:                                        
                    globals.actions[unit.unit_id] = np.array([unit.move(0)])
                else:
                    board[tuple(dst_tile)] = 1       
        # ==========================================================================
        # opponent unit collision avoidance
        # ==========================================================================
        opp_units = globals.game_state.units[self.opp_player].values()             
        for unit in units.values():
            close_opp_units = [opp_u for opp_u in opp_units if absolute_distance(unit.pos,opp_u.pos) <= 2]
            if len(close_opp_units) == 0:
                continue            

            for opp_u in close_opp_units:
                # decide if mark tiles as dangerous or attack
                opp_factory_tiles = get_enemy_factory_tiles()                
                factory_there = np.any(np.all(opp_factory_tiles == opp_u.pos,1))
                # logging.info(f"agentpy factory_there: {factory_there} opp_u.pos  {opp_u.pos}")
                try:
                    if defeat_unit(unit,opp_u,buffer=True) and not factory_there:
                        unit.navigate_to_coordinate(opp_u.pos)
                    
                        break
                    else: 
                        # dangerous_tiles = get_adjoining_tiles(opp_u.pos)
                        # dangerous_tiles.append(opp_u.pos)                    
                        # for tile in dangerous_tiles:
                        #     board[tuple(tile)] = 2
                        factory_pos = locate_closest_factory(unit.pos)[1]
                        factory_direction = direction_to(unit.pos,factory_pos)
                        dangerous_direction = direction_to(unit.pos,opp_u.pos)
                        if factory_direction != dangerous_direction:
                            unit.navigate_to_coordinate(factory_pos)
                        else: 
                            opposite_direction = direction_to(unit.pos,opp_u.pos)
                            target_pos = unit.pos + globals.move_deltas[opposite_direction]
                            factory_there = np.any(np.all(target_pos == opp_factory_tiles,1))
                            if not factory_there:
                                action = unit.move(opposite_direction,n=3)
                                globals.actions[unit.unit_id] = np.array([action])
                        break
                except KeyError as e:
                    logging.info("Key Error")
                    logging.warning(tmp)
                    logging.info(globals.unit_tasks)
                    logging.info(units)
                    raise e
            # if board[tuple(unit.pos)] == 2:
            #     unit.recalculate_task()

            

            
            

            


    def remove_outdated_unit_tasks(self,existing_units):
        del_units = []
        for unit_id in globals.unit_tasks.keys():
            # delete unit from unit_tasks if it does not exist anymore
            if not unit_id in existing_units:
                del_units.append(unit_id)            

        for unit_id in del_units:
            del globals.unit_tasks[unit_id]


    def validate_action_queue(self):
        for unit_id, queue in globals.actions.items():
            # only check the length of robots action queue
            if unit_id[0] != 'f':
                globals.actions[unit_id] = queue[:20]


    def act(self, step: int, obs, remainingOverageTime: int = 60):
        # if self.player == "player_0":
        # if step == 300:
        #     raise Exception
        
        game_state = obs_to_game_state(step, self.env_cfg, obs)
        globals.init(game_state,self.player)
        logging.info(f"STEP: {step}")
        tmp = globals.unit_tasks.copy()

        
        """
        optionally do forward simulation to simulate positions of units, lichen, etc. in the future
        from lux.forward_sim import forward_sim
        forward_obs = forward_sim(obs, self.env_cfg, n=2)
        forward_game_states = [obs_to_game_state(step + i, self.env_cfg, f_obs) for i, f_obs in enumerate(forward_obs)]
        """

        factories = game_state.factories[self.player]
        game_state.teams[self.player].place_first #what's the purpose of this line? 
        units = game_state.units[self.player]
        globals.units = units
        self.remove_outdated_unit_tasks(units)

        i = 0
        for unit_id, factory in factories.items():
            # add factory tiles and units to a global variable for better handling
            factory.__class__ = FactoryM
            factory.robots = []
            globals.factory_tiles += [factory.pos]
            globals.factory_units[unit_id] = factory
        globals.factory_tiles = np.array(globals.factory_tiles)

        # get current unit positions and assign them to a factory if they haven't already been assigned
        # (robots forget their host_factory each step, so )
        for unit_id, unit in units.items():            
            unit.__class__ = RobotM
            globals.unit_positions += [unit.pos]
            # either if or else: in both cases unit has no current host factory
            if not unit_id in globals.unit_tasks:
                # case: roboter has not been assigned to a factory yet
                closest_factory = locate_closest_factory(unit.pos)[0]
                globals.unit_tasks[unit_id] = dict()
                globals.unit_tasks[unit_id]['host_factory'] = closest_factory.unit_id
                globals.unit_tasks[unit_id]['task'] = 'None'
            else:
                # case: assigned factory does not exist anymore
                # try:
                host_factory_id = globals.unit_tasks[unit_id]['host_factory']
                # except Exception as e:
                #     logging.info(f"agent.py unit_tasks: {globals.unit_tasks[unit_id]}")
                #     raise e
                if not host_factory_id in factories:
                    closest_factory = locate_closest_factory(unit.pos)[0]
                    globals.unit_tasks[unit_id]['host_factory'] = closest_factory.unit_id
                    globals.unit_tasks[unit_id]['task'] = 'None'     
                    #reset unit task               
                    globals.actions[unit.unit_id] = np.array([unit.move(0)])
            
            host_factory_id = globals.unit_tasks[unit_id]['host_factory']
            factories[host_factory_id].robots.append(unit)
            unit.host_factory = host_factory_id
            unit.task = globals.unit_tasks[unit_id]['task']            

        globals.unit_positions = np.array(globals.unit_positions)

        # ================================================================================================
        # create existing factories and cast them to the derives class FactoryM
        #
        # additional tasks: 
        #   - build units
        #   - water surrounding
        # ================================================================================================
        for unit_id, factory in factories.items():
            # STRATEGY: decide what factory should do depending on the past game steps            
            factory.water(obs,step)
            factory.assign_tasks()            
            factory.execute_tasks()
            factory.improve_task_execution()
        

        self.avoid_unit_collision(units,tmp)
        self.validate_action_queue()
        
        return globals.actions    
        # else:
        #     return {}

# ================================================================================================
# END: master(agent) logic
# ================================================================================================
