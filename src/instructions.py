# Defines several modes and how their behaviors differ for the instructions
# Copyright 2022 Eli Fox

import math, random, sys
from common import *

VALID_COLORS = BLOCK_TO_PUSHNUM.keys()


# Template
class ModeIsr(object):
    def __init__(self, interp):
        self.interp = interp
        self.stack = interp.stack
    
    # Returns 0 on an empty stack
    def pop(self):
        return self.stack.pop() if len(self.stack) > 0 else 0
    
    def popN(self, n):
        return [self.pop() for _ in range(n)]
    
    # Pushes to the stack
    def push(self, n):
        # Don't push zero onto an empty stack
        if n == 0 and len(self.stack) == 0:
            return
        
        self.stack.append(n)
    
    # Push the block at the pos (x, y, z)
    def pushBlockAtPos(self, x, y, z):
        block = self.interp.getBlock(x, y, z)
        if block in BLOCKS_WITH_EXTRA_DATA:
            if block in ['piston', 'observer']:
                extra = (('facing', self.interp.getFacing(x, y, z)), )
                block = (block, extra)
        
        # Only push if possible to, otherwise do nothing
        if block in BLOCK_TO_VALUE:
            self.push(self.interp.getBlockVal(block))
    
    # Push the current block's value to the stack
    def pushCurrBlock(self):
        self.pushBlockAtPos(*self.interp.pos)
    
    # Arithmetic
    def add(self):
        pass
    
    def sub(self):
        pass
    
    def mult(self):
        pass
    
    def div(self):
        pass
    
    def mod(self):
        pass
    
    def exp(self):
        pass
    
    def neg(self):
        pass
    
    # Logic and comparisons
    def logicalNot(self):
        pass
    
    def greater(self):
        pass
    
    def less(self):
        pass
    
    # Motion
    def changeDir(self):
        pass
    
    def randDir(self):
        pass
    
    def skip(self):
        pass
    
    def skipCond(self):
        pass
    
    # Mode switching
    def tunnel(self):
        pass

    def inNumLiteral(self):
        pass
    
    def inStrLiteral(self):
        pass
    
    # Conditional
    def conditional(self):
        pass
    
    # Stack operations
    def dup(self):
        pass
    
    def popDestroyTop(self):
        pass
    
    def clear(self):
        pass
    
    def swap(self):
        pass
    
    def rotate(self):
        pass
    
    def pushLen(self):
        pass
    
    # Output
    def outNum(self):
        pass
    
    def outAscii(self):
        pass
    
    def outNewline(self):
        pass

    def raiseError(self):
        pass
    
    # Input
    def inNum(self):
        pass
    
    def inAscii(self):
        pass
    
    # Get/set blocks
    def getBlock(self):
        pass

    def setBlock(self):
        pass
    
    # Get/set variables
    def getVar(self):
        pass
    
    def setVar(self):
        pass
    
    # Push pos and Goto
    def pushPos(self):
        pass
    
    def goto(self):
        pass
    
    # End
    def stop(self):
        pass
    
    # Numeric push and next block push
    def pushNum(self):
        pass
    
    def pushNextBlock(self):
        pass
    
    # Running one step
    def runStep(self, block):
        if block == ADD:
            self.add()
        elif block == SUB:
            self.sub()
        elif block == MULT:
            self.mult()
        elif block == DIV:
            self.div()
        elif block == MOD:
            self.mod()
        elif block == EXP:
            self.exp()
        elif block == NEG:
            self.neg()
        elif block == NOT:
            self.logicalNot()
        elif block == GREATER:
            self.greater()
        elif block == LESS:
            self.less()
        elif block == DIR:
            self.changeDir()
        elif block == RANDOM_DIR:
            self.randDir()
        elif block == SKIP:
            self.skip()
        elif block == SKIP_COND:
            self.skipCond()
        elif block == TUNNEL:
            self.tunnel()
        elif block == IN_NUM_LITERAL:
            self.inNumLiteral()
        elif block == IN_STR_LITERAL:
            self.inStrLiteral()
        elif block == IF:
            self.conditional()
        elif block == DUP:
            self.dup()
        elif block == POP:
            self.popDestroyTop()
        elif block == CLEAR:
            self.clear()
        elif block == SWAP:
            self.swap()
        elif block == ROTATE:
            self.rotate()
        elif block == PUSH_LEN:
            self.pushLen()
        elif block == OUT_NUM:
            self.outNum()
        elif block == OUT_ASCII:
            self.outAscii()
        elif block == OUT_NEWLINE:
            self.outNewline()
        elif block == RAISE_ERROR:
            self.raiseError()
        elif block == IN_NUM:
            self.inNum()
        elif block == IN_ASCII:
            self.inAscii()
        elif block == GET_BLOCK:
            self.getBlock()
        elif block == SET_BLOCK:
            self.setBlock()
        elif block == GET_VAR:
            self.getVar()
        elif block == SET_VAR:
            self.setVar()
        elif block == PUSH_POS:
            self.pushPos()
        elif block == GOTO:
            self.goto()
        elif block == PUSH_NEXT_BLOCK:
            self.pushNextBlock()
        elif block in VALID_COLORS:
            self.pushNum()
        elif block == STOP:
            self.stop()


# Default execution mode
class ModeIsrDefault(ModeIsr):
    # Arithmetic
    def add(self):
        popped = self.popN(2)
        self.push(popped[1]+popped[0])
    
    def sub(self):
        popped = self.popN(2)
        self.push(popped[1]-popped[0])
    
    def mult(self):
        popped = self.popN(2)
        self.push(popped[1]*popped[0])
    
    def div(self):
        popped = self.popN(2)
        try:
            self.push(popped[1]//popped[0])
        except ZeroDivisionError:
            self.interp.raiseError('Attempted to divide by zero.')
    
    def mod(self):
        popped = self.popN(2)
        try:
            self.push(popped[1]%popped[0])
        except ZeroDivisionError:
            self.interp.raiseError('Attempted to mod by zero.')
    
    def exp(self): # Can only do positive exponents
        popped = self.popN(2)
        if popped[0] > 1:
            self.push(popped[1]**popped[0])
        else:
            self.push(0)
    
    def neg(self):
        self.push(-self.pop())
    
    # Logic and comparisons
    def logicalNot(self):
        self.push(int(not self.pop()))
    
    def greater(self):
        popped = self.popN(2)
        self.push(int(popped[1]>popped[0]))
    
    def less(self):
        popped = self.popN(2)
        self.push(int(popped[1]<popped[0]))
    
    # Motion
    def changeDir(self):
        self.interp.dir = self.interp.getFacing(*self.interp.pos)
    
    def randDir(self):
        self.interp.dir = random.choice(DIRS)
    
    def skip(self):
        self.interp.move()
    
    def skipCond(self):
        popped = self.pop()
        if popped == 0:
            self.interp.move()
    
    # Mode switching
    def tunnel(self):
        self.interp.mode = Modes.TUNNEL
        self.interp.isr = ModeIsrTunnel(self.interp)
    
    def inNumLiteral(self):
        self.interp.mode = Modes.IN_NUM_LITERAL
        self.interp.isr = ModeIsrInNumLiteral(self.interp)
        
        self.push(0)
        
    def inStrLiteral(self):
        self.interp.mode = Modes.IN_STR_LITERAL
        self.interp.isr = ModeIsrInStrLiteral(self.interp)
    
    # Conditional
    def conditional(self):
        blockFacing = self.interp.getFacing(*self.interp.pos)
        # True goes in same dir as observer
        if self.pop() != 0:
            self.interp.dir = blockFacing
        # False goes in opposite direction as observer
        else:
            self.interp.dir = DIRS_INV[DIRS.index(blockFacing)]
    
    # Stack operations
    def dup(self):
        popped = self.pop()
        self.push(popped)
        self.push(popped)
    
    def popDestroyTop(self):
        self.pop()
    
    def clear(self):
        self.stack.clear()
    
    def swap(self):
        popped = self.popN(2)
        self.push(popped[0])
        self.push(popped[1])
    
    def rotate(self):
        rotateBy = self.pop()
        # If the stack now has length 0 we don't do anything
        if len(self.stack) == 0:
            return
        
        # Forwards makes bottom on top [2 1 2 3 4 5] -> [3 1 2 4 5]
        if rotateBy >= 0:
            index = -rotateBy-1
            # If rotating beyond the size of the stack, it is equivalent to adding a zero.
            # [4 1 2] -> [0 1 2]
            if rotateBy >= len(self.stack):
                self.push(0)
            else:
                rotated = self.stack[index]
                del self.stack[index]
                self.push(rotated)
                # If rotating the end of the stack forwards, we need to destroy all trailing zeros
                if (rotateBy+1) == len(self.stack):
                    while self.stack[0] == 0:
                        self.stack.popleft()
        
        # Backwards makes top on bottom [-2 1 2 3 4 5] -> [2 3 1 4 5]
        else:
            rotateBy = abs(rotateBy)
            rotated = self.pop()
            # If rotating beyond the size of the stack, we have do pad it with zeros
            if rotateBy >= len(self.stack):
                self.stack.extendleft([0]*(rotateBy-len(self.stack)))
                self.stack.appendleft(rotated)
            else:
                self.stack.insert(-rotateBy, rotated)
    
    def pushLen(self):
        if len(self.stack) > 0:
            self.push(len(self.stack))
    
    # Output
    def outNum(self):
        out = str(self.pop()) + ' '
        self.interp.outputStr(out)
    
    def outAscii(self):
        out = chr(self.pop())
        self.interp.outputStr(out)
    
    def outNewline(self):
        self.interp.outputStr('\n')
    
    def raiseError(self):
        self.interp.raiseError('An error was manually raised.')
    
    # Input
    def inNum(self):
        eatenBuffer = []
        # Preceding spaces or newlines gets skipped
        c = self.interp.inputChar()
        # EOF
        if not c:
            self.push(-1)
            return
        
        # Something's there
        eatenBuffer.append(c)
        while c == ' ' or c == '\n':
            c = self.interp.inputChar()
            eatenBuffer.append(c)
        
        # Negative check
        sign = +1
        if c == '-':
            sign = -1
            c = self.interp.inputChar()
            eatenBuffer.append(c)
        
        # Extract digits
        isNum = False
        n = 0
        while c is not None and c.isnumeric():
            isNum = True
            n *= 10
            n += int(c)
            c = self.interp.inputChar()
        n *= sign
        
        # Re-add last character to input
        if not (c is not None and ord(c) != 0):
            self.interp.inputBuffer.appendleft(c)
        
        # If it isn't a number, restore everything and push -1
        if not isNum:
            while eatenBuffer:
                self.interp.inputBuffer.appendleft(eatenBuffer.pop())
            
            self.push(-1)
            return
        
        # Add n to stack
        self.push(n)
    
    def inAscii(self):
        c = self.interp.inputChar()
        if c:
            self.push(ord(c))
        else:
            self.push(-1)
    
    
    # Get/set blocks and goto
    def getBlock(self):
        z, y, x = self.popN(3)
        self.pushBlockAtPos(x, y, z)


    def setBlock(self):
        z, y, x, n = self.popN(4)
        
        # Do nothing if trying to set an invalid value
        if n not in VALUE_TO_BLOCK:
            return
        
        block = VALUE_TO_BLOCK[n]
        # Check for extra data
        if isinstance(block, tuple):
            extra = dict(block[1])
            block = block[0]
        
        blockDict = {'Name':block}
        
        properties = dict()
        # Special properties
        if block.endswith('leaves'):
            properties['persistent'] = True
        # Extra data
        elif block in ['piston', 'observer']:
            properties['facing'] = extra['facing']
        
        if properties:
            blockDict['Properties'] = properties
        
        self.interp.setBlock(x, y, z, blockDict)
    
    
    # Get/set variables
    def getVar(self):
        index = self.pop()
        # Returns value if it exists, else 0
        val = self.interp.vars.get(index, 0)
        self.push(val)
    
    def setVar(self):
        index, val = self.popN(2)
        # Setting a variable to 0 deletes it
        if val == 0:
            if index in self.interp.vars:
                del self.interp.vars[index]
        else:
            self.interp.vars[index] = val
    
    # Push pos and Goto
    def pushPos(self):
        for xyz in range(3):
            self.push(self.interp.pos[xyz])
    
    def goto(self):
        z, y, x = self.popN(3)
        self.interp.pos = [x, y, z]
        self.interp.wentTo = True
    
    # End
    def stop(self):
        self.interp.running = False
    
    # Numeric push and next block push
    def pushNum(self):
        self.push(BLOCK_TO_PUSHNUM[self.interp.block])
    
    def pushNextBlock(self):
        self.interp.move()
        self.pushCurrBlock()


# Tunneler mode
class ModeIsrTunnel(ModeIsr):
    # Mode switching
    def tunnel(self):
        self.interp.mode = Modes.DEFAULT
        self.interp.isr = ModeIsrDefault(self.interp)


# Number literal mode
class ModeIsrInNumLiteral(ModeIsr):
    def __init__(self, interp):
        super().__init__(interp)
        self.sign = +1
    
    # Motion
    def changeDir(self):
        self.interp.dir = self.interp.getFacing(*self.interp.pos)
    
    # Mode switch to default
    def inNumLiteral(self):
        self.interp.mode = Modes.DEFAULT
        self.interp.isr = ModeIsrDefault(self.interp)
        
        self.sign = +1
    
    # Getting number literal
    def pushNum(self):
        # Only push white concrete, not any other type
        if self.interp.block.startswith('white') and not self.interp.block.endswith('concrete'):
            return
        
        # Gets digit part of the number
        digit = BLOCK_TO_PUSHNUM[self.interp.block]
        while digit // 10 > 0:
            digit //= 10
        
        n = abs(self.pop())
        n *= 10
        n += digit
        n *= self.sign

        self.push(n)
    
    # Negation
    def neg(self):
        self.sign = -1
        
        n = abs(self.pop())
        n *= self.sign

        self.push(n)


# Number literal mode
class ModeIsrInStrLiteral(ModeIsr):
    # Mode switch to default, push stack
    def inStrLiteral(self):
        self.interp.mode = Modes.DEFAULT
        self.interp.isr = ModeIsrDefault(self.interp)
    
    # Running one step
    def runStep(self, block):
        if block == IN_STR_LITERAL:
            self.inStrLiteral()
        else:
            self.pushCurrBlock()