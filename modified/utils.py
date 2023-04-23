import numpy as np
import numpy.typing as npt
import logging
from typing import Optional
from . import globals

# REMOVE_RUBBLE_AROUND_FACTORY_RADIUS = 3
# MAX_RUBBLE_THRESHHOLD = 25


def dijkstra(graph: npt.NDArray, src_node: tuple, dst_node: Optional[tuple]=None):
    
    def neighbors(node: tuple, visited: npt.NDArray):
        assert 0 <= node[0] < visited.shape[0]
        assert 0 <= node[1] < visited.shape[1]
        
        nodes = []
        bot_node = (node[0]+1, node[1])
        rig_node = (node[0], node[1]+1)
        top_node = (node[0]-1, node[1])
        lef_node = (node[0], node[1]-1)
        
        if bot_node[0] < visited.shape[0] and not visited[bot_node]:
            nodes.append(bot_node)
        if rig_node[1] < visited.shape[1] and not visited[rig_node]:
            nodes.append(rig_node)
        if top_node[0] >= 0 and not visited[top_node]:
            nodes.append(top_node)
        if lef_node[1] >= 0 and not visited[lef_node]:
            nodes.append(lef_node)
        
        return nodes
    
    # Create a distance map saving the distances to a given point
    # Set the distance map's values to Infinity
    distances = np.ones(graph.shape)*np.Infinity
    # Set the distance to the source node as 0
    try:
        distances[src_node]=0
    except Exception as e:        
        logging.info(f"src_node utils.py {src_node}")
        raise e
    
    # Stores the parent's node position (as tuples) that leads to this vertex
    prev_node = np.zeros(graph.shape, dtype=object)
    
    # Stores if the node have been visited
    visited = np.zeros(graph.shape, dtype=int)
    visited[src_node] = False
    
    # Iteration loop
    while not visited.all()==True:
        infinites = np.zeros(visited.shape)
        infinites[visited==True] = np.Infinity
        min_distances=distances+infinites
        min_distance_idx = np.argmin(min_distances)
        row = int(np.floor(min_distance_idx/visited.shape[0]))
        col = int(min_distance_idx%visited.shape[0])
        eval_node = (row, col)
        visited[eval_node] = True
        if dst_node is not None and eval_node==dst_node:
            break
        
        for neighbor_node in neighbors(eval_node, visited):
            alt = distances[eval_node] + graph[neighbor_node]
            # if neighbor_node in globals.unit_positions:
            #     alt = np.Infinity
            if alt < distances[neighbor_node]: # If the distance is smaller than previously recorded for 
                                               # distance(u) then update distance value and set the reference
                distances[neighbor_node] = alt
                prev_node[neighbor_node] = eval_node
        
    return distances, prev_node


def get_path(dist, prev, src_node, dst_node):
    path = []
    # path.append(dst_node)
    prev_node = tuple(dst_node)
    while not (prev_node == src_node):
        path.append(prev_node)
        try:
            prev_node = prev[tuple(prev_node)]
            # logging.warning(prev_node)
            # logging.warning(prev)
            # logging.warning(dst_node)
        except Exception as e:
            # logging.warning("ERROR OCCURED")
            # logging.warning(prev_node)
            # logging.warning(prev)
            # logging.warning(dst_node)
            raise e
    path.append(src_node)
    return path


#helper function for finding a good starting factory postion close to ice
def find_absolute_ice_tile(game_state):
    ice_map = game_state.board.ice
    ice_tile_locations = np.argwhere(ice_map == 1)
    # logging.info(f"ice_map: {ice_map}")
    # logging.info(f"ice_tile_locations: {ice_tile_locations}")


def get_lt_x_rubble_on_tiles_around_factory(pos,env_cfg,unit_pos=None):
    REMOVE_RUBBLE_AROUND_FACTORY_RADIUS = 3
    MAX_RUBBLE_THRESHHOLD = 25
    # get area around factory, increase the radius and threshold if 
    # there is no more rubble left
    def get_area(pos,radius,threshhold):
        min_x = max(0,pos[0]-radius)
        min_y = max(0,pos[1]-radius)
        max_x = min(48,pos[0]+radius+1)
        max_y = min(48,pos[1]+radius+1)

        surrounding_area = np.zeros((48,48))
        surrounding_area[min_x:max_x,min_y:max_y] = \
        globals.game_state.board.rubble[min_x:max_x,min_y:max_y]
        surrounding_rubble_under_x = (0 < surrounding_area) & (surrounding_area < threshhold)
        rubble_tiles_locations = np.argwhere(surrounding_rubble_under_x == True)
        return rubble_tiles_locations

    rubble_tiles_locations = get_area(pos, REMOVE_RUBBLE_AROUND_FACTORY_RADIUS, MAX_RUBBLE_THRESHHOLD)
    # remove the rubble on the way to the ore tile
    ore_tile = locate_closest_resource(pos,"ore",not_occupied=False)[0]
    occupied = np.any(np.all(ore_tile == globals.unit_positions,1))
    if occupied:
        graph = (np.copy(globals.game_state.board.rubble) \
            * env_cfg.ROBOTS["LIGHT"].RUBBLE_MOVEMENT_COST).astype(int)
        graph += env_cfg.ROBOTS["LIGHT"].MOVE_COST
        obstacles = get_enemy_factory_tiles()
        for obstacle in obstacles:
            graph[tuple(obstacle)] = 2047483647

        distances, prev_node = dijkstra(graph,tuple(ore_tile),tuple(pos))
        path = get_path(distances,prev_node,tuple(ore_tile),tuple(pos))
        rubble_ore_path = [p for p in path \
            if globals.game_state.board.rubble[tuple(p)] > 0]
        rubble_tiles_locations = np.append(rubble_tiles_locations,rubble_ore_path).reshape((-1,2))

    while len(rubble_tiles_locations) == 0:
        rubble_tiles_locations = get_area(pos,REMOVE_RUBBLE_AROUND_FACTORY_RADIUS,MAX_RUBBLE_THRESHHOLD)
        REMOVE_RUBBLE_AROUND_FACTORY_RADIUS += 1
        MAX_RUBBLE_THRESHHOLD += 20

    # sort rubble_tiles_locations by its distance to the factory and eventually also the unit
    distances = [absolute_distance(pos,tile) for tile in rubble_tiles_locations]
    if unit_pos is None:
        sort = np.argsort(distances)
    else:
        distances_to_unit = [absolute_distance(unit_pos,tile) for tile in rubble_tiles_locations]
        sort = np.lexsort((distances,distances_to_unit))
    rubble_tiles_locations = rubble_tiles_locations[sort]
    # WARNING: not sure why i have to convert here 
    return rubble_tiles_locations.astype(int)


def absolute_distance(pos_1: npt.NDArray, pos_2: npt.NDArray):
    return int(np.sum(np.absolute(pos_1 - pos_2)))


# @brief: return true if pos_1 is touching pos_2 else false
# @details: tile has to be directly next to the other tile, diagonally does not count
def adjacent_to(pos_1,pos_2):
    ds = np.mean((pos_1 - pos_2)**2)
    return ds < 1


def on_factory(pos_1,pos_2):
    ds = abs(pos_1 - pos_2)
    return np.all(ds < 2)


def adjacent_to_factory(pos_1,pos_2):
    ds = abs(pos_1 - pos_2)
    return False if ds[0] == 2 and ds[1] == 2 else np.all(ds <= 2)


def get_adjacent_factory_tiles(pos,unit_pos):
    deltas = np.array([[2,-1],[2,0],[2,1],[-2,-1],[-2,0],[-2,1], \
        [1,-2],[0,-2],[-1,-2],[1,2],[0,2],[-1,2]])
    tiles = pos + deltas
    tiles = [t for t in tiles if (0 <= t[0] < 48 and 0 <= t[1] < 48)]
    # logging.warning(tiles)
    # logging.info(pos)
    # logging.info(unit_pos)
    if np.any(np.all(unit_pos == tiles,1)):
        return unit_pos
    idx = np.random.randint(len(tiles))
    while np.any(np.all(tiles[idx] == globals.unit_positions,1)):
        idx = np.random.randint(len(tiles))
    return tiles[idx]



def get_action_queue_head(unit):
    action = unit.action_queue[0,0]
    return action


def get_unit_actions(unit):
    if unit.unit_id in globals.actions:
        return globals.actions[unit.unit_id]
    elif len(unit.action_queue) > 0:
        return unit.action_queue
    else:
        return []


def get_units_next_action(unit):
    # case: action was submitted for this unit in this step
    if unit.unit_id in globals.actions: 
        # check if unit has enough power to update the action queue    
        if unit.action_queue_cost() <= unit.power:
            action = globals.actions[unit.unit_id].flatten()[:6]
            # check if the task needs additional power
            if action[0] == 0 and \
                (unit.move_cost(globals.game_state,action[1]) + \
                unit.action_queue_cost()) > unit.power:
                return [-1,0,0,0,0,0]
            elif action[0] == 3 and \
                unit.dig_cost() + unit.action_queue_cost() > unit.power:
                return [-1,0,0,0,0,0]
        else:
            return [-1,0,0,0,0,0]
    # case: no action was submitted, at least not yet
    else:
        # case: unit has a existing action queue (from previous steps)
        if len(unit.action_queue):
            action = unit.action_queue.flatten()[:6]
            if action[0] == 0 and \
                unit.move_cost(globals.game_state,action[1]) > unit.power:
                return [-1,0,0,0,0,0]
            elif action[0] == 3 and \
                unit.dig_cost() > unit.power:
                return [-1,0,0,0,0,0]
        # no existing action queue
        else:
            return [-1,0,0,0,0,0]  
    return action


# helper function for not overwriting existing action queue of a robot
def update_action_queue(unit,action,overwrite=False):
    # logging.info(unit)
    # logging.warning(action)
    if len(unit.action_queue) == 0 or unit.unit_id in globals.actions or overwrite==True: 
        if unit.unit_id not in globals.actions or overwrite==True:
            globals.actions[unit.unit_id] = np.array([action])
        elif not np.any(np.all(globals.actions[unit.unit_id][:,:4] == action[:4],axis=1)):
            # logging.warning("globals.actions = ")
            # logging.warning(globals.actions[unit.unit_id][:,:4])
            globals.actions[unit.unit_id] = \
                np.append(globals.actions[unit.unit_id],action).reshape((-1,6))
    else:
        # add action to globals.actions if action does not appear at any point of unit.action_queue yet 
        if not np.any(np.all(unit.action_queue[:,:4] == action[:4],axis=1)):
            if unit.unit_id in globals.actions:
                globals.actions[unit.unit_id] = \
                    np.append(globals.actions[unit.unit_id],action).reshape((-1,6))
            else:
                globals.actions[unit.unit_id] = np.array([action])


def append_to_action_queue(unit,action):
    if unit.unit_id in globals.actions:
        globals.actions[unit.unit_id] = \
            np.append(globals.actions[unit.unit_id],action).reshape((-1,6))    
    else:
        globals.actions[unit.unit_id] = np.array([action])


def find_most_desperate_unit(helper_unit,units):      
    units_in_need = [unit for unit in units if ((unit.power < \
        (120 if unit.unit_type=="LIGHT" else 500)))
        or absolute_distance(helper_unit.pos,unit.pos) > 15]
    if len(units_in_need):
        next_to_unit = next((unit for unit in units_in_need \
            if adjacent_to(helper_unit.pos,unit.pos)),None)
        if next_to_unit is None:    
            unit = units_in_need[np.argmin(
                [unit.power for unit in units_in_need])]
        else:
            unit =  next_to_unit
        return unit
    else: 
        return None


def direction_array_delta(direction):
    if direction == 1:
        return [0,-1]
    elif direction == 2:
        return [1,0]
    elif direction == 3:
        return [0,1]
    elif direction == 4:
        return [-1,0]
    else:
        return [0,0]


def get_surrounding_tiles(center):
    tiles = []
    for x in range(-1,2):
        for y in range(-1,2):
            delta = np.array([x,y])
            tiles.append(center+delta)
    # del tiles[4]
    return np.array(tiles)


# get closest tile which is also empty, if all 4 adjoining tiles are 
# occupied, return None
def get_empty_adjoining_tile(src,dst):
    direction = direction_to(dst,src)
    pos_next_to = dst + globals.move_deltas[direction]
    if np.all(src == pos_next_to):
        return src
    tiles = np.array(get_adjoining_tiles(dst))
    distances = [absolute_distance(src,x) for x in tiles]
    tiles = tiles[np.argsort(distances)]
    i = 0
    while np.any(np.all(pos_next_to == globals.unit_positions,1)):
        pos_next_to = tiles[i]
        i += 1
        if i == len(tiles):
            return None
    return pos_next_to        


def get_adjoining_tiles(center):
    tiles = center + globals.move_deltas[1:]
    opponent_tiles = get_enemy_factory_tiles()    
    tiles = [tile for tile in tiles if np.all((0 <= tile) & (tile < 48)) 
    and not np.any(np.all(tile == opponent_tiles,1))]
    # logging.warning(f"adjoining tiles: {tiles}")    
    return tiles


def get_enemy_factory_tiles():
    factories = globals.game_state.factories[globals.opp_player]
    tiles = np.array([get_surrounding_tiles(f.pos) for f in factories.values()]).reshape((-1,2))
    return tiles


def defeat_unit(unit,opponent,buffer=False):
    if buffer == True:
        cushion = 10 if unit.unit_type == "LIGHT" else 30
    else:
        cushion = 0
    if unit.unit_type == "HEAVY":
        if opponent.unit_type == "HEAVY":
            if unit.power - cushion > opponent.power:
                return True
            else:
                return False
        else:
            return True
    else:
        if opponent.unit_type == "HEAVY":
            return False
        else:
            if unit.power - cushion > opponent.power:
                return True
            else:
                return False


# locate closest factory tile which is also empty
def locate_closest_factory_tile(pos,reference_pos=None):
    if reference_pos is None:
        reference_pos = pos
    closest_factory_tile = locate_closest_factory(pos)[1]
    tiles = get_surrounding_tiles(closest_factory_tile)
    # FUTURE: delete center from tiles?
    distances = np.sum(abs(tiles - reference_pos), 1)
    closest_tiles = tiles[np.argsort(distances)]
    if np.all(reference_pos == closest_tiles[0]):
        return reference_pos
    i = 0
    while np.any(np.all(closest_tiles[i] == globals.unit_positions,1)):
        i += 1
        if i == 8:
            i = 0
            break
    return closest_tiles[i]


def locate_closest_factory(pos):
    closest_factory = None
    closest_factory_center = None
    adjacent_to_factory = False
    if len(globals.factory_tiles) > 0:
        factory_distances = np.mean((globals.factory_tiles - pos) ** 2, 1)
        closest_factory_center = globals.factory_tiles[np.argmin(factory_distances)]
        key = [f.unit_id for f in globals.factory_units.values() \
            if np.all(f.pos == closest_factory_center)][0]                       
        closest_factory = globals.factory_units[key]
        adjacent_to_factory = np.mean((closest_factory_center - pos) ** 2) == 0 # why == and not < 2???
    return [closest_factory, closest_factory_center, adjacent_to_factory]


def locate_closest_resource(pos,resource,reference_pos=None,not_occupied=True):
    if reference_pos is None:
        reference_pos = pos        
    resource_map = globals.game_state.board.ice if resource == "ice" else \
        globals.game_state.board.ore
    resource_tile_locations = np.argwhere(resource_map == 1)
    resource_tile_distances = np.mean((resource_tile_locations - reference_pos) ** 2,1)
    closest_tiles = resource_tile_locations[np.argsort(resource_tile_distances)]
    i = 0
    if np.all(pos == closest_tiles[0]):
        on_resource_tile = True
    else:      
        if not_occupied:
            unit_positions = np.array([unit.pos for unit in globals.units.values() if unit.unit_type=="HEAVY"])
            while len(globals.unit_positions) > 0 and \
                np.any(np.all(closest_tiles[i] == unit_positions,1)):
                i += 1
                if i == len(closest_tiles):
                    i = 0
                    break
        on_resource_tile = False
    return [closest_tiles[i], on_resource_tile]


def simple_locate_closest_resource_(pos,resource_map):         
    resource_tile_locations = np.argwhere(resource_map == 1)
    resource_tile_distances = np.sum(np.absolute(resource_tile_locations - pos),1)
    closest_tile = resource_tile_locations[np.argmin(resource_tile_distances)]
    return closest_tile
        

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


def get_sorted_distances_to(units,target):
    if len(units) > 0:
        distances = np.sum((units.pos - target),1)
        
    else:
        return None
    


# direction (0 = center, 1 = up, 2 = right, 3 = down, 4 = left)
def direction_to(src, target):
    ds = target - src
    dx = ds[0]
    dy = ds[1]
    if dx == 0 and dy == 0:
        return 0
    if abs(dx) > abs(dy):
        if dx > 0:
            return 2 
        else:
            return 4
    else:
        if dy > 0:
            return 3
        else:
            return 1
