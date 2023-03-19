import numpy as np
import logging
from . import globals

# direction_orders is a array of 4 numbers
# first digit indicates x - direction (2 or 4) (see above)
# second digit indicates for how long 
# third digit indicates y - direction (1 or 3)
# forth digit indicates for how long
# 0 always stands for do not move in this direction
def navigate_from_to(src,target):
    direction_orders = []
    ds = target - src
    dx = ds[0]
    dy = ds[1]
    if dx == 0 and dy == 0:
        return [0,0,0,0]
    
    if dx == 0:
        direction_orders = [0,0]
    elif dx > 0:
        direction_orders = [2,dx]
    else:
        direction_orders = [4,abs(dx)]


    if dy == 0:
        direction_orders += [0,0]
    elif dy > 0:
        direction_orders += [3,dy]
    else:
        direction_orders += [1,abs(dy)]
    
    return direction_orders


#helper function for finding a good starting factory postion close to ice
def find_absolute_ice_tile(game_state):
    ice_map = game_state.board.ice
    ice_tile_locations = np.argwhere(ice_map == 1)
    # logging.info(f"ice_map: {ice_map}")
    # logging.info(f"ice_tile_locations: {ice_tile_locations}")


# helper function for not overwriting existing action queue of a robot
def update_action_queue(key,action):
    if key in globals.actions.keys():
        globals.actions[key].append(action)
    else:
        globals.actions[key] = [action]


# @brief: return true if pos_1 is touching pos_2 else false
# @details: tile has to be directly next to the other tile, diagonally does not count
def adjacent_to(pos_1,pos_2):
    ds = np.mean((pos_1 - pos_2)**2)
    return ds < 1


def get_action_queue_head(unit):
    action = unit.action_queue[0,0]
    return action


def get_unit_live_actions(unit_id):
    action = globals.actions[unit_id][0][0]
    return action


def locate_closest_factory(pos):
        closest_factory = None
        closest_factory_tile = None
        adjacent_to_factory = False
        if len(globals.factory_tiles) > 0:
            factory_distances = np.mean((globals.factory_tiles - pos) ** 2, 1)
            closest_factory_tile = globals.factory_tiles[np.argmin(factory_distances)]
            closest_factory = globals.  factory_units[np.argmin(factory_distances)]
            adjacent_to_factory = np.mean((closest_factory_tile - pos) ** 2) == 0 # why == and not < 2???
        return [closest_factory, closest_factory_tile, adjacent_to_factory]

def locate_closest_resource(pos,resource):
    closest_resource_tile = None
    on_resource_tile = False
    resource_map = globals.game_state.board.ice if resource == "ice" else \
        globals.game_state.board.ore
    resource_tile_locations = np.argwhere(resource_map == 1)
    resource_tile_distances = np.mean((resource_tile_locations - pos) ** 2,1)
    closest_resource_tile = resource_tile_locations[np.argmin(resource_tile_distances)]
    on_resource_tile = np.all(closest_resource_tile == pos)
    return [closest_resource_tile, on_resource_tile]
        

def locate_closest_ice_tile(game_state,pos):
    closest_ice_tile = None
    on_ice_tile = False
    ice_map = game_state.board.ice
    ice_tile_locations = np.argwhere(ice_map == 1)
    ice_tile_distances = np.mean((ice_tile_locations - pos) ** 2,1)
    closest_ice_tile = ice_tile_locations[np.argmin(ice_tile_distances)]
    on_ice_tile = np.all(closest_ice_tile == pos)
    return [closest_ice_tile, on_ice_tile]


def locate_closest_ore_tile(game_state,pos):
    closest_ore_tile = None
    on_ore_tile = False
    ore_map = game_state.board.ore
    ore_tile_locations = np.argwhere(ore_map == 1)
    ore_tile_distances = np.mean((ore_tile_locations - pos) ** 2,1)
    closest_ore_tile = ore_tile_locations[np.argmin(ore_tile_distances)]
    on_ore_tile = np.all(closest_ore_tile == pos)
    return [closest_ore_tile, on_ore_tile]


def check_resource_underneath(self,game_state,pos):
        rubble_map = game_state.board.rubble
        rubble_tile_locations = np.argwhere(rubble_map == 1)
        if np.any(rubble_tile_locations == pos):
            return "rubble"
        ice_map = game_state.board.ice
        ice_tile_locations = np.argwhere(ice_map == 1)
        if np.any(ice_tile_locations == pos):
            return "ice"
        ore_map = game_state.board.ore
        ore_tile_locations = np.argwhere(ore_map == 1)
        if np.any(ore_tile_locations == pos):
            return "ore"
        lichen_map = game_state.board.lichen
        lichen_tile_locations = np.argwhere(lichen_map == 1)
        if np.any(lichen_tile_locations == pos):
            return "lichen"
        logging.warning("WARNING: check_resource_underneath() returned None!")      