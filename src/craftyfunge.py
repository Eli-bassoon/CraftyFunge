# The main CraftyFunge interpreter
# Copyright 2022 Eli Fox

from nbt.nbt import NBTFile, TAG_Long, TAG_Int, TAG_String, TAG_List, TAG_Compound
from nbt import nbt, world
from pprint import pprint
import collections, copy
import os, sys

from common import *
from instructions import ModeIsrDefault

STRUCTURE_PATH = 'generated/craftyfunge/structures/'


# Unpack into python format
def unpackNbt(tag):
    if isinstance(tag, TAG_List):
        return [unpackNbt(i) for i in tag.tags]
    
    elif isinstance(tag, TAG_Compound):
        return dict((i.name, unpackNbt(i)) for i in tag.tags)
    
    else:
        return tag.value


# Nicely formatted nested list
def pprintNestedList(L, depth=0):
    space = '\t'*depth
    if isinstance(L, list):
        print(space + '[')
        for e in L:
            pprintNestedList(e, depth=depth+1)
        print(space + '],')
    else:
        print(space + repr(L) + ',')


# Generates list full of None for specified dimensions
def emptyList(dims):
    if len(dims) != 0:
        return [emptyList(dims[1:]) for _ in range(dims[0])]
    else:
        return None


class CraftyFunge():
    def __init__(self, programName, useWorldPath=True, 
                 input=sys.stdin, output=sys.stdout, 
                 debug=False, debugOut=sys.stdout,
                 stack=[]):
        
        self.programName = programName
        self.programFile = CraftyFunge.getProgramFile(programName, useWorldPath)
        self.input = input
        self.output = output
        self.debug = debug
        
        if self.debug:
            self.outputBuffer = []
            self.debugBuffer = []
            self.debugOut = debugOut
            self.steps = 0
        
        self.block = ''
        self.blocks = []
        self.size = [0, 0, 0]
        self.getBlocks()
        
        self.pos = [0, 0, 0]
        self.offset = [0, 0, 0]
        self.dir = 'north'
        self.mode = Modes.DEFAULT
        self.wentTo = False
        self.getStart()
        
        self.stack = collections.deque(stack)
        self.vars = dict()
        
        self.inputBuffer = collections.deque()
        
        self.running = True
        self.isr = ModeIsrDefault(self)
    
    
    # Get the file path to the program
    @staticmethod
    def getProgramFile(programName, useWorldPath):
        # Change to importing from world path if specified
        if useWorldPath:
            START_PATH = os.path.join(WORLD_PATH, STRUCTURE_PATH)
            startPath = START_PATH
        else:
            startPath = ''
        
        # Format file extension if necessary
        if programName.endswith('.nbt'):
            programName = programName[:-4]
        
        return os.path.join(startPath, programName+'.nbt')
    
    
    # Print an error to the 
    def raiseError(self, msg):
        print(f'Error at position {tuple(self.pos)}:', file=sys.stderr)
        print(msg, file=sys.stderr)
        sys.exit(1)
    
    
    # Uses the offset to convert world pos to internal pos, for use in lists
    def getInternalPos(self, x, y, z):
        pos = (x, y, z)
        internalPos = []
        for xyz in range(3):
            internalPos.append(pos[xyz] + self.offset[xyz])
            if (internalPos[xyz] < 0) or (internalPos[xyz] >= self.size[xyz]):
                self.raiseError('Position is out of bounds.')
        
        return internalPos
    
    
    # Reads structure file and gets blocks
    def getBlocks(self):
        # Get structure data
        structure = unpackNbt(NBTFile(self.programFile, 'rb'))

        # Get blocks
        self.size = structure['size']
        self.blocks = emptyList(self.size)
        
        for block in structure['blocks']:
            x, y, z = block['pos']
            
            self.blocks[x][y][z] = copy.deepcopy(structure['palette'][block['state']])
            self.blocks[x][y][z]['Name'] = self.blocks[x][y][z]['Name'][10:] # Chops off "minecraft:"
        
    
    # Gets the type of block at a location
    def getBlock(self, x, y, z):
        x, y, z = self.getInternalPos(x, y, z)
        return self.blocks[x][y][z]['Name']

    
    # Sets a block at a location
    def setBlock(self, x, y, z, block):
        x, y, z = self.getInternalPos(x, y, z)
        self.blocks[x][y][z] = block
    
    
    # Gets the direction the block is facing
    def getFacing(self, x, y, z):
        x, y, z = self.getInternalPos(x, y, z)
        try:
            return self.blocks[x][y][z]['Properties']['facing']
        except KeyError:
            return None
    
    
    # Gets the block value from a block name
    def getBlockVal(self, block):
        return BLOCK_TO_VALUE[block]
    

    # Gets starting location and direction from command block
    def getStart(self):
        for x in range(self.size[0]):
            for y in range(self.size[1]):
                for z in range(self.size[2]):
                    block = self.blocks[x][y][z]['Name']
                    if block == START:
                        self.offset = [x, y, z]
                        self.dir = self.blocks[x][y][z]['Properties']['facing']
                        return


    # Moves one block
    def move(self):
        delta = DIRS_DEL[self.dir]
        for xyz in range(3):
            self.pos[xyz] += delta[xyz]
    
    
    # Reads a character or buffers it
    def inputChar(self):
        # Reads one line into the buffer
        if not self.inputBuffer:
            lineIn = self.input.readline()
            self.inputBuffer = collections.deque(lineIn)
        
        # If there's something in the buffer, we haven't reached EOF
        if self.inputBuffer:
            return self.inputBuffer.popleft()
    
    
    # Outputs a character or several characters
    def outputStr(self, s):
        if self.debug:
            self.debugBuffer.append(f'  Out: {s}')
            self.outputBuffer.append(s)
        else:
            print(s, end='', file=self.output, flush=True)
    
    
    # Executes program
    def run(self):
        while self.running:
            self.block = self.getBlock(*self.pos)
            
            if self.debug:
                initPos = self.pos.copy()
                initBlock = self.block
                self.steps += 1
            
            self.runStep()

            if self.debug:
                stackAsText = ''.join([chr(n) for n in self.stack])
                self.debugBuffer.append(f' Step: {self.steps}')
                self.debugBuffer.append(f'  Pos: {initPos}')
                self.debugBuffer.append(f'Block: {initBlock}')
                self.debugBuffer.append(f'Stack: {list(self.stack)} {repr(stackAsText)}')
                self.debugBuffer.append(f' Vars: {self.vars}')
                
                # See if we have any output
                if len(self.debugBuffer) > 5:
                    out = self.debugBuffer.pop(0)
                    self.debugBuffer.append(out)
                
                print('\n'.join(self.debugBuffer), file=self.debugOut)
                self.debugBuffer = []
                
                print(file=self.debugOut)
            
            # We don't move if we immediately did a goto command
            if not self.wentTo:
                self.move()
            
            self.wentTo = False

        if self.debug:
            print(f'Program terminated in {self.steps} steps.', file=self.debugOut)
            print('Final Output:', file=self.debugOut)
            finalOut = ''.join(self.outputBuffer)
            print(finalOut, file=self.output)
            if self.debugOut != self.output: print(finalOut, file=self.debugOut)
    
    
    # Run one instruction at the current block
    def runStep(self):
        self.isr.runStep(self.block)


# Parse arguments from the command line
def parseArgs():
    import argparse

    parser = argparse.ArgumentParser(description='Run a CraftyFunge program.', prog='craftyfunge', usage='%(prog)s [-h] [--version] [-w] [-d] [-l [DEBUGFILE]] [-s STACK] [-i INFILE] [-o OUTFILE] FILE')
    parser.add_argument('filename', nargs=argparse.REMAINDER, metavar='FILE', help='Which file to run. Must be an nbt file exported from a structure block. File extension not necessary.')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')
    parser.add_argument('-w', dest='useWorldPath', action='store_true', help='Run a file from the configured structure block export location.')
    parser.add_argument('-d', dest='debug', action='store_true', help='Run the program in debug mode, printing the position, block, and stack at each step.')
    parser.add_argument('-l', nargs='?', dest='debugOut', metavar='DEBUGFILE', default=None, const=True, help='Log the debug output separately. Defaults to "debugout.txt".')
    parser.add_argument('-s', '--stack', nargs=1, dest='stack', metavar='STACK', default=[], help='Pre-populate the stack. Input the stack as a comma-separated list of integers surrounded by square brackets with no spaces. Ex. [1,2,3,4,5]')
    parser.add_argument('-i', nargs=1, dest='input', metavar='INFILE', type=argparse.FileType('r'), default=[sys.stdin], help='Take input from INFILE instead of stdin.')
    parser.add_argument('-o', nargs=1, dest='output', metavar='OUTFILE', type=argparse.FileType('w'), default=[sys.stdout], help='Send output to OUTFILE instead of stdout.')

    args = parser.parse_args()
    
    # See if filename got eaten by -l
    if (not args.filename) and isinstance(args.debugOut, str):
        args.filename = [args.debugOut]
        args.debugOut = True
    # See if user actually didn't specify file
    elif not args.filename:
        parser.error('the following arguments are required: FILE')
    
    # Get lists into single arguments
    args.filename = args.filename[0]
    args.input = args.input[0]
    args.output = args.output[0]
    if args.stack: args.stack = args.stack[0]
    
    # Sees if the args are good before trying to process them
    validateProcessArgs(args, parser)
    
    # Handle where to send the debug
    if args.debug:
        # Get default debug out if flag specified but not file
        if args.debugOut == True:
            args.debugOut = open('debugout.txt', 'w')
        # Get debug out if flag and file specified
        elif args.debugOut is not None:
            args.debugOut = open(args.debugOut, 'w')
        # Pipe the debug out to the regular output
        else:
            args.debugOut = args.output
    
    return args


# Validates command line args before processing them
def validateProcessArgs(args, parser):
    # See if stack is valid format
    if args.stack:
        stackError = False
        
        if args.stack[0] != '[' or args.stack[-1] != ']':
            stackError = True
        
        try:
            stack = args.stack[1:-1]
            stack = [int(n) for n in stack.split(',')]
            # Remove trailing zeros
            while stack[0] == 0:
                del stack[0]
            args.stack = stack
        except:
            stackError = True
        
        if stackError:
            parser.error(f'invalid stack "{args.stack}". Must be a comma-separated list of integers surrounded by square brackets with no spaces. Ex. [1,2,3,4,5]')
    
    # If -w is used, see if the world path is configured
    if args.useWorldPath:
        # world.cfg doesn't exist
        if not os.path.isfile(CONFIG_PATH):
            parser.error(f"argument -w: config file 'world.cfg' must exist to use this option")
        
        global WORLD_PATH
        WORLD_PATH = readConfig()
        
        # World path not specified
        if not os.path.isdir(WORLD_PATH):
            parser.error('argument -w: world path must be specified in world.cfg')

    # See if program exists
    programFile = CraftyFunge.getProgramFile(args.filename, args.useWorldPath)
    if not os.path.isfile(programFile):
        parser.error(f"argument FILE: can't open '{args.filename}': [Errno 2] No such file or directory: '{args.filename}'")


if __name__ == '__main__':
    args = parseArgs()
    interp = CraftyFunge(args.filename, args.useWorldPath, 
                         args.input, args.output, 
                         args.debug, args.debugOut,
                         args.stack)
    interp.run()