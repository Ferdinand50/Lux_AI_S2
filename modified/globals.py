def init(gs):
    global actions
    global factory_tiles
    global factory_units
    global game_state

    game_state = gs
    actions = dict()
    factory_tiles = []
    factory_units = []