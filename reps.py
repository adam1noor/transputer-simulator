from enum import Enum
import warnings
#We store tokenTypes here since they are used thoughout the program
class TokenType(Enum):
	#We enumerate each insturction with it's code in the instruction set
	#Ordering the insturctions as they're ordered in the insturction set booklet for clarity
	#This will make it easier to implement prefixs later.
	#The first 16 are instrcutions that don't need to be prefixed in
	PFIX = '#2'
	NFIX = '#6'
	OPR = '#F'

	LDC = '#4'
	LDL = '#7'
	STL = '#D'
	LDLP = '#1'

	ADC = '#8'

	EQC = '#C'
	J = '#0'
	CJ = '#A'

	LDNL = '#3'
	STNL = '#E'
	LDNLP = '#5'

	CALL = '#9'
	AJW = '#B'

	#And now we can represent the other instructions
	REV = '#00'
	
	ADD = '#05'
	SUB = '#0C'
	MUL = '#53'
	DIV = '#2C'
	REM = '#1F'

	SUM = '#52'
	DIFF = '#04'
	PROD = '#08'

	AND = '#46'
	OR = '#4B'
	XOR = '#33'
	NOT = '#32'
	SHL = '#41'
	SHR = '#40'

	GT = '#09'

	LEND = '#21'

	BCNT = '#34'
	WCNT = '#3F'

	LDPI = '#1B'
	MINT = '#42'
	BSUB = '#02'
	WSUB = '#0A'

	MOVE = '#4A'
	IN = '#07'

	OUT = '#0B'

	LB = '#01'
	SB = '#3B'
	OUTBYTE = '#0E'
	OUTWORD = '#0F'

	GCALL = '#06'
	GAJW = '#3C'
	RET = '#20'

	STARTP = '#0D'
	ENDP = '#03'

	RUNP = '#39'
	STOPP = '#15'
	LDPRI = '#1E'

	LDTIMER = '#22'
	TIN = '#2B'

	ALT = '#43'
	ALTWT = '#44'
	ALTEND = '#45'
	TALT = '#4E'
	TALTWT = '#51'

	ENBS = '#49'
	DISS = '#30'
	ENBC = '#48'
	DISC = '#2F'
	ENBT = '#47'
	DIST = '#2E'

	CSUB0 = '#13'
	CCNT1 = '#4D'
	TESTERR = '#29'
	STOPERR = '#55'
	SETERR = '#10'

	XWORD = '#3A'
	CWORD = '#56'
	XDBLE = '#1D'
	CSNGL = '#4C'

	LADD = '#16'
	LSUB = '#38'
	LSUM = '#37'
	LDIFF = '#4F'
	LMUL = '#31'
	LDIV = '#1A'

	LSHL = '#36'
	LSHR = '#35'
	NORM = '#19'

	RESETCH = '#12'

	TESTPRANAL ='#2A'

	STHF = '#18'
	STLF = '#1C'
	STTIMER = '#54'
	STHB = '#50'
	STLB = '#17'

	SAVEH = '#3E'
	SAVEL = '#3D'

	CLRHALTERR = '#57'
	SETHALTERR = '#58'
	TESTHALTERR = '#59'

	#And now we can define types for the input which is just an integer
	#We allow the users to enter numbers for ease of use but we will warn them
	#That positive integers are preferred
	NUMBER = 1

	#Also helpful to know when the code has ended
	EOF = 2

	#And we add a marker to differentiate insturctions
	NEXT = 3	

	#Since we've defined each instruction by it's hash code it makes sense
	#That we should be able to check if a Token is an instruction
	def isInstruction(self):
		return not isinstance(self.value,int)

	#It's also helpful to have a function to find the instruction code of the instruction
	#we're representing
	def instructionCode(self):
		assert(self.isInstruction()), f'{self.name} has no instruction code'
		return self.value[1:]

#A token to represent a Instruction/Operand
class Token:
	#Typed represents the type of token which of one of the TokenType above
	#text represents the original text that this token corresponds to
	#value repesents the value that this token currrently corresponds to
	def __init__(self,typed,text,value,line, column):
		self.typed = typed
		self.text = text
		self.value = value
		self.line = line
		self.column = column
	def __str__(self):
		printtype = self.typed.name
		return (f'{self.line}[{self.column}]: {printtype} {self.text} {self.value}')



#A Node that represents a series of instructions that build up
#A terminal Node is a leaf
#A non-terminal Node is a branch
class Node:
	def __init__(self,label,terminal = False,distance = 0):
		self.label = label
		self.instructionToken = None
		self.distance = distance
		self.operandToken = None
		self.children = []
		self.terminal = terminal
		#We want to restrict the labels that a ndoe can take
		assert(['Chain','Single','Double','Prefix','Offset','Statements'].count(label) == 1)

	#Add Leaves
	def add(self,child):
		#Node cannot be terminal AND child must be a node
		assert (not self.terminal), f'{self.label} is terminal'
		assert(isinstance(child,Node)), f'{child} is not a Node'
		self.children.append(child)

	#Set the instruction that this Node represents
	def setInstruc(self,value):
		#Node must be terminal
		assert (self.terminal), (f'{self.label} is not terminal')
		self.instructionToken = value

	#Get the instruction that this Node represents
	def getInstruc(self):
		#Node must have an instruction => Node is terminal
		assert (not self.instructionToken==None), f'{self.label} has no instruction'
		return self.instructionToken

	#Set the operand that this Node represents
	def setOperand(self,value):
		#Node must be terminal AND must have instruction
		assert (self.terminal), (f'{self.label} is not terminal')
		assert (not self.instructionToken==None), f'{self.label} has no instruction'
		self.operandToken = value

	#Get the operand that this Node represents
	def getOperand(self):
		#Node must have an operand => Node is terminal AND Node has an instruction
		assert (not self.operandToken==None), f'{self.label} has no operand'
		return self.operandToken

	#Useful to have the number of leaves in a Node
	def numLeaves(self):
		size = 0
		#If we have data we have an inherent size of 1
		if (not self.instructionToken == None):
			size += 1
		for child in self.children:
			size += child.numLeaves()
		return size

	#Number of children this has
	def numChildren(self):
		return len(self.children)

	#We replace a child in the node with another node
	def replaceChild(self, previous, new = None):
		assert(not self.terminal), f'{self.label} is terminal'
		assert(isinstance(new,Node) or new == None), f'{new} is not a Node'
		try:
			position = self.children.index(previous)
			if new == None:
				self.children.remove(previous)
			else:
				self.children[position] = new
		except:
			raise AssertionError(f'{previous.label} is not a child of {self.label}')

	#We build up the representation of the Node
	def __str__(self, level = 0):
		tabs = '    '*level
		#Initalise to type
		rep = f'{tabs} label: {self.label} [ \n'
		if (not (self.instructionToken==None)):
			rep += f'{tabs} Instruction: {self.instructionToken.value} \n'
			rep += f'{tabs} Instrc#: {self.distance} \n'
			if (not (self.operandToken==None)):
				rep += f'{tabs} Operand: {self.operandToken.value} \n'
		#Now we add the children
		for child in self.children:
			rep += child.__str__(level+1) + '\n'

		rep += tabs + ']'
		return rep

#We use LablledNodes in the expander
#They have a "instructionNum" and a "distance"
#Which track how many instructions away from the start we were in the original
#and far away we are now respectively
class LabelledNode(Node):
	def __init__(self, label, terminal, distance = 0, instructionNum = 0):
		super().__init__(label, terminal, distance)
		self.instructionNum = instructionNum

	#We should only call this on the root, we assume that the tree has been expanded
	def generateDistances(self):
		assert (self.label == 'Statements'), f'Cannot call generateDistances on non root node'
		#Set the root's distance to the distance reached, which is 0
		self.distance = 0
		distance = 0
		for child in self.children:
			distance = child.__generateDistances(distance)
		#Distance in this case == size 

	#This is the actual call on the other nodes
	#It returns the new distance reached
	def __generateDistances(self,distance):
		#Set the distance of this node to the current distance reached
		self.distance = distance
		if self.terminal:
			#If it's terminal increment number of instructions generated by 1
			return distance + 1
		for child in self.children:
			distance = child.__generateDistances(distance)
			#Othewise iterate through the nodes children and generate their distances
		return distance

	def maxInstrucNum(self):
		assert self.label == 'Statements', f'Cannot find max Instruction if not on root'
		return self.__rightMostEndNum(self)

	#This takes in a number and return a link to a terminal node
	#with the lowest distance that has the least instructionNum >= requiredNum 
	def findInstrucAtNum(self, requiredNum):
		assert self.label == 'Statements', f'Cannot find instruction if not on root'
		#The highest numb instruction in the tree is the instruction num of the right most node
		highestInstruction = self.__rightMostEndNum(self)
		#If we're trying to find a non existent Node we should report there is no such node
		if requiredNum > highestInstruction or requiredNum < 0:
			return None
		#Otherwise start the recursive binary search
		#Do a check to ensure that we aren't jumping to an invalid instruction
		return self.__binarySearchNode(requiredNum, self)

	def __binarySearchNode(self,requiredNum,node):
		left = 0
		right = node.numChildren()-1
		#We terminate when the left node and right node are adjacent
		while left < right-1:
			m = (left+right)//2
			#If m has less than the requiredNum
			#We can safely move L to M's position
			if node.children[m].instructionNum < requiredNum:
				left = m
			else:
				right = m
		assert(left == right-1 or left == right)
		leftNode = node.children[left]
		rightNode = node.children[right]
		leftINum = leftNode.instructionNum
		rightINum = rightNode.instructionNum
		#If the requiredNumber is less than or equal to leftmost Node's instructionNum
		#We give back the first instruction we have
		if requiredNum <= leftINum:
			assert(left == 0)
			return self.__leftMostEnd(leftNode)
		#We check if it could be elsewhere in the left branch. In which case we binary
		#search the left branch
		#This implicity checks if leftNode is terminal since otherwise we have an excluded
		#middle. Hence we don't need to check for terminality
		elif requiredNum > leftINum and requiredNum <= self.__rightMostEndNum(leftNode) :
			return self.__binarySearchNode(requiredNum,leftNode)
		#If it's between the highest value of the left branch and the lowest value of the 
		#Right branch the next highest instruction num is the first in the right branch
		elif requiredNum <= rightINum:
			return self.__leftMostEnd(rightNode)
		#The remaining condition is requiredNum > rightINum
		#We should binary search the right branch in this case
		#We can assume that rightNode is not terminal in this case either since we know that
		#This is the rightmost branch in the entire tree and since we limited our check
		#To the highest instruction num in the tree, it must be in this branch somewhere
		else:
			return self.__binarySearchNode(requiredNum,rightNode)

	#This finds the highest initial instruction number in this tree
	def __rightMostEndNum(self,node):
		#The node latest in our children must have the highest value
		result = node
		#We keep going down until we find a terminal node
		while not result.terminal:
			result = result.children[-1]
		return result.instructionNum

	#This finds the right most node in this tree
	def rightMostEnd(self):
		result = self
		#We keep going down until we find a terminal node
		while not result.terminal:
			result = result.children[-1]
		return result

	def __leftMostEnd(self,node):
		result = node
		#Keep going down the first child until you reach a terminal node
		while not result.terminal:
			result = result.children[0]
		return result

	def __str__(self, level = 0):
		tabs = '    '*level
		#Initalise to type
		rep = f'{tabs} label: {self.label} [ \n'
		rep += f'{tabs} CurrentInstrc#: {self.distance} \n'
		rep += f'{tabs} OriginalInstrc#: {self.instructionNum} \n'
		if (not (self.instructionToken==None)):
			rep += f'{tabs} Instruction: {self.instructionToken.value} \n'
			rep += f'{tabs} Original Instruction: {self.instructionToken.text} \n'
			if (not (self.operandToken==None)):
				rep += f'{tabs} Operand: {self.operandToken.value} \n'
		#Now we add the children
		for child in self.children:
			rep += child.__str__(level+1) + '\n'

		rep += tabs + ']'
		return rep

#We use this class when we initailly translate the Offset Nodes. Since we orginally
#estimate they need length 0, it makes sense that we actually set their size to be zero
#when initialised. We do this through changing the distance and size functions that
#They inherit
class OffsetZeroNode(LabelledNode):
	def __init__(self, label, terminal, distance = 0, instructionNum = 0):
		super().__init__(label, terminal, distance, instructionNum)

	#We adjust the generate distances node since this is 
	#How their distances are set
	def __generateDistances(self,distance):
	#Set the distance of this node to the current distance reached
		self.distance = distance
		if self.terminal:
			#Since we don't want to adjust the distance we return the same one in this case
			return distance
		for child in self.children:
			distance = child.__generateDistances(distance)
			#Othewise iterate through the nodes children and generate their distances
		return distance