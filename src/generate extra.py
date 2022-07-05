# Helper functions, either for easier programming or for generating files
# Copyright 2022 Eli Fox

import csv

from common import *


# Get/set blocks
def writeBlockValues():
    blockValues = []
    
    pushableNumBlocks = BLOCK_TO_PUSHNUM.keys()
    
    # Regular and rotate
    for block in BLOCKS_FOR_VALUES:
        blockValues.append(block)
    
    # Add non-functional blocks
    with open('data/all_blocks.txt', 'r') as f:
        for block in f.readlines():
            block = block.strip()
            if not ((block in blockValues) or (block in pushableNumBlocks)) and block not in ('air', 'tinted_glass'):
                blockValues.append(block)
    
    # Dict of number to block
    blockValuesDict = dict()
    extraDataDict = dict()
    totalNumPossible = len(blockValues) + len(BLOCK_TO_PUSHNUM)
    halfLen = int(math.ceil(totalNumPossible/2))
    
    minIn = halfLen-len(blockValues)
    maxIn = halfLen+1
    
    pushableNums = list(BLOCK_TO_PUSHNUM.values())
    
    n = 0
    # Positive values
    for i in range(1, maxIn, +1):
        if i not in pushableNums:
            if blockValues[n] == 'piston':
                extraDataDict[i] = {'facing':'north'}
            elif blockValues[n] == 'observer':
                extraDataDict[i] = {'facing':'south'}
            blockValuesDict[i] = blockValues[n]
            n += 1
    # Negative values
    for i in range(-1, minIn, -1):
        blockValuesDict[i] = blockValues[n]
        n += 1
    
    # Now do pushable number blocks
    for block in BLOCK_TO_PUSHNUM.keys():
        if block != 'white_concrete':
            n = BLOCK_TO_PUSHNUM[block]
            blockValuesDict[n] = block
    
    # Piston and observer
    for direction_i in range(1, 6):
        piston_i = maxIn+direction_i-1
        observer_i = minIn-direction_i+1
        blockValuesDict[piston_i] = 'piston'
        extraDataDict[piston_i] = {'facing': DIRS[direction_i]}
        blockValuesDict[observer_i] = 'observer'
        extraDataDict[observer_i] = {'facing': DIRS_INV[direction_i]}
    
    # Air
    blockValuesDict[0] = 'air'
    # White concrete
    blockValuesDict[MIN_VAL] = 'white_concrete'
    # Tinted glass
    blockValuesDict[MAX_VAL] = 'tinted_glass'
    
    # Write to file
    with open('data/block_to_value.csv', 'w', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        for blockValue in sorted(blockValuesDict.keys()):
            row = [blockValue, blockValuesDict[blockValue]]
            # Adding extra data if applicable
            if blockValue in extraDataDict.keys():
                extraData = extraDataDict[blockValue]
                for key in EXTRA_DATA_ORDER:
                    if key in extraData:
                        row.append(key)
                        row.append(extraData[key])
                        
            writer.writerow(row)

writeBlockValues()


# Make a markdown table of all block values
def writeBlockValueTableDoc(VALUE_TO_BLOCK):
    # Get table of (value, block)
    table = []
    for value in sorted(VALUE_TO_BLOCK.keys()):
        block = getNameFromValue(value)
        block = block.replace('_', ' ')
        block = block.title()
        
        # Add extra information to block
        if getNameFromValue(value) in BLOCKS_WITH_EXTRA_DATA:
            extra = ', '.join(f'{k} {v}' for k,v in VALUE_TO_BLOCK[value][1])
            block = f'{block} ({extra})'
        
        if value == ord('\n'):
            c = 'Newline'
        elif 32 <= value < 127:
            c = chr(value)
            if c == '|': c = '\\|'
            elif c == ' ': c = 'Space'
        else:
            c = ''
        
        table.append((str(value), block, c))
    
    # Header
    joinLine = lambda line: '| ' + ' | '.join(line) + ' |\n'
    table = [
        ('Value', 'Block', 'ASCII Character'),
        ['---']*3
    ] + table
    
    # Write to file
    with open(resourcePath('../doc/block_values.md'), 'w') as f:
        for row in table:
            f.write(joinLine(row))
            
writeBlockValueTableDoc(VALUE_TO_BLOCK)


# Gets the block representation of each character in a string
def strToBlocks(s):
    for c in s:
        print(VALUE_TO_BLOCK[ord(c)])