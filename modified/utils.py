import numpy as np
import logging



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
    logging.info(f"ice_map: {ice_map}")
    logging.info(f"ice_tile_locations: {ice_tile_locations}")
