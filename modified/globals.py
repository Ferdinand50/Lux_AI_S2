import numpy as np

def init(gs,p):
    global actions
    global factory_tiles
    global factory_units
    # variable keeps track of where units, will be next step, 
    # unit.pos has the current position
    global unit_positions
    global game_state
    global player
    global opp_player

    game_state = gs
    actions = dict()
    factory_tiles = []
    factory_units = dict()
    unit_positions = []
    player = p
    opp_player = "player_1" if player == "player_0" else "player_0"


def init_once():
    global unit_tasks
    global move_deltas

    unit_tasks = dict()
    move_deltas = np.array([
        [0, 0],
        [0, -1],
        [1, 0],
        [0, 1],
        [-1, 0]
    ])

