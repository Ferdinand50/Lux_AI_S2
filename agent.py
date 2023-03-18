from lux.kit import obs_to_game_state, GameState
from lux.config import EnvConfig
from lux.utils import direction_to, my_turn_to_place_factory
from modified.utils import navigate_from_to, update_action_queue
import modified.utils
import numpy as np
import sys
import logging

logging.basicConfig(filename="Logs/agent.log", level=logging.INFO)
# logging.info(f"factory distance: {factory_distances}")

"""
CONSTANT VARIABLES
"""
FACTORY_WATER_LIMIT = 15
FACTORY_ICE_LIMIT = 60
FACTORY_MINIMUM_ICE_WATER_PROD = 12
ROBOT_POWER_LIMIT = 20
LIGHT_ROBOT_CARGO_LIMIT = 100
HEAVY_ROBOT_CARGO_LIMIT = 1000
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


    def check_resource_underneath(self,game_state,unit):
        rubble_map = game_state.board.rubble
        rubble_tile_locations = np.argwhere(rubble_map == 1)
        if np.any(rubble_tile_locations == unit.pos):
            return "rubble"
        ice_map = game_state.board.ice
        ice_tile_locations = np.argwhere(ice_map == 1)
        if np.any(ice_tile_locations == unit.pos):
            return "ice"
        ore_map = game_state.board.ore
        ore_tile_locations = np.argwhere(ore_map == 1)
        if np.any(ore_tile_locations == unit.pos):
            return "ore"
        lichen_map = game_state.board.lichen
        lichen_tile_locations = np.argwhere(lichen_map == 1)
        if np.any(lichen_tile_locations == unit.pos):
            return "lichen"
        logging.ingo("WARNING: check_resource_underneath() returned None!")      
        

    def dig(self,game_state,unit):
        free_cargo = self.calculate_free_cargo(unit)
        removing_factor = 2 if (self.check_resource_underneath(game_state,unit) \
        == ("ice" or "ore" or "rubble")) else 10
        if unit.unit_type == "HEAVY":
            removing_factor *= 10
        t = free_cargo // removing_factor
        self.actions = update_action_queue(self.actions,unit.unit_id,unit.dig(repeat=0,n=t))

       
    def locate_closest_factory(self,unit):
        closest_factory = None
        adjacent_to_factory = False
        if len(self.factory_tiles) > 0:
            factory_distances = np.mean((self.factory_tiles - unit.pos) ** 2, 1)
            closest_factory_tile = self.factory_tiles[np.argmin(factory_distances)]
            closest_factory = self.factory_units[np.argmin(factory_distances)]
            adjacent_to_factory = np.mean((closest_factory_tile - unit.pos) ** 2) == 0 # why == and not < 2???
            return [closest_factory, closest_factory_tile, adjacent_to_factory]
        

    def locate_closest_ice_tile(self,game_state,unit):
        closest_ice_tile = None
        on_ice_tile = False
        ice_map = game_state.board.ice
        ice_tile_locations = np.argwhere(ice_map == 1)
        ice_tile_distances = np.mean((ice_tile_locations - unit.pos) ** 2,1)
        closest_ice_tile = ice_tile_locations[np.argmin(ice_tile_distances)]
        on_ice_tile = np.all(closest_ice_tile == unit.pos)
        return [closest_ice_tile, on_ice_tile]
    

    def locate_closest_ore_tile(self,game_state,unit):
        closest_ore_tile = None
        on_ore_tile = False
        ore_map = game_state.board.ore
        ore_tile_locations = np.argwhere(ore_map == 1)
        ore_tile_distances = np.mean((ore_tile_locations - unit.pos) ** 2,1)
        closest_ore_tile = ore_tile_locations[np.argmin(ore_tile_distances)]
        on_ore_tile = np.all(closest_ore_tile == unit.pos)
        return [closest_ore_tile, on_ore_tile]
    

    def navigate_to_coordinate(self,unit,target_pos):
        direction_orders = navigate_from_to(unit.pos,target_pos)
        if direction_orders[0] != 0:
            action = unit.move(direction_orders[0],repeat=0,n=direction_orders[1])
            self.actions = update_action_queue(self.actions,unit.unit_id,action)
        if direction_orders[2] != 0:
            action = unit.move(direction_orders[2],repeat=0,n=direction_orders[3])
            self.actions = update_action_queue(self.actions,unit.unit_id,action)
        
    

    def navigate_to_factory(self,game_state,unit):
        [closest_factory,closest_factory_tile,adjacent_to_factory] = self.locate_closest_factory(unit)
        if not adjacent_to_factory:
            self.navigate_to_coordinate(unit,closest_factory_tile)
        return adjacent_to_factory


    def navigate_to_ice_tile(self,game_state,unit):
        [closest_ice_tile, on_ice_tile] = self.locate_closest_ice_tile(game_state,unit)
        if not on_ice_tile:
            self.navigate_to_coordinate(unit,closest_ice_tile)
        return on_ice_tile


    def navigate_to_ore_tile(self,game_state,unit):
        [closest_ore_tile, on_ore_tile] = self.locate_closest_ore_tile(game_state,unit)
        if not on_ore_tile:
            self.navigate_to_coordinate(unit,closest_ore_tile)
        return on_ore_tile
        

    def calculate_free_cargo(self,unit):
        free_cargo = LIGHT_ROBOT_CARGO_LIMIT if unit.unit_type == "LIGHT" else HEAVY_ROBOT_CARGO_LIMIT
        free_cargo -= (unit.cargo.ice+unit.cargo.ore+unit.cargo.water+unit.cargo.metal)
        return free_cargo
    
    def transfer_resources(self,unit):
        # always transfer all resources to factory
        pass


    def collect_ice(self,game_state,unit):
        free_cargo = self.calculate_free_cargo(unit)
        if free_cargo > 0:
            # POSSIBLE BUG: is unit.unit_id the same as for unit_id, unit in unit.items()???
            on_ice_tile = self.navigate_to_ice_tile(game_state,unit)
            # if already there, start digging
            if on_ice_tile:
                self.dig(game_state,unit)
        else:
            # go to factory if unit.cargo is full and transfer ice if already there
            adjacent_to_factory = self.navigate_to_factory(game_state,unit)
            # if already there, transfer resources
            if adjacent_to_factory:
                if unit.power >= unit.action_queue_cost(game_state):
                    self.actions = update_action_queue(self.actions,unit.unit_id, \
                    unit.transfer(0,0,unit.cargo.ice,repeat=0))
    

    def collect_ore(self,game_state,unit):
        free_cargo = self.calculate_free_cargo(unit)
        if free_cargo > 0:
            # POSSIBLE BUG: is unit.unit_id the same as for unit_id, unit in unit.items()???
            on_ore_tile = self.navigate_to_ore_tile(game_state,unit)
            # if already there, start digging
            if on_ore_tile:
                self.dig(game_state,unit)
        else:
            adjacent_to_factory = self.navigate_to_factory(game_state,unit)
            if adjacent_to_factory:
                if unit.power >= unit.action_queue_cost(game_state):
                    self.actions = update_action_queue(self.actions,unit.unit_id,\
                    unit.transfer(0,0,unit.cargo.ore)) # WARNING: missing parameter?!
        
        

    def factory_commands(self,unit_id,factory,game_state):    
        # build heavy robot if there are enough resources
        if factory.power >= self.env_cfg.ROBOTS["HEAVY"].POWER_COST and \
        factory.cargo.metal >= self.env_cfg.ROBOTS["HEAVY"].METAL_COST:
            self.actions[unit_id] = factory.build_heavy()
        # prefer to build smaller robots first
        elif factory.power >= self.env_cfg.ROBOTS["LIGHT"].POWER_COST and \
        factory.cargo.metal >= self.env_cfg.ROBOTS["LIGHT"].METAL_COST:
            self.actions[unit_id] = factory.build_light()
        # water surrounding to grow lichen tiles; eventually overrides factory action?
        elif factory.water_cost(game_state) <= factory.cargo.water / 5 - 200:
            self.actions[unit_id] = factory.water()
    
    
    def unit_commands(self,game_state):
        units = game_state.units[self.player]
        # water_unit_sent = [0] * len(self.factory_units) # do not cancel action queue of all units
        # last_factory_id = "xxxxxxxx"

        for unit_id, unit in units.items():

            # track the closest factory
            closest_factory = self.locate_closest_factory(unit)[0]

            # save unit from running out of power
            # if unit.power < ROBOT_POWER_LIMIT:
            #     actions[unit_id] = [unit.recharge(50,repeat=True,n=1)]
            # emergency: closest factory is thirsty! check if factory has enough water/ ice, a robot was not already
            # send to this specfic factory for the case 2 factories run out of water at the same time
            if closest_factory.cargo.water < FACTORY_WATER_LIMIT and closest_factory.cargo.ice < FACTORY_ICE_LIMIT:
                #and (not water_unit_sent and closest_factory.unit_id != last_factory_id):
                    self.collect_ice(game_state,unit)
                    # last_factory_id = closest_factory.unit_id
            else:
                # Since it is less efficient...do we really need to update the action queue? 
                logging.info(f"unit action queue: {unit.action_queue}")
                if len(unit.action_queue) == 0:
                        # send 50% of the roboters ice farming, other 50% ore farming
                    logging.info(f"Unit_id: {int(unit_id[-1]) % 2}")
                    if int(unit_id[-1]) % 2 == 0:
                        self.collect_ore(game_state,unit)
                    else:
                        self.collect_ice(game_state,unit)
            


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
                logging.info("\n")

                potential_spawns = np.array(list(zip(*np.where(obs["board"]["valid_spawns_mask"] == 1))))
                no_rubble_spawns = np.array(list(zip(*np.where(obs["board"]["rubble"] == 0))))
                ice_map = np.array(list(zip(*np.where(obs["board"]["ice"] == 1))))

                #gets postions around the ice_grids
                ice_map_array = game_state.board.ice
                ice_tile_locations = np.argwhere(ice_map_array == 1)
                # arr = ice_tile_locations
                # logging.info(f"arr: {arr}")
                # arr[:,0] += 2
                # logging.info(f"arr_new: {arr}")

                ice_tile_locations_down= np.argwhere(ice_map_array == 1)

                ice_tile_locations[:,0] =+ 2
                ice_tile_locations_up= ice_tile_locations[:,0] - 2
                ice_tile_locations_right= ice_tile_locations[0,:] + 2
                ice_tile_locations_left= ice_tile_locations[0,:] - 2

                logging.info(f"ice_tile_locations: {ice_tile_locations}")
                logging.info(f"ice_tile_locations_down: {ice_tile_locations_down}")


                # ice_tile_locations_up_right = ice_tile_locations_up[0,:] +1
                # ice_tile_locations_up_left = ice_tile_locations_up[0,:] - 1
                # ice_tile_locations_down_right = ice_tile_locations_down[:,0] + 1
                # ice_tile_locations_down_left = ice_tile_locations_down[:,0] - 1
                # ice_tile_locations_right_up = ice_tile_locations_right[:,0] -1
                # ice_tile_locations_right_down = ice_tile_locations_right[:,0] +1
                # ice_tile_locations_left_up = ice_tile_locations_left[:,0] -1
                # ice_tile_locations_left_down = ice_tile_locations_left[:,0] +1

                #logging.info(f"ice_map_surrounding: {ice_map_surrounding}")
                
                # spawn location which are possible and no rubble is placed 
                intersection = np.array([x for x in set(tuple(x) for x in potential_spawns) & set(tuple(x) for x in no_rubble_spawns)])
                # logging.info(f"intersection: {intersection}")

                #if no location with zero rubble avalible choosen random 
                if(len(intersection)==0):
                    logging.info("there is no spawn location withoud 0 rubble")
                    spawn_loc = potential_spawns[np.random.randint(0, len(potential_spawns))]
                else:
                    spawn_loc = intersection[np.random.randint(0, len(intersection))]

                logging.info(f"factory spawn location: {spawn_loc}")
                return dict(spawn=spawn_loc, metal=150, water=150)
            
            return dict()


############# Factory placement functions ##########################################



    def act(self, step: int, obs, remainingOverageTime: int = 60):
        self.factory_tiles, self.factory_units = [], []
        self.actions = dict()
        
        """
        optionally do forward simulation to simulate positions of units, lichen, etc. in the future
        from lux.forward_sim import forward_sim
        forward_obs = forward_sim(obs, self.env_cfg, n=2)
        forward_game_states = [obs_to_game_state(step + i, self.env_cfg, f_obs) for i, f_obs in enumerate(forward_obs)]
        """

        game_state = obs_to_game_state(step, self.env_cfg, obs)
        factories = game_state.factories[self.player]
        game_state.teams[self.player].place_first #what's the purpose of this line? 
        # update commands for all factories and create factory_tiles and factory_units as class attributes
        for unit_id, factory in factories.items():
            self.factory_commands(unit_id,factory,game_state)
            self.factory_tiles += [factory.pos]
            self.factory_units += [factory]
        self.factory_tiles = np.array(self.factory_tiles)

        self.unit_commands(game_state)

        return self.actions    