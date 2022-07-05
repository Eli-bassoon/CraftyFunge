# Common variarbles for the CraftyFunge esoteric programming language
# Copyright 2022 Eli Fox

import sys, os
import math, enum
import csv

# Stack and number limits
MAX_NUMBER_HEIGHT = 31
MAX_VAL = 2**MAX_NUMBER_HEIGHT - 1
MIN_VAL = -2**MAX_NUMBER_HEIGHT
MAX_DIGITS = int(math.log10(MAX_VAL)) + 1
MAX_STACK_SIZE = 2**7 - 1
MAX_VARS_SIZE = 2**7 - 1

# Movement directions
DIRS = [
    'north',
    'south',
    'east',
    'west',
    'up',
    'down',
]
DIRS_INV = [
    'south',
    'north',
    'west',
    'east',
    'down',
    'up',
]
DIRS4 = DIRS[:4]

DIRS_DEL = {
    'north' : (0, 0, -1),
    'south' : (0, 0, +1),
    'east'  : (+1, 0, 0),
    'west'  : (-1, 0, 0),
    'up'    : (0, +1, 0),
    'down'  : (0, -1, 0),
}

AXIS_NAMES = ('x', 'y', 'z')

# Colors
COLORS = [
    'red',
    'orange',
    'yellow',
    'lime',
    'green',
    'light_blue',
    'cyan',
    'blue',
    'purple',
]

# Instructions
ADD = 'iron_block'
SUB = 'gold_block'
MULT = 'diamond_block'
DIV = 'emerald_block'
MOD = 'lapis_block'
EXP = 'netherite_block'
NEG = 'coal_block'

NOT = 'obsidian'

GREATER = 'mossy_stone_bricks'
LESS = 'cracked_stone_bricks'

DIR = 'piston'
RANDOM_DIR = 'magenta_glazed_terracotta'
SKIP = 'sea_lantern'
SKIP_COND = 'redstone_lamp'

TUNNEL = 'deepslate'
IN_NUM_LITERAL = 'glass'
IN_STR_LITERAL = 'tinted_glass'

IF = 'observer'

DUP = 'crafting_table'
POP = 'magma_block'
CLEAR = 'tnt'
SWAP = 'pumpkin'
ROTATE = 'melon'
PUSH_LEN = 'ancient_debris'

OUT_NUM = 'dispenser'
OUT_ASCII = 'dropper'
OUT_NEWLINE = 'bookshelf'
RAISE_ERROR = 'note_block'

IN_NUM = 'chest'
IN_ASCII = 'ender_chest'

GET_BLOCK = 'slime_block'
SET_BLOCK = 'honey_block'
PUSH_NEXT_BLOCK = 'jukebox'

GET_VAR = 'red_nether_bricks'
SET_VAR = 'nether_bricks'

PUSH_POS = 'dark_prismarine'
GOTO = 'prismarine'

START = 'command_block'
STOP = 'bedrock'

NUM_TYPES = [
# Exponent, name
    (0, 'concrete'), 
    (1, 'terracotta'), 
    (2, 'wool'), 
    (3, 'stained_glass'), 
    (6, 'shulker_box')
]

BLOCKS_FOR_VALUES = [
    ADD, SUB, MULT, DIV, MOD, EXP, NEG, 
    NOT,
    GREATER, LESS,
    DIR, RANDOM_DIR, SKIP, SKIP_COND,
    TUNNEL, IN_NUM_LITERAL, #IN_STR_LITERAL,
    IF,
    DUP, POP, CLEAR, SWAP, ROTATE, PUSH_LEN,
    OUT_NUM, OUT_ASCII, OUT_NEWLINE, RAISE_ERROR,
    IN_NUM, IN_ASCII,
    GET_BLOCK, SET_BLOCK, PUSH_NEXT_BLOCK,
    GET_VAR, SET_VAR,
    PUSH_POS, GOTO,
    STOP, # START,
]

# Execution modes
class Modes(enum.IntEnum):
    STOPPED = 0
    DEFAULT = enum.auto()
    TUNNEL = enum.auto()
    IN_NUM_LITERAL = enum.auto()
    IN_STR_LITERAL = enum.auto()
    PAUSED = enum.auto()

MODE_COLORS = {
    Modes.STOPPED           : 'red',
    Modes.DEFAULT           : 'green',
    Modes.TUNNEL            : 'dark_gray',
    Modes.IN_NUM_LITERAL    : 'blue',
    Modes.IN_STR_LITERAL    : 'light_purple',
    Modes.PAUSED            : 'yellow',
}

MODE_NAMES = {
    Modes.STOPPED           : 'stopped',
    Modes.DEFAULT           : 'default',
    Modes.TUNNEL            : 'tunnel',
    Modes.IN_NUM_LITERAL    : 'in_num_literal',
    Modes.IN_STR_LITERAL    : 'in_str_literal',
    Modes.PAUSED            : 'paused',
}

BLOCKS_WITH_EXTRA_DATA = ['piston', 'observer']
EXTRA_DATA_ORDER = ['facing']


# Gets a path to a resource depending on if it's bundled or not
def resourcePath(relPath, config=False):
    # If we are bundled and getting config data, we want a different location
    if  getattr(sys, 'frozen', False) and config:
        base_path = os.path.dirname(sys.executable)
    # Otherwise:
    else:
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relPath)
CONFIG_PATH = resourcePath('world.cfg', config=True)


# Reads the world name from world.cfg
def readConfig():
    # Read config
    with open(CONFIG_PATH, 'r') as f:
        worldPath = f.read().strip()
        worldPath = os.path.expandvars(worldPath)
    
    return worldPath


def invertDict(d):
    return {v: k for k, v in d.items()}


# Gets blocks corresponding to pushing numbers
def findNumColors():
    colorNumbers = dict()
    for exp, blockType in NUM_TYPES:
        if exp == 0:
            colorNumbers['white_concrete'] = 0
            
        for i, color in enumerate(COLORS):
            num = (i+1) * 10**exp
            block = color + '_' + blockType
            colorNumbers[block] = num
            
    return colorNumbers
BLOCK_TO_PUSHNUM = findNumColors()


# Generates consistent paired tuples from extra data
def getExtraDataTup(block, extraData):
    extraDataPairs = []
    for key in EXTRA_DATA_ORDER:
        if key in extraData:
            extraDataPairs.append((key, extraData[key]))
            
    return (block, tuple(extraDataPairs))


# Read block values from csv
def readBlockValues():
    valueToBlock = dict()
    
    with open(resourcePath('data/block_to_value.csv'), 'r', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            # Value to block
            value = row[0]
            block = row[1]
            if block not in BLOCKS_WITH_EXTRA_DATA:
                valueToBlock[int(value)] = block
            
            # Extra data (if applicable)
            else:
                row = row[2:]
                # Get value/extra data conversions
                extraData = dict()
                # Get values to extra data
                for i in range(len(row)//2):
                    extraData[row[i]] = row[i+1]
                
                valueToBlock[int(value)] = getExtraDataTup(block, extraData)
    
    blockToValue = invertDict(valueToBlock)
    
    return valueToBlock, blockToValue
VALUE_TO_BLOCK, BLOCK_TO_VALUE = readBlockValues()


# Get a block's name from extra data
def getNameFromValue(value):
    v = VALUE_TO_BLOCK[value]
    if isinstance(v, str):
        return v
    # Extra data means the name is the first element
    else:
        return v[0]


# Used for runAll in "function generator.py"
def getBadFuncs():
    import types
    return [f for f in globals().values() if type(f) == types.FunctionType]