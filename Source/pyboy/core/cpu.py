#
# License: See LICENSE file
# GitHub: https://github.com/Baekalfen/PyBoy
#

import array

from . import opcodes

FLAGC, FLAGH, FLAGN, FLAGZ = range(4, 8)
VBLANK, LCDC, TIMER, SERIAL, HIGHTOLOW = range(5)
IF_ADDRESS = 0xFF0F
IE_ADDRESS = 0xFFFF



class CPU:
    def set_bc(self, x):
        assert x <= 0xFFFF, "%0.4x" % x
        self.B = x >> 8
        self.C = x & 0x00FF

    def set_de(self, x):
        assert x <= 0xFFFF, "%0.4x" % x
        self.D = x >> 8
        self.E = x & 0x00FF

    # CPU Flags
    def test_flag(self, flag):
        return (self.F & (1 << flag)) != 0

    def set_flag(self, flag, value=True):
        self.F = (self.F & (0xFF - (1 << flag)))
        if value:
            self.F = (self.F + (1 << flag))

    def clear_flag(self, flag):
        self.F = (self.F & (0xFF - (1 << flag)))

    # Interrupt flags
    def set_interruptflag(self, flag):
        self.mb.setitem(IF_ADDRESS, self.mb.getitem(IF_ADDRESS) | (1 << flag))

    def test_ramregisterflag(self, address, flag):
        v = self.mb.getitem(address)
        return (v & (1 << flag))

    def clear_ramregisterflag(self, address, flag):
        self.mb.setitem(address, (self.mb.getitem(address) & (0xFF - (1 << flag))))

    def test_interrupt(self, if_v, ie_v, flag):
        intr_flag_enabled = (ie_v & (1 << flag))
        intr_flag = (if_v & (1 << flag))

        if intr_flag_enabled and intr_flag:

            # Clear interrupt flag
            self.mb.setitem(
                0xFF0F, self.mb.getitem(0xFF0F) & (0xFF - (1 << flag)))

            self.interrupt_master_enable = False
            if self.halted:
                self.PC += 1 # Escape HALT on return

            self.mb.setitem(self.SP-1, self.PC >> 8) # High
            self.mb.setitem(self.SP-2, self.PC & 0xFF) # Low
            self.SP -= 2

            return True
        return False

    def check_interrupts(self):
        # GPCPUman.pdf p. 40 about priorities
        # If an interrupt occours, the PC is pushed to the stack.
        # It is up to the interrupt routine to return it.
        if not self.interrupt_master_enable:
            return False

        # 0xFF0F (IF_address) - Bit 0-4 Requested interrupts
        if_v = self.mb.getitem(IF_ADDRESS)
        # 0xFFFF (IE_address) - Bit 0-4 Enabling interrupt vectors
        ie_v = self.mb.getitem(IE_ADDRESS)

        # Better to make a long check, than run through 5 if statements
        if ((if_v & 0b11111) & (ie_v & 0b11111)) != 0:
            if self.test_interrupt(if_v, ie_v, VBLANK):
                self.PC = 0x0040
                return True
            elif self.test_interrupt(if_v, ie_v, LCDC):
                self.PC = 0x0048
                return True
            elif self.test_interrupt(if_v, ie_v, TIMER):
                self.PC = 0x0050
                return True
            elif self.test_interrupt(if_v, ie_v, SERIAL):
                self.PC = 0x0058
                return True
            elif self.test_interrupt(if_v, ie_v, HIGHTOLOW):
                self.PC = 0x0060
                return True
        return False

    def f_c(self):
        return (self.F & (1 << FLAGC)) != 0

    def f_h(self):
        return (self.F & (1 << FLAGH)) != 0

    def f_n(self):
        return (self.F & (1 << FLAGN)) != 0

    def f_z(self):
        return (self.F & (1 << FLAGZ)) != 0

    def f_nc(self):
        return (self.F & (1 << FLAGC)) == 0

    def f_nz(self):
        return (self.F & (1 << FLAGZ)) == 0

    def __init__(self, mb, profiling=False):
        self.A = 0
        self.F = 0
        self.B = 0
        self.C = 0
        self.D = 0
        self.E = 0
        self.HL = 0
        self.SP = 0
        self.PC = 0

        self.extraChars = 0
        self.memChange = False
        self.memAddress = 0
        self.memValue = 0
        self.rewindCounter = 0
        self.memCounter = 0
        self.tA = 0
        self.tF = 0
        self.tB = 0
        self.tC = 0
        self.tD = 0
        self.tE = 0
        self.tHL = 0
        self.tSP = 0
        self.tPC = 0
        self.dict = {1: self.A, 2: self.F, 3: self.B, 4: self.C, 5: self.D, 6: self.E, 7: self.HL}
        # Char array to store the registers which have changed
        self.regArray = [[0, 0]] * 3600
        # regArray[0].value, regArray[1].value, SP.value, PC.value, memAddress, memValue
        self.valueArray = [[0, 0, 0, 0, 0, 0]] * 3600


        self.mb = mb

        self.interrupt_master_enable = False

        self.break_allow = True
        self.break_on = False
        self.break_next = 0

        self.halted = False
        self.stopped = False

        # Profiling
        self.profiling = profiling
        if profiling:
            self.hitrate = array.array('L', [0] * 512)

    def save_state(self, f):
        for n in [self.A, self.F, self.B, self.C, self.D, self.E]:
            f.write((n & 0xFF).to_bytes(1, 'little'))

        for n in [self.HL, self.SP, self.PC]:
            f.write((n & 0xFF).to_bytes(1, 'little'))
            f.write(((n & 0xFF00) >> 8).to_bytes(1, 'little'))

        f.write(self.interrupt_master_enable.to_bytes(1, 'little'))
        f.write(self.halted.to_bytes(1, 'little'))
        f.write(self.stopped.to_bytes(1, 'little'))

    def load_state(self, f):
        self.A, self.F, self.B, self.C, self.D, self.E = [ord(f.read(1)) for _ in range(6)]
        self.HL, self.SP, self.PC = [ord(f.read(1)) | (ord(f.read(1)) << 8) for _ in range(3)]

        self.interrupt_master_enable = ord(f.read(1))
        self.halted = ord(f.read(1))
        self.stopped = ord(f.read(1))

    def fetch_and_execute(self, pc):
        opcode = self.mb.getitem(pc)
        if opcode == 0xCB: # Extension code
            pc += 1
            opcode = self.mb.getitem(pc)
            opcode += 0x100 # Internally shifting look-up table

        # Profiling
        if self.profiling:
            self.hitrate[opcode] += 1

        return opcodes.execute_opcode(self, opcode)

    def tick(self):
        # "The interrupt will be acknowledged during opcode fetch
        # period of each instruction."
        did_interrupt = self.check_interrupts()

        if self.halted and did_interrupt:
            # GBCPUman.pdf page 20
            # WARNING: The instruction immediately following the HALT
            # instruction is "skipped" when interrupts are disabled
            # (DI) on the GB,GBP, and SGB.
            self.halted = False
        elif self.halted:
            return -1

        return self.fetch_and_execute(self.PC)

    # #EXTENDED
    def rewindCheck(self):
        self.extraChars = 0
        if self.A != self.tA:
            self.regArray[self.rewindCounter][self.extraChars] = 1          #Saves the register which changed
            self.valueArray[self.rewindCounter][self.extraChars] = self.tA  #Saves the old value of the register
            self.tA = self.A                                                #Updates the value to check against
            self.extraChars = 1
        if self.F != self.tF:
            self.regArray[self.rewindCounter][self.extraChars] = 2          #Saves the register which changed
            self.valueArray[self.rewindCounter][self.extraChars] = self.tF  #Saves the old value of the register
            self.tF = self.F                                                #Updates the value to check against
            self.extraChars = 1
        if self.B != self.tB:
            self.regArray[self.rewindCounter][self.extraChars] = 3          #Saves the register which changed
            self.valueArray[self.rewindCounter][self.extraChars] = self.tB  #Saves the old value of the register
            self.tB = self.B                                                #Updates the value to check against
            self.extraChars = 1
        if self.C != self.tC:
            self.regArray[self.rewindCounter][self.extraChars] = 4          #Saves the register which changed
            self.valueArray[self.rewindCounter][self.extraChars] = self.tC  #Saves the old value of the register
            self.tC = self.C                                                #Updates the value to check against
            self.extraChars = 1
        if self.D != self.tD:
            self.regArray[self.rewindCounter][self.extraChars] = 5          #Saves the register which changed
            self.valueArray[self.rewindCounter][self.extraChars] = self.tD  #Saves the old value of the register
            self.tD = self.D                                                #Updates the value to check against
            self.extraChars = 1
        if self.E != self.tE:
            self.regArray[self.rewindCounter][self.extraChars] = 6          #Saves the register which changed
            self.valueArray[self.rewindCounter][self.extraChars] = self.tE  #Saves the old value of the register
            self.tE = self.E                                                #Updates the value to check against
            self.extraChars = 1
        if self.HL != self.tHL:
            self.regArray[self.rewindCounter][self.extraChars] = 7          #Saves the register which changed
            self.valueArray[self.rewindCounter][self.extraChars] = self.tHL #Saves the old value of the register
            self.tHL = self.HL                                              #Updates the value to check against
            self.extraChars = 1
        self.valueArray[self.rewindCounter][2] = self.tSP                   #Saves the old value of the register
        self.tSP = self.SP                                                  #Updates the value to check against
        self.valueArray[self.rewindCounter][3] = self.tPC                   #Saves the old value of the register
        self.tPC = self.PC                                                  #Updates the value to check against
        if self.memChange == True:
            self.valueArray[self.memCounter][5] = self.memAddress           #Saves the address which changed
            self.valueArray[self.memCounter][4] = self.memValue             #Saves the value which changed
            self.memChange = False
        self.memCounter += 1
        self.rewindCounter += 1
        self.memCounter %= 3600
        self.rewindCounter %= 3600