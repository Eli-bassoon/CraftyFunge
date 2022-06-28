# Generates Minecraft functions for the in-game interpreter
# Copyright 2022 Eli Fox

import math
import os, sys

from common import *

FUNCTION_PATH = 'datapacks/craftyfunge/data/craftyfunge/functions/'
WORLD_PATH = readConfig()
START_PATH = os.path.join(WORLD_PATH, FUNCTION_PATH)

# Make sure the path exists before trying to write to it
if not os.path.exists(START_PATH):
    raise OSError('Function folder does not exist. Change world.cfg to match the path to your world.')


BLOCKS_TO_FN_NAMES = [
    (STOP, 'stop'),
    (OUT_NUM, 'output_number'),
    (OUT_ASCII, 'output_ascii'),
    (OUT_NEWLINE, 'output_newline'),
    (RAISE_ERROR, 'raise_error'),
    (EXP, 'arithmetic/exp'),
    (NEG, 'arithmetic/neg'),
    (DUP, 'duplicate'),
    (POP, 'pop_stack1'),
    (CLEAR, 'clear_stack'),
    (SWAP, 'swap'),
    (ROTATE, 'rotate'),
    (PUSH_LEN, 'push_stack_length'),
    (IF, 'conditional'),
    (NOT, 'not'),
    (DIR, 'change_direction'),
    (RANDOM_DIR, 'random_direction'),
    (SKIP, 'move'),
    (SKIP_COND, 'conditional_skip'),
    (TUNNEL, 'toggles/tunnel/tunnel_toggle'),
    (IN_NUM_LITERAL, 'toggles/in_num_literal/in_num_literal_toggle'),
    (IN_STR_LITERAL, 'toggles/in_str_literal/in_str_literal_toggle'),
    (GET_BLOCK, 'get_block'),
    (SET_BLOCK, 'set_block'),
    (GET_VAR, 'get_var'),
    (SET_VAR, 'set_var'),
    (PUSH_POS, 'push_pos'),
    (GOTO, 'goto'),
    (IN_NUM, 'input/input_number'),
    (IN_ASCII, 'input/input_ascii'),
    (PUSH_NEXT_BLOCK, 'push_next_block'), # This must be at the end, so nothing overrides it
]

# Selectors
getSelector = lambda mob, tag: f'type=minecraft:{mob},tag={tag},limit=1'
FUNGIE = getSelector('magma_cube', 'Fungie') # The IP
STACKER = getSelector('armor_stand', 'Stacker')
SETTER = getSelector('armor_stand', 'VarSetter')
MARKER = getSelector('marker', 'BlockMarker')

# Scoreboard limits
STACKS = 4
TEMPS = 4

# Hardcoded positions
# Stack/Stacker
STACKER_POS = (-39, 1, 10)
STACKER_Z = STACKER_POS[2]
STACK_POS = (STACKER_POS[0], STACKER_POS[1]-1, STACKER_POS[2])
STACK_Z = STACK_POS[2]

# Setter/Vars
SETTER_POS = (STACKER_POS[0], 37, STACKER_POS[2])
SETTER_Z = SETTER_POS[2]
VARS_POS = (SETTER_POS[0], SETTER_POS[1]-1, SETTER_POS[2])
VARS_Z = VARS_POS[2]

# Clock start
CLOCK_START_POS = (-45, 0, 23)


def writeFile(filename, lines, mode='w'):
    # Appending needs an extra newline before
    if mode == 'a':
        lines[0] = '\n' + lines[0]
        
    with open(filename, mode) as f:
        s = '\n'.join(lines)
        f.write(s)


# Teleport a scoreboard distance using binary search. Adds to the lines, to be written later.
def binaryTeleport(scoreboard, maxDistance):
    lines = []
    
    player, objective = scoreboard
    for exp in range(int(math.log(maxDistance, 2)), -1, -1):
        n = 2**exp
        lines.append(f'execute at @s if score {player} {objective} matches {n}.. run tp @s ~ ~ ~-{n}')
        lines.append(f'execute if score {player} {objective} matches {n}.. run scoreboard players remove {player} {objective} {n}')

    return lines


# Encodes a scoreboard value to a binary block representation
def binaryEncode(negScoreboard, fromScoreboard, maxHeight):
    lines = []
    
    negPl, negOb = negScoreboard
    inputPl, inputOb = fromScoreboard
    
    # Special case of MIN_VAL is represented as negative zero
    lines.append(f'execute at @s if score {inputPl} {inputOb} matches -2147483648 run setblock ~ ~-1 ~ minecraft:obsidian')
    lines.append(f'execute if score {inputPl} {inputOb} matches -2147483648 run scoreboard players set {inputPl} {inputOb} 0')
    
    # Negate if necessary
    lines.append(f'scoreboard players set {negPl} {negOb} -1')
    lines.append(f'execute at @s if score {inputPl} {inputOb} matches ..-1 run setblock ~ ~-1 ~ minecraft:obsidian')
    lines.append(f'execute if score {inputPl} {inputOb} matches ..-1 run scoreboard players operation {inputPl} {inputOb} *= {negPl} {negOb}')
    lines.append(f'scoreboard players set {negPl} {negOb} 0')
    
    # Set number of blocks
    for exp in range(maxHeight, 0, -1):
        exp -= 1
        n = 2**exp
        lines.append(f'execute at @s if score {inputPl} {inputOb} matches {n}.. run setblock ~ ~{exp} ~ minecraft:iron_block')
        lines.append(f'execute at @s if score {inputPl} {inputOb} matches {n}.. run scoreboard players remove {inputPl} {inputOb} {n}')
    
    return lines


# Decodes blocks into a scoreboard value
def binaryDecode(negScoreboard, toScoreboard, maxHeight):
    lines = []
    
    negPl, negOb = negScoreboard
    outputPl, outputOb = toScoreboard
    
    # Add to scoreboard
    for exp in range(maxHeight):
        lines.append(f'execute at @s if block ~ ~{exp} ~ minecraft:iron_block run scoreboard players add {outputPl} {outputOb} {2**exp}')
    
    # Negate if necessary
    lines.append(f'scoreboard players set {negPl} {negOb} -1')
    lines.append(f'execute at @s if block ~ ~-1 ~ minecraft:obsidian run scoreboard players operation {outputPl} {outputOb} *= {negPl} {negOb}')
    lines.append(f'scoreboard players set {negPl} {negOb} 0')
    
    # Negative zero is -2147483648 by convention
    lines.append(f'execute at @s if block ~ ~-1 ~ minecraft:obsidian if score {outputPl} {outputOb} matches 0 run scoreboard players set {outputPl} {outputOb} -2147483648')

    return lines


# A helper function to get the current block and push it to the stack
def pushCurrBlock():
    filename = os.path.join(START_PATH, 'push_curr_block.mcfunction')
    lines = []
    
    # Variable to see if we found any block
    lines.append('scoreboard players set $temp temp1 0')
    
    # Get block
    for n in sorted(VALUE_TO_BLOCK.keys()):
        lines.append(f'execute at @s if block ~ ~ ~ {VALUE_TO_BLOCK[n]} run scoreboard players set $stack stackin {n}')
        lines.append(f'execute at @s if block ~ ~ ~ {VALUE_TO_BLOCK[n]} run scoreboard players set $temp temp1 1')
    
    # Push
    lines.append('execute if score $temp temp1 matches 1 run function craftyfunge:push_stack')
    
    # Reset scoreboard
    lines.append('scoreboard players set $temp temp1 0')
    
    writeFile(filename, lines)


def move():
    filename = os.path.join(START_PATH, 'move.mcfunction')
    lines = f'''
execute as @e[{FUNGIE}] at @s if score $ip direction matches 0 run tp ~ ~ ~-1
execute as @e[{FUNGIE}] at @s if score $ip direction matches 1 run tp ~ ~ ~1
execute as @e[{FUNGIE}] at @s if score $ip direction matches 2 run tp ~1 ~ ~
execute as @e[{FUNGIE}] at @s if score $ip direction matches 3 run tp ~-1 ~ ~
execute as @e[{FUNGIE}] at @s if score $ip direction matches 4 run tp ~ ~1 ~
execute as @e[{FUNGIE}] at @s if score $ip direction matches 5 run tp ~ ~-1 ~
'''.strip().splitlines()
    
    writeFile(filename, lines)


def conditionalSkip():
    filename = os.path.join(START_PATH, 'conditional_skip.mcfunction')
    lines = []
    lines.append('function craftyfunge:pop_stack1')
    lines.append('execute if score $stack stack1 matches 0 run function craftyfunge:move')
    
    # Temp reset stackin
    lines.append('scoreboard players set $stack stackin 0')
    
    writeFile(filename, lines)


def randomDirection():
    filename = os.path.join(START_PATH, 'random_direction.mcfunction')
    lines = '''
# From https://reddit.com/r/MinecraftCommands/wiki/questions/randomnumber
summon area_effect_cloud ~ ~ ~ {Tags:["random_uuid"]}
execute store result score $ip direction run data get entity @e[type=area_effect_cloud,tag=random_uuid,limit=1] UUID[0] 1
scoreboard players operation $ip direction %= $constants numdirs
kill @e[type=area_effect_cloud,tag=random_uuid]
'''.strip().splitlines()
    
    writeFile(filename, lines)


# A generic mode toggler
def toggleMode(mode):
    modeName = MODE_NAMES[mode]
    
    # Toggle
    filename = os.path.join(START_PATH, f'toggles/{modeName}/{modeName}_toggle.mcfunction')
    lines = []
    
    lines.append(f'execute unless score $ip mode matches {mode} if score $ip changed_mode matches 0 run function craftyfunge:toggles/{modeName}/{modeName}_start')
    lines.append(f'execute if score $ip mode matches {mode} if score $ip changed_mode matches 0 run function craftyfunge:toggles/{modeName}/{modeName}_stop')
    
    writeFile(filename, lines)
    
    
    # Starting the mode
    filename = os.path.join(START_PATH, f'toggles/{modeName}/{modeName}_start.mcfunction')
    lines = []
    
    lines.append(f'team join {MODE_NAMES[mode]}')
    lines.append(f'scoreboard players set $ip mode {mode}')
    lines.append(f'scoreboard players set $ip changed_mode 1')
    
    writeFile(filename, lines)
    

    # Stopping the mode
    filename = os.path.join(START_PATH, f'toggles/{modeName}/{modeName}_stop.mcfunction')
    lines = []
    
    lines.append(f'team join {MODE_NAMES[Modes.DEFAULT]}')
    lines.append(f'scoreboard players set $ip mode {Modes.DEFAULT}')
    
    writeFile(filename, lines)


# Tunneling ignores all instructions until it hits another tunnel
def tunnelToggle():
    toggleMode(Modes.TUNNEL)


def inNumLiteralToggle():
    toggleMode(Modes.IN_NUM_LITERAL)
    
    # Starting
    filename = os.path.join(START_PATH, 'toggles/in_num_literal/in_num_literal_start.mcfunction')
    lines = []
    
    # Initialize scoreboard
    # Temp1 is taken by pop_stack
    lines.append('scoreboard players set $temp temp2 1') # negation
    
    # Push 0 to the stack, for modifying
    lines.append('scoreboard players set $stack stackin 0')
    lines.append('function craftyfunge:push_stack')
    
    writeFile(filename, lines, mode='a')
    
    
    # Stopping
    filename = os.path.join(START_PATH, 'toggles/in_num_literal/in_num_literal_stop.mcfunction')
    lines = []
    
    # Reset scoreboard
    lines.append('scoreboard players set $temp temp2 0')
    lines.append('scoreboard players set $temp temp3 0')
    
    writeFile(filename, lines, mode='a')


def inStrLiteralToggle():
    toggleMode(Modes.IN_STR_LITERAL)


def moveStackLeft():
    filename = os.path.join(START_PATH, 'move_stack_left.mcfunction')
    lines = []
    
    lines.append(f'execute at @e[{STACKER}] run clone ~ ~-1 ~-1 ~ ~{MAX_NUMBER_HEIGHT} ~-{MAX_STACK_SIZE} ~ ~-1 ~-{MAX_STACK_SIZE-1} replace move')
    
    writeFile(filename, lines)


def moveStackRight():
    filename = os.path.join(START_PATH, 'move_stack_right.mcfunction')
    lines = []
    
    lines.append(f'execute at @e[{STACKER}] run clone ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~-{MAX_STACK_SIZE-1} ~ ~-1 ~-{MAX_STACK_SIZE} replace move')
    
    writeFile(filename, lines)


def dupStack():
    filename = os.path.join(START_PATH, 'duplicate.mcfunction')
    lines = []
    # Manipulate the blocks to duplicate the stack
    lines.append('function craftyfunge:move_stack_right')
    lines.append(f'execute at @e[{STACKER}] run clone ~ ~-1 ~-1 ~ ~{MAX_NUMBER_HEIGHT} ~-1 ~ ~-1 ~ replace')
    
    # Add 1 to length unless we're duplicating an empty stack
    lines.append('execute unless score $stack stacklen matches 0 run scoreboard players add $stack stacklen 1')
    
    writeFile(filename, lines)


def clearStack():
    filename = os.path.join(START_PATH, 'clear_stack.mcfunction')
    lines = []
    
    lines.append(f'execute at @e[{STACKER}] run fill ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~-{MAX_STACK_SIZE} minecraft:air')
    lines.append('scoreboard players set $stack stacklen 0')
    
    writeFile(filename, lines)


def popStack():
    for n in range(1, STACKS+1):
        # Calling function
        filename = os.path.join(START_PATH, f'pop_stack{n}.mcfunction')
        lines = [f'execute as @e[{STACKER}] run function craftyfunge:wrapped/pop_stack{n}']
        writeFile(filename, lines)
        
        # Wrapped function
        filename = os.path.join(START_PATH, f'wrapped/pop_stack{n}.mcfunction')
        lines = []
        
        # Reset stack
        lines.append(f'scoreboard players set $stack stack{n} 0')
        
        lines.extend(binaryDecode(('$temp', 'temp1'), ('$stack', f'stack{n}'), MAX_NUMBER_HEIGHT))
        
        # # Add to scoreboard
        # for exp in range(MAX_NUMBER_HEIGHT):
        #     lines.append(f'execute at @s if block ~ ~{exp} ~ minecraft:iron_block run scoreboard players add $stack stack{n} {2**exp}')
        
        # # Negate if necessary
        # lines.append('scoreboard players set $temp temp1 -1')
        # lines.append(f'execute at @s if block ~ ~-1 ~ minecraft:obsidian run scoreboard players operation $stack stack{n} *= $temp temp1')
        # lines.append('scoreboard players set $temp temp1 0')
        
        # # Negative zero is -2147483648 by convention
        # lines.append(f'execute at @s if block ~ ~-1 ~ minecraft:obsidian if score $stack stack{n} matches 0 run scoreboard players set $stack stack{n} -2147483648')
        
        # Remove 1 from stack length unless already empty
        lines.append('execute unless score $stack stacklen matches 0 run scoreboard players remove $stack stacklen 1')
        
        # Move left
        lines.append('function craftyfunge:move_stack_left')
        
        writeFile(filename, lines)


def pushStack():
    # Calling function
    filename = os.path.join(START_PATH, 'push_stack.mcfunction')
    lines = [f'execute as @e[{STACKER}] run function craftyfunge:wrapped/push_stack']
    writeFile(filename, lines)
    
    # Wrapped function
    filename = os.path.join(START_PATH, 'wrapped/push_stack.mcfunction')
    lines = []
    
    # Shift stack right
    lines.append('function craftyfunge:move_stack_right')
    
    # Add 1 to stack length if either nonzero or zero and something's already there.
    lines.append('execute if score $stack stackin matches 1.. run scoreboard players add $stack stacklen 1')
    lines.append('execute if score $stack stackin matches ..-1 run scoreboard players add $stack stacklen 1')
    lines.append('execute if score $stack stackin matches 0 unless score $stack stacklen matches 0 run scoreboard players add $stack stacklen 1')
    
    # Encode stackin as blocks
    lines.extend(binaryEncode(('$temp', 'temp1'), ('$stack', 'stackin'), MAX_NUMBER_HEIGHT))
    
    # Reset scoreboard
    lines.append('scoreboard players set $stack stackin 0')
        
    writeFile(filename, lines)


def pushNumStack():
    def pushNumType(blockType, exp):
        n = 10**exp
        
        filename = os.path.join(START_PATH, f'push_number/push_number_{n}.mcfunction')
        lines = []
        
        if exp == 0:
            lines.append('execute at @s if block ~ ~ ~ minecraft:white_concrete run scoreboard players set $stack stackin 0')
        
        for i, color in enumerate(COLORS):
            i += 1
            lines.append(f'execute at @s if block ~ ~ ~ minecraft:{color}_{blockType} run scoreboard players set $stack stackin {i*n}')
        
        writeFile(filename, lines)
    
    filename = os.path.join(START_PATH, 'push_number.mcfunction')
    lines = []
    
    # Temp reset stackin
    lines.append('scoreboard players set $stack stackin -1')
    
    # Get number into accumulator
    # Concrete is single-digits
    for exp, blockType in NUM_TYPES:
        pushNumType(blockType, exp)
        lines.append(f'execute at @s if block ~ ~ ~ #craftyfunge:{blockType} run function craftyfunge:push_number/push_number_{10**exp}')
    
    # Push number
    lines.append('execute unless score $stack stackin matches -1 run function craftyfunge:push_stack')
    
    # Reset stackin
    lines.append('scoreboard players set $stack stackin 0')
    
    writeFile(filename, lines)


def pushNextBlock():
    # Calling function
    filename = os.path.join(START_PATH, 'push_next_block.mcfunction')
    lines = []
    
    lines.append('function craftyfunge:move')
    lines.append('function craftyfunge:push_curr_block')

    writeFile(filename, lines)


def pushStackLength():
    filename = os.path.join(START_PATH, 'push_stack_length.mcfunction')
    lines = []
    
    lines.append('scoreboard players operation $stack stackin = $stack stacklen')
    lines.append('function craftyfunge:push_stack')

    writeFile(filename, lines)


# Removes trailing zeros from the stack length
def recountLength():
    # Initializing function
    filename = os.path.join(START_PATH, 'recount_length.mcfunction')
    lines = []
    
    lines.append('scoreboard players operation $temp temp2 = $stack stacklen')
    lines.append('execute unless score $stack stacklen matches 0 run scoreboard players remove $temp temp2 1')
    
    # Teleport to where it thinks the stack length is
    lines.extend(binaryTeleport(('$temp', 'temp2'), MAX_STACK_SIZE))
    lines.append('scoreboard players set $temp temp3 0')
    lines.append(f'execute store result score $temp temp3 run data get entity @e[{STACKER}] Pos[2] 1')
    
    lines.append(f'execute as @e[{STACKER}] at @s unless score $stack stacklen matches 0 if blocks ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~ ~1 ~-1 ~ all run function craftyfunge:wrapped/recount_length')
    lines.append(f'tp @e[{STACKER}] ~ ~ {STACKER_Z}')

    writeFile(filename, lines)
    
    # Wrapped recursive function
    filename = os.path.join(START_PATH, 'wrapped/recount_length.mcfunction')
    lines = []
    
    # Keep moving until reaching a zero value
    lines.append('scoreboard players remove $stack stacklen 1')
    lines.append('tp @s ~ ~ ~1')
    lines.append('scoreboard players set $temp temp3 0')
    lines.append(f'execute store result score $temp temp3 run data get entity @e[{STACKER}] Pos[2] 1')
    lines.append(f'execute as @s at @s unless score $stack stacklen matches 0 if blocks ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~ ~1 ~-1 ~ all run function craftyfunge:wrapped/recount_length')

    writeFile(filename, lines)


def arithmeticOperators():
    # Main function
    filename = os.path.join(START_PATH, 'arithmetic.mcfunction')
    lines = []
    
    binaryOperators = [
        ('add',     '+=',   ADD),
        ('sub',     '-=',   SUB),
        ('mult',    '*=',   MULT),
        ('div',     '/=',   DIV),
        ('mod',     '%=',   MOD),
    ]
    
    for name, _, block in binaryOperators:
        lines.append(f'execute at @s if block ~ ~ ~ minecraft:{block} run function craftyfunge:arithmetic/{name}')
        
    writeFile(filename, lines)
    
    # Binary Operators
    for name, op, _ in binaryOperators:
        filename = os.path.join(START_PATH, f'arithmetic/{name}.mcfunction')
        lines = []
        
        # Get top stack values
        lines.append('function craftyfunge:pop_stack1')
        lines.append('function craftyfunge:pop_stack2')
        
        # Divide by zero error
        if name == 'div' or name == 'mod':
            fullName = 'divide' if name == 'div' else name
            lines.append('execute if score $stack stack1 matches 0 run tellraw @a {"text":"Error: Attempted to %s by zero.","color":"red"}' % fullName)
            lines.append('execute if score $stack stack1 matches 0 run function craftyfunge:stop')
        
        # Reset stackin
        lines.append('scoreboard players set $stack stackin 0')
        
        # Add and swap
        lines.append(f'scoreboard players operation $stack stack2 {op} $stack stack1')
        lines.append('scoreboard players operation $stack stackin >< $stack stack2')
        
        # Reset stack1 and 2
        lines.append('scoreboard players set $stack stack1 0')
        lines.append('scoreboard players set $stack stack2 0')
        
        # Push
        lines.append('function craftyfunge:push_stack')
        
        writeFile(filename, lines)


def exponent():
    # Recursively multiply
    def multRec():
        filename = os.path.join(START_PATH, 'arithmetic/exp_rec_mult.mcfunction')
        lines = []
        
        lines.append('execute if score $stack stack1 matches 1.. run scoreboard players remove $stack stack1 1')
        lines.append('execute if score $stack stack1 matches 1.. run scoreboard players operation $stack stackin *= $stack stack2')
        
        lines.append('execute if score $stack stack1 matches 1.. run function craftyfunge:arithmetic/exp_rec_mult')
        
        writeFile(filename, lines)
    multRec()
    
    filename = os.path.join(START_PATH, 'arithmetic/exp.mcfunction')
    lines = []

    # Get stack
    lines.append('function craftyfunge:pop_stack1') # Exponent
    lines.append('function craftyfunge:pop_stack2') # Base
    
    # Negative exponents don't work, so just return 0
    lines.append('execute if score $stack stack1 matches ..-1 run scoreboard players set $stack stackin 0')
    lines.append('execute if score $stack stack1 matches ..-1 run scoreboard players set $stack stack2 0')
    
    # To the zeroth power
    lines.append('execute if score $stack stack1 matches 0 run scoreboard players set $stack stackin 1')
    lines.append('execute if score $stack stack1 matches 0 run scoreboard players set $stack stack2 1')
    
    # Multiply
    lines.append('scoreboard players operation $stack stackin = $stack stack2')
    lines.append('function craftyfunge:arithmetic/exp_rec_mult')
    
    # Push to stack
    lines.append('function craftyfunge:push_stack')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')
    lines.append('scoreboard players set $stack stack2 0')

    writeFile(filename, lines)
    

def negate():
    filename = os.path.join(START_PATH, 'arithmetic/neg.mcfunction')
    lines = []

    # Get stack
    lines.append('function craftyfunge:pop_stack1')
    
    # Multiply by -1
    lines.append('scoreboard players set $temp temp1 -1')
    lines.append('scoreboard players operation $stack stackin >< $stack stack1')
    lines.append('scoreboard players operation $stack stackin *= $temp temp1')
    
    lines.append('function craftyfunge:push_stack')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')
    lines.append('scoreboard players set $temp temp1 0')

    writeFile(filename, lines)
    

def outputNumber():
    filename = os.path.join(START_PATH, 'output_number.mcfunction')
    lines = []

    lines.append('function craftyfunge:pop_stack1')

    # Check for negative
    lines.append('scoreboard players set $temp temp1 1')
    lines.append('execute if score $stack stack1 matches ..-1 run scoreboard players set $temp temp1 -1')
    lines.append('execute if score $stack stack1 matches ..-1 run data modify storage craftyfunge:io textBuffer append value "-"')
    lines.append('execute if score $stack stack1 matches ..-1 run scoreboard players operation $stack stack1 *= $temp temp1')
    lines.append('scoreboard players set $temp temp1 0')
    
    # Temp1 is when we find the topmost digit
    lines.append('scoreboard players set $temp temp1 0')
    
    for exp in range(MAX_DIGITS-1, -1, -1):
        # Temp 2 is if we find any digits
        lines.append('scoreboard players set $temp temp2 0')
        for i in range(9, 0, -1):
            n = i * 10**exp
            if n > MAX_VAL:
                continue
            
            lines.append(f'execute if score $stack stack1 matches {n}.. run data modify storage craftyfunge:io textBuffer append value "{i}"')
            lines.append(f'execute if score $stack stack1 matches {n}.. run scoreboard players set $temp temp1 1')
            lines.append(f'execute if score $stack stack1 matches {n}.. run scoreboard players set $temp temp2 1')
            lines.append(f'execute if score $stack stack1 matches {n}.. run scoreboard players remove $stack stack1 {n}')

        lines.append('execute if score $temp temp1 matches 1 if score $temp temp2 matches 0 run data modify storage craftyfunge:io textBuffer append value "0"')
    
    # Special case of MIN_VAL
    lines.append('execute if score $stack stack1 matches -2147483648 run scoreboard players set $temp temp1 1')
    for digit in str(MIN_VAL)[1:]:
        lines.append(f'execute if score $stack stack1 matches -2147483648 run data modify storage craftyfunge:io textBuffer append value "{digit}"')
    
    # Special case for 0
    lines.append('execute unless score $temp temp1 matches 1 run data modify storage craftyfunge:io textBuffer append value "0"')
    
    # Final space
    lines.append('data modify storage craftyfunge:io textBuffer append value " "')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')
    lines.append('scoreboard players set $temp temp1 0')
    lines.append('scoreboard players set $temp temp2 0')
    lines.append('scoreboard players set $temp temp3 0')
    
    # Output all text in buffer
    lines.append('function craftyfunge:output')

    writeFile(filename, lines)


def outputAscii():
    filename = os.path.join(START_PATH, 'output_ascii.mcfunction')
    lines = []
    
    # Pop
    lines.append('function craftyfunge:pop_stack1')
    
    # Ascii code to character
    backslash = '\\'
    for ordinal in range(32, 127):
        if chr(ordinal) == '"':
            # Changes it to two single quotes because for some reason minecraft doesn't like the double quote, even when escaped
            char = "''"
        elif chr(ordinal) == backslash:
            char = backslash+backslash
        else:
            char = chr(ordinal)
            
        lines.append(f'execute if score $stack stack1 matches {ordinal} run data modify storage craftyfunge:io textBuffer append value "{char}"')
    
    # Newline
    newline = ord('\n')
    lines.append(f'execute if score $stack stack1 matches {newline} run data modify storage craftyfunge:io textBuffer append from storage suso.str:internal newline')
    
    # Bell
    lines.append('execute if score $stack stack1 matches 7 run playsound block.note_block.bell master @a ~ ~ ~ 1 0.5 1')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')
    
    # Output all text in buffer
    lines.append('function craftyfunge:output')

    writeFile(filename, lines)
    

def output():
    filename = os.path.join(START_PATH, 'output.mcfunction')
    lines = []
    
    lines.append('tellraw @a ["%s"]' % ('\\n'*50))
    lines.append('tellraw @a {"nbt":"textBuffer","storage":"craftyfunge:io","interpret":"true"}')
    
    writeFile(filename, lines)


# Not used now, was used for debug intitially
def outputSign():
    filename = os.path.join(START_PATH, 'signs.mcfunction')
    lines = []
    
    # Oak signs push character onto stack
    backslash = '\\'
    for ordinal in range(32, 127):
        if chr(ordinal) == '"':
            char = backslash + '"'
        elif chr(ordinal) == backslash:
            char = backslash+backslash
        else:
            char = chr(ordinal)

        lines.append('execute at @s if block ~ ~ ~ minecraft:oak_sign{Text2:"{\\"text\\":\\"%s\\"}"} run scoreboard players set $stack stackin %i' % (char, ordinal))
    
    lines.append('execute unless score $stack stackin matches 0 run function craftyfunge:push_stack')
    
    # Birch signs display each line separately if non-empty
    for lineNum in range(1, 5):
        lines.append('execute at @s if block ~ ~ ~ minecraft:birch_sign unless block ~ ~ ~ minecraft:birch_sign{Text%i:"{\\"text\\":\\"\\"}"} run tellraw @a {"nbt":"Text%i","block":"~ ~ ~","interpret":"true"}' % (lineNum, lineNum))
    
    # Crimson signs display all lines merged together
    lines.append('execute at @s if block ~ ~ ~ minecraft:crimson_sign run tellraw @a {"nbt":"Text1","block":"~ ~ ~","interpret":"true","extra":[{"nbt":"Text2","block":"~ ~ ~","interpret":"true"},{"nbt":"Text3","block":"~ ~ ~","interpret":"true"},{"nbt":"Text4","block":"~ ~ ~","interpret":"true"}]}')

    writeFile(filename, lines)


def outputNewline():
    filename = os.path.join(START_PATH, 'output_newline.mcfunction')
    lines = []
    
    lines.append('data modify storage craftyfunge:io textBuffer append from storage suso.str:internal newline')
    lines.append('function craftyfunge:output')

    writeFile(filename, lines)


def raiseError():
    filename = os.path.join(START_PATH, 'raise_error.mcfunction')
    lines = []
    
    lines.append('tellraw @a {"text":"Error: An error was manually raised.","color":"red"}')
    lines.append('function craftyfunge:stop')

    writeFile(filename, lines)


def changeDirection():
    filename = os.path.join(START_PATH, 'change_direction.mcfunction')
    lines = []
    
    for i, dirn in enumerate(DIRS):
        lines.append(f'execute at @s if block ~ ~ ~ minecraft:piston[facing={dirn}] run scoreboard players set $ip direction {i}')
    
    writeFile(filename, lines)


def start():
    startFilename = os.path.join(START_PATH, 'start.mcfunction')
    stepFilename = os.path.join(START_PATH, 'start_step.mcfunction')
    lines = []
    
    # Respawn start anchor
    lines.append('kill @e[tag=StartAnchor]')
    lines.append('summon minecraft:armor_stand ~ ~ ~ {Tags:["StartAnchor"],Invisible:1b}')
    
    # Kill extraneous entities
    lines.append(f'kill @e[{MARKER[:-8]}]')
    
    # Reset positions
    lines.append(f'tp @e[{FUNGIE}] ~ ~-0.5 ~')
    lines.append(f'tp @e[{STACKER}] {STACKER_POS[0]} {STACKER_POS[1]} {STACKER_POS[2]}')
    lines.append(f'tp @e[{SETTER}] {SETTER_POS[0]} {SETTER_POS[1]} {SETTER_POS[2]}')
    
    # Direction depends on command block orientation
    for i, dirn in enumerate(DIRS):
        lines.append(f'execute if block ~ ~ ~ minecraft:command_block[facing={dirn}] run scoreboard players set $ip direction {i}')
    # Resetting scoreboard
    for i in range(1, STACKS+1):
        lines.append(f'scoreboard players set $stack stack{i} 0')
    for i in range(1, TEMPS+1):
        lines.append(f'scoreboard players set $temp temp{i} 0')
    
    for player, objective in [('$stack', 'stackin'), ('$stack', 'stacklen'), ('$ip', 'changed_mode'), ('$ip', 'went_to')]:
        lines.append(f'scoreboard players set {player} {objective} 0')
    
    lines.append(f'scoreboard players set $ip mode {Modes.DEFAULT}')
    
    for axis, objective in enumerate(AXIS_NAMES):
        lines.append(f'execute store result score $start_pos {objective} run data get entity @e[tag=StartAnchor,limit=1] Pos[{axis}] 1')
    
    # Reset stack and vars
    lines.append(f'execute at @e[{STACKER}] run fill ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~-{MAX_STACK_SIZE} minecraft:air')
    lines.append(f'execute at @e[{SETTER}] run fill ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~-{MAX_STACK_SIZE} minecraft:air')
    
    # Reset text buffer
    lines.append('data remove storage craftyfunge:io textBuffer')
    lines.append('data remove storage craftyfunge:io eatenBuffer')
    
    # Prepopulate stack, then parse input
    lines.append('function suso.str:charsets/ascii')
    
    def writeStartFile(lines, filename=None, stepping=None, mode=None):
        newLines = lines.copy()
        
        # Change fungie color to green
        newLines.append(f'team join {MODE_NAMES[mode]} @e[{FUNGIE}]')
        
        # Parse prepopulation and input
        newLines.append(f'scoreboard players set $ip stepping {stepping}')
        newLines.append('function craftyfunge:prepop/parse_prepop')
        
        writeFile(filename, newLines)
    
    writeStartFile(lines, filename=startFilename, stepping=0, mode=Modes.DEFAULT)
    writeStartFile(lines, filename=stepFilename, stepping=1, mode=Modes.PAUSED)
    
    
    # Get all characters from prepopulating book
    def parsePrepop():
        filename = os.path.join(START_PATH, 'prepop/parse_prepop.mcfunction')
        lines = []
        
        lines.append('data remove storage craftyfunge:io inputBuffer')
        lines.append('data modify storage suso.str:io out set value []')
        lines.append('data modify storage suso.str:io in.string set value ""')
        lines.append('execute at @e[tag=Prepop,limit=1] run data modify storage suso.str:io in.string set from block ~ ~2 ~ Items[0].tag.pages[0]')
        lines.append('data modify storage suso.str:io in.callback set value "function craftyfunge:prepop/input_all_prepop"')
        lines.append('function suso.str:call')
        
        writeFile(filename, lines)
    parsePrepop()
    
    # Input everything to the stack
    def inputAllPrepop():
        filename = os.path.join(START_PATH, 'prepop/input_all_prepop.mcfunction')
        lines = []
        
        # Initialize scoreboard
        lines.append('scoreboard players set $temp temp4 1')
        
        # Get everything into the stack
        lines.append('function craftyfunge:prepop/input_prepop_recurse')
        
        # Reset
        lines.append('function craftyfunge:pop_stack1')
        lines.append('scoreboard players set $stack stack1 0')
        lines.append('scoreboard players set $temp temp4 0')
        
        # Parse regular input
        lines.append('function craftyfunge:parse_input')
        
        writeFile(filename, lines)
    inputAllPrepop()
    
    # Input one thing to the stack and recurse
    def inputPrepopRecurse():
        filename = os.path.join(START_PATH, 'prepop/input_prepop_recurse.mcfunction')
        lines = []
        
        lines.append('function craftyfunge:input/input_number')
        lines.append('execute if score $temp temp4 matches 1 run function craftyfunge:prepop/input_prepop_recurse')
        
        writeFile(filename, lines)
    inputPrepopRecurse()
    
    # Get all characters from input book
    def parseInput():
        filename = os.path.join(START_PATH, 'parse_input.mcfunction')
        lines = []
        
        lines.append('data remove storage craftyfunge:io inputBuffer')
        lines.append('data modify storage suso.str:io out set value []')
        lines.append('data modify storage suso.str:io in.string set value ""')
        lines.append('execute at @e[tag=Input,limit=1] run data modify storage suso.str:io in.string set from block ~ ~2 ~ Items[0].tag.pages[0]')
        lines.append(f'execute if score $ip stepping matches 0 run data modify storage suso.str:io in.callback set value "function craftyfunge:wrapped/start_moving"')
        lines.append(f'execute if score $ip stepping matches 1 run data modify storage suso.str:io in.callback set value ""')
        lines.append('function suso.str:call')
        
        writeFile(filename, lines)
    parseInput()
    
    # Start automatically moving
    def startMoving():
        filename = os.path.join(START_PATH, 'wrapped/start_moving.mcfunction')
        lines = []
        
        lines.append(f'scoreboard players operation $ip move_countdown = $ip delay')
        lines.append(f'scoreboard players set $ip running 1')
        
        writeFile(filename, lines)
    startMoving()


def stop():
    # Stopping
    filename = os.path.join(START_PATH, 'stop.mcfunction')
    lines = []
    
    lines.append(f'scoreboard players set $ip direction -1')
    lines.append('kill @e[tag=StartAnchor]')
    lines.append(f'scoreboard players set $ip mode {Modes.STOPPED}')
    lines.append(f'scoreboard players set $ip running 0')
    lines.append('schedule function craftyfunge:red_fungie 0.1s')
    
    writeFile(filename, lines)
    
    # Make fungie red at the end
    filename = os.path.join(START_PATH, 'red_fungie.mcfunction')
    lines = [f'team join {MODE_NAMES[Modes.STOPPED]} @e[{FUNGIE}]']
    writeFile(filename, lines)


# Toggles between paused and running
def pauseToggle():
    filename = os.path.join(START_PATH, 'pause_toggle.mcfunction')
    lines = []
    
    # Change mode
    lines.append('execute if score $ip stepping matches 0 run function craftyfunge:pause')
    lines.append('execute if score $ip stepping matches 1 run function craftyfunge:resume')
    
    # Reset stepping if necessary
    lines.append('execute if score $ip stepping matches 0 if score $ip running matches 0 run scoreboard players set $ip stepping 1')
    
    writeFile(filename, lines)
    

# Transitions to stepping
def pause():
    filename = os.path.join(START_PATH, 'pause.mcfunction')
    lines = []
    
    lines.append(f'team join {MODE_NAMES[Modes.PAUSED]} @e[{FUNGIE}]')
    lines.append(f'scoreboard players set $ip running 0')
    # lines.append(f'scoreboard players set $ip stepping 1')
    
    writeFile(filename, lines)


# Resumes moving
def resume():
    filename = os.path.join(START_PATH, 'resume.mcfunction')
    lines = []
    
    # Change fungie color to green
    lines.append(f'team join {MODE_NAMES[Modes.DEFAULT]} @e[{FUNGIE}]')
    lines.append(f'scoreboard players set $ip mode {Modes.DEFAULT}')
    lines.append(f'scoreboard players set $ip changed_mode 0')
    lines.append(f'scoreboard players set $ip running 1')
    lines.append(f'scoreboard players set $ip stepping 0')
    
    writeFile(filename, lines)


# Stops the program and recalls the IP to a place near the executor
def recall():
    filename = os.path.join(START_PATH, 'recall.mcfunction')
    lines = []
    
    lines.append('function craftyfunge:stop')
    lines.append(f'tp @e[{FUNGIE}] ~-2 ~-0.5 ~')
    
    writeFile(filename, lines)
    

def clearProgram():
    filename = os.path.join(START_PATH, 'clear_program.mcfunction')
    lines = []
    
    lines.append('fill ~1 ~ ~1 ~35 ~25 ~35 minecraft:air')
    lines.append('setblock ~4 ~ ~4 minecraft:command_block[facing=south]{Command:"function craftyfunge:start"}')
    lines.append('setblock ~3 ~ ~4 minecraft:stone_button[face=wall,facing=west]')
    lines.append('kill @e[type=minecraft:item]')
    
    writeFile(filename, lines)


def conditional():
    filename = os.path.join(START_PATH, 'conditional.mcfunction')
    lines = []

    lines.append('function craftyfunge:pop_stack1')
    
    # Non-zero
    for i, dirn in enumerate(DIRS):
        lines.append(f'execute at @s if block ~ ~ ~ minecraft:observer[facing={dirn}] unless score $stack stack1 matches 0 run scoreboard players set $ip direction {i}')
    
    # Zero
    for i, dirn in enumerate(DIRS_INV):
        lines.append(f'execute at @s if block ~ ~ ~ minecraft:observer[facing={dirn}] if score $stack stack1 matches 0 run scoreboard players set $ip direction {i}')

    writeFile(filename, lines)


def comparisons():
    filename = os.path.join(START_PATH, 'comparisons.mcfunction')
    lines = []

    compTypes = [
        ('lessthan',     '<',   'cracked_stone_bricks'),
        ('greaterthan',  '>',   'mossy_stone_bricks'),
    ]
    
    for name, _, block in compTypes:
        lines.append(f'execute at @s if block ~ ~ ~ minecraft:{block} run function craftyfunge:comparisons/{name}')

    writeFile(filename, lines)

    # Comparisons
    for name, op, _ in compTypes:
        filename = os.path.join(START_PATH, f'comparisons/{name}.mcfunction')
        lines = []

        # Get top stack values
        lines.append('function craftyfunge:pop_stack1')
        lines.append('function craftyfunge:pop_stack2')

        # Reset stackin
        lines.append('scoreboard players set $stack stackin 0')
        
        # Compare
        lines.append(f'execute if score $stack stack2 {op} $stack stack1 run scoreboard players set $stack stackin 1')

        # Reset stack1 and 2
        lines.append('scoreboard players set $stack stack1 0')
        lines.append('scoreboard players set $stack stack2 0')

        # Push
        lines.append('function craftyfunge:push_stack')

        writeFile(filename, lines)


def swap():
    filename = os.path.join(START_PATH, 'swap.mcfunction')
    lines = []

    lines.append(f'execute at @e[{STACKER}] run clone ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~ ~1 ~-1 ~ replace move')
    lines.append(f'execute at @e[{STACKER}] run clone ~ ~-1 ~-1 ~ ~{MAX_NUMBER_HEIGHT} ~-1 ~ ~-1 ~ replace move')
    lines.append(f'execute at @e[{STACKER}] run clone ~1 ~-1 ~ ~1 ~{MAX_NUMBER_HEIGHT} ~ ~ ~-1 ~-1 replace move')

    writeFile(filename, lines)


def rotate():
    # Calling function
    filename = os.path.join(START_PATH, 'rotate.mcfunction')
    lines = [f'execute as @e[{STACKER}] run function craftyfunge:wrapped/rotate']
    writeFile(filename, lines)
    
    # Wrapped function
    filename = os.path.join(START_PATH, 'wrapped/rotate.mcfunction')
    lines = []

    # Get rotate length
    lines.append('function craftyfunge:pop_stack1')
    
    # Get sign and take absolute value
    lines.append('scoreboard players set $temp temp1 1')
    lines.append('execute if score $stack stack1 matches ..-1 run scoreboard players set $temp temp1 -1')
    lines.append('scoreboard players operation $stack stack1 *= $temp temp1')
    lines.append('scoreboard players operation $temp temp2 = $stack stack1')
    
    # Teleport there
    lines.extend(binaryTeleport(('$stack', 'stack1'), MAX_STACK_SIZE))
    
    # For positive rotations, bottom goes to top. [2 1 2 3 4 5] -> [3 1 2 4 5]
    lines.append('execute at @s if score $temp temp1 matches 1 run function craftyfunge:wrapped/rotate_right')
    def rotateRight():
        filename = os.path.join(START_PATH, 'wrapped/rotate_right.mcfunction')
        lines = []
        
        # Moving blocks
        lines.append(f'clone ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~ ~1 ~-1 {STACK_Z} replace move')
        lines.append(f'clone ~ ~-1 ~1 ~ ~{MAX_NUMBER_HEIGHT} {STACK_Z} ~ ~-1 ~ replace move')
        lines.append(f'clone ~1 ~-1 {STACK_Z} ~1 ~{MAX_NUMBER_HEIGHT} {STACK_Z} ~ ~-1 {STACK_Z} replace move')
        
        # Teleport back
        lines.append(f'execute at @s run tp @s ~ ~ {STACKER_Z}')
        
        # Changing the stack length if applicable
        lines.append('execute if score $stack stacklen matches 1.. if score $temp temp2 >= $stack stacklen run scoreboard players add $stack stacklen 1')
        
        # Reckecking the stack length if taking the last element to the front
        lines.append('scoreboard players operation $temp temp2 -= $stack stacklen')
        lines.append(f'execute as @e[{STACKER}] at @s if score $temp temp2 matches -1 run function craftyfunge:recount_length')
        
        writeFile(filename, lines)
    rotateRight()
    
    # For negative rotations, top goes to bottom. [-2 1 2 3 4 5] -> [2 3 1 4 5]
    lines.append('execute at @s if score $temp temp1 matches -1 run function craftyfunge:wrapped/rotate_left')
    def rotateLeft():
        filename = os.path.join(START_PATH, 'wrapped/rotate_left.mcfunction')
        lines = []
        
        # Moving blocks
        lines.append(f'clone ~ ~-1 {STACK_Z} ~ ~{MAX_NUMBER_HEIGHT} {STACK_Z} ~1 ~-1 {STACK_Z} replace move')
        lines.append(f'clone ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} {STACK_Z-1} ~ ~-1 ~1 replace move')
        lines.append(f'clone ~1 ~-1 {STACK_Z} ~1 ~{MAX_NUMBER_HEIGHT} {STACK_Z} ~ ~-1 ~ replace move')
        
        # Teleport back
        lines.append(f'execute at @s run tp @s ~ ~ {STACKER_Z}')
        
        # Changing the stack length if applicable
        lines.append('execute if score $stack stacklen matches 1.. if score $temp temp2 >= $stack stacklen run scoreboard players operation $stack stacklen = $temp temp2')
        lines.append('execute if score $stack stacklen matches 1.. if score $temp temp2 = $stack stacklen run scoreboard players add $stack stacklen 1')
        
        writeFile(filename, lines)
    rotateLeft()
    
    # Reset stack1
    lines.append('scoreboard players set $stack stack1 0')
    lines.append('scoreboard players set $temp temp1 0')
    lines.append('scoreboard players set $temp temp2 0')

    writeFile(filename, lines)


def logicalNot():
    filename = os.path.join(START_PATH, 'not.mcfunction')
    lines = []

    # Get stack
    lines.append('function craftyfunge:pop_stack1')
    
    # Invert
    lines.append('execute if score $stack stack1 matches 0 run scoreboard players set $stack stackin 1')
    lines.append('execute unless score $stack stack1 matches 0 run scoreboard players set $stack stackin 0')
    
    # Push
    lines.append('function craftyfunge:push_stack')

    writeFile(filename, lines)


def markPos():
    filename = os.path.join(START_PATH, 'mark_pos.mcfunction')
    lines = []
    
    # Summon temp entity
    lines.append('summon marker ~ ~ ~ {Tags:["BlockMarker"]}')
    
    # Teleport it one coordinate at a time. Pop order is z, y, x, so we start with axis 2 and go to 0
    for axis in range(2, -1, -1):
        # Get stack
        lines.append('function craftyfunge:pop_stack1')
        # Add scores
        lines.append(f'scoreboard players operation $stack stack1 += $start_pos {AXIS_NAMES[axis]}')
        # Teleport temp entity
        lines.append(f'execute store result entity @e[{MARKER}] Pos[{axis}] double 1 run scoreboard players get $stack stack1')
        # Reset
        lines.append('scoreboard players set $stack stack1 0')
    
    writeFile(filename, lines)


def getBlock():
    # Calling function
    filename = os.path.join(START_PATH, 'get_block.mcfunction')
    lines = []
    
    lines.append('function craftyfunge:mark_pos')
    lines.append(f'execute as @e[{MARKER}] run function craftyfunge:wrapped/get_block')
    
    writeFile(filename, lines)
    
    # Wrapped function
    filename = os.path.join(START_PATH, 'wrapped/get_block.mcfunction')
    lines = []
    
    lines.append('function craftyfunge:push_curr_block')
    
    # Clean up temp entity
    lines.append('kill @s')

    writeFile(filename, lines)
    

def setBlock():
    # Calling function
    filename = os.path.join(START_PATH, 'set_block.mcfunction')
    lines = []
    
    lines.append('function craftyfunge:mark_pos')
    lines.append(f'execute as @e[{MARKER}] run function craftyfunge:wrapped/set_block')
    
    writeFile(filename, lines)
    
    # Wrapped function
    filename = os.path.join(START_PATH, 'wrapped/set_block.mcfunction')
    lines = []
    
    lines.append('function craftyfunge:pop_stack4') # value
    
    # Set block
    for n in sorted(VALUE_TO_BLOCK.keys()):
        block = VALUE_TO_BLOCK[n]
        # Make leaves persistent
        if block.endswith('leaves'):
            block = block + '[persistent=true]'
        
        lines.append(f'execute at @s if score $stack stack4 matches {n} run setblock ~ ~ ~ {block}')
    
    # Clean up temp entity
    lines.append('kill @s')
    
    lines.append('scoreboard players set $stack stack4 0')

    writeFile(filename, lines)


def getVar():
    # Calling function
    filename = os.path.join(START_PATH, 'get_var.mcfunction')
    lines = [f'execute as @e[{SETTER}] run function craftyfunge:wrapped/get_var']
    writeFile(filename, lines)
    
    # Wrapped function
    filename = os.path.join(START_PATH, 'wrapped/get_var.mcfunction')
    lines = []
    
    # Get variable index
    lines.append('function craftyfunge:pop_stack1')
    
    # Teleport there
    lines.extend(binaryTeleport(('$stack', 'stack1'), MAX_VARS_SIZE))
    lines.extend(binaryDecode(('$temp', 'temp1'), ('$stack', 'stackin'), MAX_NUMBER_HEIGHT))
    
    # Teleport back
    lines.append(f'execute at @s run tp @s ~ ~ {SETTER_Z}')
    
    # Push onto stack
    lines.append('function craftyfunge:push_stack')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')

    writeFile(filename, lines)


def setVar():
    # Calling function
    filename = os.path.join(START_PATH, 'set_var.mcfunction')
    lines = [f'execute as @e[{SETTER}] run function craftyfunge:wrapped/set_var']
    writeFile(filename, lines)
    
    # Wrapped function
    filename = os.path.join(START_PATH, 'wrapped/set_var.mcfunction')
    lines = []
    
    # Get index and value
    lines.append('function craftyfunge:pop_stack1')
    lines.append('function craftyfunge:pop_stack2')
    
    # Teleport there
    lines.extend(binaryTeleport(('$stack', 'stack1'), MAX_VARS_SIZE))
    
    # Reset the variable to 0
    lines.append(f'execute at @s run fill ~ ~-1 ~ ~ ~{MAX_NUMBER_HEIGHT} ~ minecraft:air')
    
    # Set the variable to new value
    lines.extend(binaryEncode(('$temp', 'temp1'), ('$stack', 'stack2'), MAX_NUMBER_HEIGHT))
    
    # Teleport back
    lines.append(f'execute at @s run tp @s ~ ~ {SETTER_Z}')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')
    lines.append('scoreboard players set $stack stack2 0')

    writeFile(filename, lines)


def pushPos():
    filename = os.path.join(START_PATH, 'push_pos.mcfunction')
    lines = []
    
    # Get one axis at a time. Push order is x, y, z
    for axis in range(3):
        # Get command block start position
        lines.append(f'execute store result score $stack stackin run data get entity @e[{FUNGIE}] Pos[{axis}] 1')
        # Add scores
        lines.append(f'scoreboard players operation $stack stackin -= $start_pos {AXIS_NAMES[axis]}')
        # Push to stack
        lines.append('function craftyfunge:push_stack')
    
    writeFile(filename, lines)


def goto():
    filename = os.path.join(START_PATH, 'goto.mcfunction')
    lines = []
    
    # Teleport marker to temp position
    lines.append('function craftyfunge:mark_pos')
    
    # Teleport Fungie to marker and offset
    lines.append(f'tp @e[{FUNGIE}] @e[{MARKER}]')
    lines.append(f'execute as @e[{FUNGIE}] at @s run tp ~0.5 ~ ~0.5')
    
    # Mark as went tto
    lines.append(f'scoreboard players set $ip went_to 1')
    
    # Clean up
    lines.append(f'kill @e[{MARKER}]')

    writeFile(filename, lines)


def inputAscii():
    filename = os.path.join(START_PATH, 'input/input_ascii.mcfunction')
    lines = []
    
    # Default is -1 (for EOF)
    lines.append('scoreboard players set $stack stackin -1')
    
    # Test for newline
    newline = ord('\n')
    lines.append('scoreboard players set $temp temp1 1')
    lines.append('data modify storage craftyfunge:io inputBuffer set from storage suso.str:io out[0]')
    lines.append('execute store success score $temp temp1 run data modify storage craftyfunge:io inputBuffer set from storage suso.str:internal newline') # 0 if newline
    lines.append(f'execute if score $temp temp1 matches 0 run scoreboard players set $stack stackin {newline}') # If newline, push 10
    
    # Reset input buffer if not newline and remove the top
    lines.append('execute if score $temp temp1 matches 1 run data modify storage craftyfunge:io inputBuffer set from storage suso.str:io out[0]')
    lines.append('data remove storage suso.str:io out[0]')
    
    # Change stackin based on input value
    backslash = '\\'
    for ordinal in range(32, 127):
        if chr(ordinal) == '"':
            char = backslash + '"'
        elif chr(ordinal) == backslash:
            char = backslash+backslash
        else:
            char = chr(ordinal)
        
        lines.append('execute if data storage craftyfunge:io {inputBuffer:"%s"} run scoreboard players set $stack stackin %i' % (char, ordinal))
    
    # Reset
    lines.append('scoreboard players set $temp temp1 0')
    lines.append('data remove storage craftyfunge:io inputBuffer')
    lines.append('function craftyfunge:push_stack')

    writeFile(filename, lines)


def inputNumber():
    def inputDigits():
        filename = os.path.join(START_PATH, 'input/input_digits.mcfunction')
        lines = []
        
        # Get input buffer
        lines.append('data modify storage craftyfunge:io inputBuffer set from storage suso.str:io out[0]')
        
        # Digit
        lines.append('scoreboard players set $temp temp1 0')
        lines.append('scoreboard players set $temp temp2 0')
        for n in range(10):
            lines.append('execute if data storage craftyfunge:io {inputBuffer:"%i"} run scoreboard players set $temp temp2 %i' % (n, n))
            lines.append('execute if data storage craftyfunge:io {inputBuffer:"%i"} run scoreboard players set $temp temp1 1' % n)
            lines.append('execute if data storage craftyfunge:io {inputBuffer:"%i"} run scoreboard players set $temp temp4 1' % n)
        
        # If numeric:
        # Add and multiply
        lines.append('execute if score $temp temp1 matches 1 run scoreboard players operation $stack stackin *= $constants ten')
        lines.append('execute if score $temp temp1 matches 1 run scoreboard players operation $stack stackin += $temp temp2')
        # Remove from list
        lines.append('execute if score $temp temp1 matches 1 run data remove storage suso.str:io out[0]')
        lines.append('data modify storage craftyfunge:io inputBuffer set value ""')
        
        # Recurse
        lines.append('execute if score $temp temp1 matches 1 run function craftyfunge:input/input_digits')
        
        writeFile(filename, lines)
    inputDigits()
    
    # Removes preceding spaces
    def eatSpaces():
        filename = os.path.join(START_PATH, 'input/eat_spaces.mcfunction')
        lines = []
        
        # Ignore preceding spaces
        lines.append('scoreboard players set $temp temp1 1')
        lines.append('data modify storage craftyfunge:io inputBuffer set from storage suso.str:io out[0]')
        lines.append('execute if data storage craftyfunge:io {inputBuffer:" "} run scoreboard players set $temp temp1 0')
        lines.append('execute if data storage craftyfunge:io {inputBuffer:" "} run data modify storage craftyfunge:io eatenBuffer prepend value " "')
        lines.append('execute if data storage craftyfunge:io {inputBuffer:" "} run data remove storage suso.str:io out[0]')
        
        # If temp1=0 then we succeeded and try again
        lines.append('execute if score $temp temp1 matches 0 run function craftyfunge:input/eat_spaces')
        
        writeFile(filename, lines)
    eatSpaces()
    
    # Puts back the whitespace (and negative sign) if there was nothing after
    def restoreEatenInput():
        filename = os.path.join(START_PATH, 'input/restore_eaten_input.mcfunction')
        lines = []
        
        lines.append('scoreboard players set $temp temp1 0')
        lines.append('data modify storage suso.str:io out prepend from storage craftyfunge:io eatenBuffer[0]')
        lines.append('execute store success score $temp temp1 run data remove storage craftyfunge:io eatenBuffer[0]')
        lines.append('execute if score $temp temp1 matches 1 run function craftyfunge:input/restore_eaten_input')
        
        writeFile(filename, lines)
    restoreEatenInput()
    
    filename = os.path.join(START_PATH, 'input/input_number.mcfunction')
    lines = []
    
    lines.append('data remove storage craftyfunge:io eatenBuffer')
    
    # Ignore spaces
    lines.append('function craftyfunge:input/eat_spaces')
    
    # Ignore newline
    lines.append('scoreboard players set $temp temp1 1')
    lines.append('data modify storage craftyfunge:io inputBuffer set from storage suso.str:io out[0]')
    lines.append('execute store success score $temp temp1 run data modify storage craftyfunge:io inputBuffer set from storage suso.str:internal newline') # 0 if newline
    lines.append('execute if score $temp temp1 matches 0 run data modify storage craftyfunge:io eatenBuffer prepend from storage suso.str:internal newline')
    lines.append('execute if score $temp temp1 matches 0 run data remove storage suso.str:io out[0]')
    
    # Check for negative
    lines.append('scoreboard players set $temp temp3 1')
    lines.append('data modify storage craftyfunge:io inputBuffer set from storage suso.str:io out[0]')
    lines.append('execute if data storage craftyfunge:io {inputBuffer:"-"} run scoreboard players set $temp temp3 -1')
    lines.append('execute if score $temp temp3 matches -1 run data modify storage craftyfunge:io eatenBuffer prepend value "-"')
    lines.append('execute if score $temp temp3 matches -1 run data remove storage suso.str:io out[0]')
    lines.append('data modify storage craftyfunge:io inputBuffer set value ""')
    
    # Get number
    lines.append('scoreboard players set $temp temp4 0')
    lines.append('function craftyfunge:input/input_digits')
    
    # Negate if necessary
    lines.append('scoreboard players operation $stack stackin *= $temp temp3')
    
    # If we got something before but there was nothing afterwards, we re-add that to the input
    lines.append('execute if score $temp temp4 matches 0 run scoreboard players set $stack stackin -1')
    lines.append('execute if score $temp temp4 matches 0 run function craftyfunge:input/restore_eaten_input')
    
    # Push stack
    lines.append('function craftyfunge:push_stack')
    
    # Reset
    lines.append('data remove storage craftyfunge:io inputBuffer')
    lines.append('scoreboard players set $temp temp1 0')
    lines.append('scoreboard players set $temp temp2 0')
    lines.append('scoreboard players set $temp temp3 0')
    # lines.append('scoreboard players set $temp temp4 0') Don't reset this. It's used for prepopulation.

    writeFile(filename, lines)


def inNumLiteral():
    filename = os.path.join(START_PATH, 'in_num_literal.mcfunction')
    lines = []
    
    # Pop top of stack
    lines.append('function craftyfunge:pop_stack1')
    
    # Reset sign
    lines.append('execute if score $stack stack1 matches ..-1 run scoreboard players operation $stack stack1 *= $temp temp2')
    lines.append('execute if score $stack stack1 matches 0.. unless score $temp temp2 matches -1 run scoreboard players operation $stack stack1 *= $temp temp2')
    # Multiply by 10
    lines.append('scoreboard players operation $stack stack1 *= $constants ten')
    
    # Add the next literal
    lines.append('execute at @s if block ~ ~ ~ minecraft:white_concrete run scoreboard players add $stack stack1 0')
    
    for i, color in enumerate(COLORS):
        i += 1
        for _, blockType in NUM_TYPES:
            lines.append(f'execute at @s if block ~ ~ ~ minecraft:{color}_{blockType} run scoreboard players add $stack stack1 {i}')
    
    # Negate if necessary
    lines.append('scoreboard players operation $stack stack1 *= $temp temp2')
    
    # Push back to stack
    lines.append('scoreboard players operation $stack stackin >< $stack stack1')
    lines.append('function craftyfunge:push_stack')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')
    
    writeFile(filename, lines)


def inNumLiteralNeg():
    filename = os.path.join(START_PATH, 'in_num_literal_neg.mcfunction')
    lines = []
    
    # Pop stack
    lines.append('function craftyfunge:pop_stack1')
    
    # Set scoreboard
    lines.append('scoreboard players set $temp temp2 -1')
    
    # Only make negative if the popped number if positive
    lines.append('execute if score $stack stack1 matches 1.. run scoreboard players operation $stack stack1 *= $temp temp2')
    
    # Push back to stack
    lines.append('scoreboard players operation $stack stackin >< $stack stack1')
    lines.append('function craftyfunge:push_stack')
    
    # Reset
    lines.append('scoreboard players set $stack stack1 0')
    
    writeFile(filename, lines)


def initScoreboard():
    filename = os.path.join(START_PATH, 'init_scoreboard.mcfunction')
    lines = []
    
    # Scoreboard
    for i in range(1, STACKS+1):
        lines.append(f'scoreboard objectives add stack{i} dummy')
    
    for i in range(1, TEMPS+1):
        lines.append(f'scoreboard objectives add temp{i} dummy')
    
    for objective in ['stackin', 'stacklen', 'direction', 
                      'numdirs', 'ten', 'minus',
                      'mode', 'changed_mode', 
                      'went_to', 'stepping',
                      'running', 'move_countdown', 'delay'] + list(AXIS_NAMES):
        lines.append(f'scoreboard objectives add {objective} dummy')
    
    lines.append('scoreboard players set $constants numdirs 6')
    lines.append('scoreboard players set $constants ten 10')
    lines.append('scoreboard players set $constants minus -1')
    lines.append('scoreboard players set $ip delay 6')

    # Teams
    for mode in Modes:
        name, color = MODE_NAMES[mode], MODE_COLORS[mode]
        lines.append(f'team add {name}')
        lines.append(f'team modify {name} color {color}')
    
    writeFile(filename, lines)


# Runs all steps
def runStep():
    # Calling function
    filename = os.path.join(START_PATH, 'run_step.mcfunction')
    lines = [f'execute as @e[{FUNGIE}] at @s run function craftyfunge:wrapped/run_step']
    writeFile(filename, lines)
    
    # Wrapped function
    filename = os.path.join(START_PATH, 'wrapped/run_step.mcfunction')
    lines = []
    
    # Reset changed mode
    lines.append('scoreboard players set $ip changed_mode 0')
    
    # Execute each mode
    for mode in Modes:
        # Only evalute if not stopped and mode hasn't already been changed
        if mode != Modes.STOPPED:
            lines.append(f'execute as @s if score $ip mode matches {mode} if score $ip changed_mode matches 0 run function craftyfunge:steps/run_step_{MODE_NAMES[mode]}')
    
    # Move
    lines.append(f'execute unless score $ip direction matches -1 unless score $ip went_to matches 1 run function craftyfunge:move')
    
    # Reset went_to
    lines.append(f'scoreboard players set $ip went_to 0')
    
    # Reset delay
    lines.append('execute if score $ip running matches 1 run scoreboard players operation $ip move_countdown = $ip delay')
    
    writeFile(filename, lines)

    fnNameDict = dict(BLOCKS_TO_FN_NAMES)


    def runStepDefault():
        filename = os.path.join(START_PATH, 'steps/run_step_default.mcfunction')
        lines = []
        
        lines.append('execute as @s at @s if block ~ ~ ~ #craftyfunge:numbers run function craftyfunge:push_number')
        lines.append(f'execute as @s run function craftyfunge:arithmetic')
        lines.append(f'execute as @s run function craftyfunge:comparisons')
        
        for block, functionName in BLOCKS_TO_FN_NAMES:
            lines.append(f'execute as @s at @s if block ~ ~ ~ minecraft:{block} run function craftyfunge:{functionName}')
        
        writeFile(filename, lines)
    runStepDefault()
    

    def runStepTunnel():
        filename = os.path.join(START_PATH, 'steps/run_step_tunnel.mcfunction')
        lines = []
        
        lines.append(f'execute as @s at @s if block ~ ~ ~ minecraft:{TUNNEL} run function craftyfunge:{fnNameDict[TUNNEL]}')
        
        writeFile(filename, lines)
    runStepTunnel()
    
    
    def runStepInNumLiteral():
        filename = os.path.join(START_PATH, 'steps/run_step_in_num_literal.mcfunction')
        lines = []
        
        lines.append(f'execute as @s at @s if block ~ ~ ~ minecraft:{IN_NUM_LITERAL} run function craftyfunge:{fnNameDict[IN_NUM_LITERAL]}')
        lines.append(f'execute as @s at @s if block ~ ~ ~ minecraft:{DIR} run function craftyfunge:{fnNameDict[DIR]}')
        lines.append(f'execute as @s at @s if block ~ ~ ~ #craftyfunge:numbers run function craftyfunge:in_num_literal')
        lines.append(f'execute as @s at @s if block ~ ~ ~ minecraft:{NEG} run function craftyfunge:in_num_literal_neg')
        
        writeFile(filename, lines)
    runStepInNumLiteral()
    
    
    def runStepInStrLiteral():
        filename = os.path.join(START_PATH, 'steps/run_step_in_str_literal.mcfunction')
        lines = []
        
        lines.append(f'execute as @s at @s if block ~ ~ ~ minecraft:{IN_STR_LITERAL} run function craftyfunge:{fnNameDict[IN_STR_LITERAL]}')
        lines.append(f'execute as @s at @s unless block ~ ~ ~ minecraft:{IN_STR_LITERAL} run function craftyfunge:push_curr_block')
        
        writeFile(filename, lines)
    runStepInStrLiteral()


# Uses scoreboard timer to check if the IP should move
def run():
    filename = os.path.join(START_PATH, 'run.mcfunction')
    lines = []
    
    lines.append('execute if score $ip move_countdown matches 1.. run scoreboard players remove $ip move_countdown 1')
    lines.append('execute if score $ip running matches 1 if score $ip move_countdown matches 0 run function craftyfunge:run_step')
    
    writeFile(filename, lines)


def runEverything():
    # Haven't run it yet, if it's bad then manually change badFuncs back to evything not a function
    import types
    funcs = [f for f in globals().values() if type(f) == types.FunctionType]
    badFuncs = [getSelector, writeFile, 
                binaryTeleport, binaryEncode, binaryDecode,
                toggleMode, runEverything] + getBadFuncs()
    for func in badFuncs:
        funcs.remove(func)
    
    for func in funcs:
        func()


