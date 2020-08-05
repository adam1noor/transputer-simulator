#We want to be to raise runtime warnings.
import warnings
from errors import report
import math

#Should warn users if they do something that isn't supported
class InstructionNotImplemented(Warning):
	pass

#Also raise an error if users if they do something nonsencial that can't be resolved
class RunTimeError(Warning):
	pass

#We use RuntimeWarnings for things that can be resolved but shouldn't happen

import reps

class VM:
	def __init__(self):
		#These represent the internal registers of the transputer as defined in the handbook
		#Where the registers are initally undefined they will defined as such in the VM
		self.Wptr=0
		self.Iptr=0
		self.Areg =None 
		self.Breg =None
		self.Creg =None
		self.Oreg = 0 
		#Though we don't implement Floating point instructions in this instructions set we will
		#Leave the registers in for easier extension.
		self.FA = None
		self.FB = None
		self.FC = None
		#This allows us to keep track of how much of the stack is used.
		self.stackdepth=0
		#And finally we have a representation of the memory of the transputer
		#We simulate a 16 bit transputer
		self.bit = 16
		self.bytesPerWord = int(self.bit/8)
		self.byteSelectLength = math.ceil(math.log(self.bytesPerWord,2))
		self.byteSelectMask = (2**self.byteSelectLength)-1
		#Our memory is arranged into words
		self.memory = [0]*(2**(self.bit))


	#This is how commands are processed by the VM and is the only way to interact with it,
	#We do this to ensure that this interpreter is as faithful as possible to the spec
	def run(self,trees):
		#We also want to be able to raise errors and Halt just as the transputer would
		#We reset our errors and Iptr whenever we receieve a new set of commands
		self.haltFlag = False
		self.error = False
		self.Iptr = 0
		#We take in the trees we've generated and convert them to byte codes
		instructions = self.getInstructionOperand(trees)
		while self.Iptr < len(instructions) and not self.haltFlag and not self.error:
			currentInstrucPair = instructions[self.Iptr]
			#We use instruction names for clarity
			#We also store globally since methods can call errors
			self.currentInstruc = currentInstrucPair[0]
			self.currentOperand = int(currentInstrucPair[1].value)
			self.line = self.currentInstruc.line
			self.column = self.currentInstruc.column
			#We first load the operand into the Oreg
			self.Oreg += self.currentOperand
			#And then we run whatever is the current Instruction
			self.execute(self.currentInstruc.typed.name)
			print(self.__str__())
			#Finally move forward by 1 instruction
			self.Iptr +=1
			#While each instruction should do this, we do this in the loop
			#Because it's common to every instruction	

	def __str__(self):
		#We want to be able to see what is currently stored inside the Virtual machine.
		#We will only show the contents of the registers for clarity
		return (f'WPTR:{self.Wptr}, IPTR:{self.Iptr}, Areg:{self.Areg}, Breg:{self.Breg}, Creg:{self.Creg}, Oreg:{self.Oreg}')

	#We implment pop and push individually since they are used by near all insturctions
	def pop(self):
		#Pop an item from the stack [A,B,C] and let the user know if it would be invalid.
		result = self.Areg
		self.Areg = self.Breg
		self.Breg = self.Creg
		if self.stackdepth==0:
			report(self.line, self.column,f'{self.currentInstrucName}Stack is empty', RuntimeWarning)
		else:
			self.stackdepth -=1
		return result

	def push(self,new):
		#Push an item on to the stack [A,B,C] and update the depth
		self.Creg=self.Breg
		self.Breg=self.Areg
		self.Areg=new
		if self.stackdepth <3:
			self.stackdepth +=1

	def isValidReg(self,reg,error):
		registerValue = eval('self.'+reg)
		if registerValue == None:
			if error:
				report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg}, {reg} is Empty', RunTimeError)
				self.hadError = True
			else:
				report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg}, {reg} + is Empty', RuntimeWarning)
			return False
		else:
			return True

	#Just so we that we can change to signed easily
	def toSigned(self, num, bits = None):
		if bits == None:
			bits = self.bit
		if num >= 0 and num < 2**(bits-1):
			return num
		elif num < 0 and num >= -2**(bits-1):
			return 2**(bits)+num
		elif num <0:
			return self.toSigned(num + 2**(bits))
		else:
			return self.toSigned(num - 2**(bits))

	def fromSigned(self, num, bits = None):
		if bits == None:
			bits = self.bit
		if num >= 2**(bits-1):
			return num - 2**(bits)
		else:
			return num

	def readByte(self, address):
		address = self.toSigned(address)
		return self.memory[address]

	def writeByte(self,address,num):
		if num == None:
			report(self.line, self.column,f'{num}, Wrote Nothing ', RuntimeWarning)
			return
		address = self.toSigned(address)
		memory[address] = num

	#Reading a Word's value
	def readMem(self, address):
		address = self.toSigned(address)
		if address % self.bytesPerWord == 0:
			i = 0
			result = 0
			while i < self.bytesPerWord:
				result += (self.memory[address+i])*(2**(8*i))
				i+=1
		else:
			report(self.line, self.column,f'At: {self.currentInstrucName}, {address} is not a wordLength Address', RuntimeWarning)
			result = None
		return result

	#Writing a word to memory
	def writeMem(self, address, num):
		address = self.toSigned(address)
		if num == None:
			report(self.line, self.column,f'{num}, Wrote Nothing ', RuntimeWarning)
			return
		#Normalise it to n bits
		num = self.toSigned(num)
		num = self.fromSigned(num)
		if address % self.bytesPerWord == 0:
			i = 0
			while i < self.bytesPerWord - 1:
				#Set it to be the lowest bye
				self.memory[address+i] = num & 0xFF
				num = num >> 8
				i += 1
			self.memory[address+i] = num
		else:
			report(self.line, self.column,f'At: {self.currentInstrucName}, {address} is not a wordLength Address', RuntimeWarning)

	#Run an instruction by name
	def execute(self,name):
		self.currentInstrucName = name
		try:
			eval('self.'+ name +'()')
		#If we can't match that means we've not implemented it yet
		except Warning:
			pass
		except AttributeError:
			message = f'{name} is not yet implemented in the simulator'
			report(self.line, self.column, message, InstructionNotImplemented)
			self.error = True
		except Exception as inst:
			print (inst)

	#We eat the tree in and turn it into instruction/operand pairs
	def getInstructionOperand(self, node):
		code = []
		if node.terminal:
			code.append((node.getInstruc(),node.getOperand()))
		else:
			for child in node.children:
				code += self.getInstructionOperand(child)
		return code

	#Everything below here represents a function in the code
	
	def PFIX(self):
		self.Oreg = self.Oreg << 4

	def NFIX(self):
		self.Oreg = ~self.Oreg <<4

	#This will execute whatever instruction we've built up in Oreg
	def OPR(self):
		if self.Oreg < 0:
			report(self.line, self.column, f'OPR {self.Oreg} is not valid', RunTimeError)
			self.Oreg = 0
			self.haltFlag = True
			return
		instructionCodeToRun = hex(self.Oreg)[2:].upper()
		#If we've only got a single length we add a zero so we can match it correctly
		if len(instructionCodeToRun) == 1:
			instructionCodeToRun ='0'+instructionCodeToRun
		instructionCodeToRun = '#' + instructionCodeToRun
		try:
			instruction = reps.TokenType(instructionCodeToRun).name
			self.execute(instruction)
		except ValueError:
			report(self.line, self.column, f'OPR {self.Oreg} is not valid', RunTimeError)
			self.haltFlag = True
		finally:
			self.Oreg = 0
			return

	def LDC(self):
		self.push(self.Oreg)
		self.Oreg = 0

	def LDL(self):
		value = self.readMem(self.workspace(self.Oreg))
		if value == None:
			report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg}, Loaded Nothing', RuntimeWarning)
		self.push(value)
		self.Oreg = 0

	def STL(self):
		value = self.pop()
		self.writeMem(self.Wptr+self.Oreg*self.bytesPerWord, value)
		self.Oreg = 0

	def LDLP(self):
		value = self.Wptr+self.Oreg*self.bytesPerWord
		self.push(value)
		self.Oreg = 0

	def ADC(self):
		self.Areg += self.Oreg
		if self.Areg > 2**(self.bit-1) -1:
			report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg+self}, Integer Overflow', RunTimeError)
			self.haltFlag = True
		elif self.Areg < -2**(self.bit-1):
			report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg+self}, Integer Underflow', RunTimeError)
			self.haltFlag = True
		self.Oreg = 0

	def EQC(self):
		if self.Areg == self.Oreg:
			self.Areg = 1
		else:
			self.Areg = 0
		self.Oreg = 0

	def J(self):
		self.Iptr += self.Oreg
		self.Oreg = 0

	def CJ(self):
		if self.Areg == 0:
			self.Iptr += self.Oreg
		else:
			self.pop()
		self.Oreg = 0

	def LDNL(self):
		if not self.isValidReg('Areg',True):
			return
		if self.Areg & self.byteSelectMask == 0:
			index = self.Areg + self.bytesPerWord*self.Oreg
			self.Areg = self.readMem(index)
		else:
			report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg}, Loaded Nothing', RuntimeWarning)
		self.Oreg =0

	def STNL(self):
		if not self.isValidReg('Areg',True):
			return
		if self.Areg & self.byteSelectMask == 0:
			movement = self.pop()
			value = self.pop()
			if value == None:
				report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg}, Stored \'None\' ', RuntimeWarning)
			movement = movement + self.Oreg
		self.Oreg = 0

	def LDNLP(self):
		if not self.isValidReg('Areg',True):
			return
		self.areg = self.areg + self.bytesPerWord*self.Oreg
		self.Oreg = 0

	def CALL(self):
		self.Wptr = self.Wptr-4*self.bytesPerWord
		self.writeMem(self.Wptr,self.Iptr)
		self.writeMem(self.Wptr+1*self.bytesPerWord,self.Areg)
		self.writeMem(self.Wptr+2*self.bytesPerWord,self.Breg)
		self.writeMem(self.Wptr+3*self.bytesPerWord,self.Creg)
		self.Areg = self.Iptr + 1
		self.Iptr = self.Iptr + self.Oreg
		self.Oreg = 0

	def ADW(self):
		self.Wptr = self.Wptr + self.bytesPerWord*self.Oreg
		self.Oreg = 0

	'''
	While not every instruction has been implemented all single length ones have
	A few double length instructions will be implemented
	'''
	def REV(self):

		self.Areg, self.Breg = self.Breg, self.Areg

	def ADD(self):
		if not self.isValidReg('Areg',True):
			return
		if not self.isValidReg('Breg',True):
			return
		value = self.pop()
		self.Areg += value
		if self.Areg > 2**(self.bit-1) -1:
			report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg+self}, Integer Overflow', RunTimeError)
			self.haltFlag = True
		elif self.Areg < -2**(self.bit-1):
			report(self.line, self.column,f'At: {self.currentInstrucName} {self.Oreg+self}, Integer Underflow', RunTimeError)
			self.haltFlag = True