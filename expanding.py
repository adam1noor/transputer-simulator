import reps
from errors import reportNode
import warnings

#We have a class to warn us when a offset at the end of a prefix needs a prefix of
#it's own
#We stop proccessing in such a case
class OffsetPrefixError(Warning):
	pass
warnings.filterwarnings('always',category = OffsetPrefixError)

'''
We have 2 requirements in this section

1) Expand Double length instructions
2) Expand Operands longer than 4 bits
3) Change all the offsets so that they point to the same instruction
'''

class Expander:
	def __init__(self,trees):
		#Copy over the trees
		self.initTrees= trees
		
		self.initalNumInstructions = trees.numLeaves()
		#While not neccesasry keeping track of current Instructions proccssed is useful for error checking
		self.currentInstruc = 0
		#Initialise the new tree
		self.expanded = self.translateNode(trees)

	def expand(self):
		#We know that all instructions sequences rise to the top after we collapse
		#So we can then check each those individually and check if they match:
		#Single/Prefix
		#Double
		#Chain
		for child in self.initTrees.children:
			#We build every child up first and then append them
			#this allows to retain the instruction sequence that we were given
			if (child.label == 'Chain'):
				newChild = self.expandChain(child)
			elif (child.label == 'Single'):
				newChild = self.expandSingle(child)
			elif (child.label == 'Offset'):
				#We let the jump correcter handle Offset insturctions
				#We do have to create a speical kind of node for offset nodes though
				newChild = self.translateNode(child, offset = True)
				self.currentInstruc +=1
			elif (child.label == 'Double'):
				newChild = self.expandDouble(child)
			else:
				raise AssertionError(f'{child.label} should not be present at expansion stage')
			self.expanded.add(newChild)
		#We do +1 since currentInstruc is 0 indexed
		assert(self.currentInstruc == self.initalNumInstructions), \
		f'Mismatch in number of instructions, Instructions now: {self.currentInstruc}, Insructions before: {self.initalNumInstructions}'
		
		#Set the distances of all the nodes
		self.expanded.generateDistances()
		
		#Attempt to correct all the offsets
		#Assume the code has changed
		self.offsetChanged = True

		#If we don't run into issues while correcting, return the tree
		self.hadError = False
		if self.offsetCorrect():
			return self.expanded
		else:
			return None

	'''
	The next section convers the inital expansion
	'''

	#Chains are built by iterating along them
	def expandChain(self, chainNode):
		newChain = self.translateNode(chainNode)
		#In Prefix Check we only allowed the top node to have an invalid value.
		#So we end up only checking the top value here as well
		topNode = chainNode.children[0]
		expandedNode = self.expandSingle(topNode)
		#If we get a terminal node we know that we have the node we put in
		#and since expandSingle ensures it's a valid chain we know the current chain is valid
		if (expandedNode.terminal):
			newChain.add(expandedNode)
		else:
			for child in expandedNode.children:
				newChain.add(child)
		#Translate and append all the other children
		for i in range(1,chainNode.numChildren()):
			newChild = self.translateNode(chainNode.children[i])
			newChain.add(newChild)
			self.currentInstruc +=1
		return newChain

	#Expands nodes which represent a single length insturction/operand pair
	def expandSingle(self, singleNode):
		#Get the instruction and operand tokens
		instructionToken = singleNode.getInstruc()
		operandToken = singleNode.getOperand()
		operandValue = operandToken.value
		#Do we need to expand?
		if operandValue <16 and operandValue >= 0:
			#We just translate the node we've been given
			result = self.translateNode(singleNode)
		else:
			result = self.generatePrefixSequence(singleNode, operandValue, instructionToken, operandToken)
		self.currentInstruc+=1
		return result

	#GeneratePrefixSequence generates a series of prefixes
	def generatePrefixSequence(self, original, value, instructionToken, operandToken):
		label = original.label
		#The instruction Number we need depends on the kind of node we're given
		#If we're giving a basic Node to expand,
		# the insturction number is euqal to the old distance
		#If we're given a new LabelledNode however the instructionNumber
		#is carried across
		if isinstance(original, reps.LabelledNode):
			instructionNumber = original.instructionNum
		else:
			instructionNumber = original.distance
		#The final instruction in this sequence must match the type of the original instruction
		instrucName = instructionToken.typed.name
		result = reps.LabelledNode('Chain', False, instructionNum = instructionNumber)
		#We obtain the Prefix Sequence we need to generate
		sequence = self.generatePrefixNumbers(value, instructionToken.typed.name)
		#We want to create nodes linked to the Operand for all the prefixes we generate
		for i in range(0,len(sequence)-1):
			#For each PFIX/NFIX instruction, generate tokens that PFIX/Hold the number we're prefixing by
			#and that are linked to the original operand
			part = sequence[i]
			nodeInstruc = self.translateToken(operandToken, part[0])
			nodeOperand = self.translateToken(operandToken, 'NUMBER', part[1])
			#These nodes are prefixing though and we should mark them as such
			node = self.createInstructionNode('Prefix', instructionNumber, nodeInstruc, nodeOperand)
			result.add(node)
		#Finally we create the last node, this has it's instruction linked to the orignal instruction
		#but the operand is linked to the original operand
		lastOperandToken = self.translateToken(operandToken, 'NUMBER' , sequence[-1][1])
		finalNode = self.createInstructionNode(label, instructionNumber, instructionToken, lastOperandToken)
		result.add(finalNode)
		#If we've not prefixed anything just return the final node
		if result.numChildren() == 1:
			result =  result.children[0]
		return result

	#This returns a valid PFIX/NFIX chain that would result in the desiered value,
	#an instruction must be entered to sync with the end of the list
	def generatePrefixNumbers(self, value, instruc):
		#Calculate the remainder first and start the list
		remainder = value & 0xF
		sequence = [(instruc,remainder)]
		if value >= 16:
			#Append the rest of the sequence to the start
			sequence[:0] = self.generatePrefixNumbers(value >> 4, 'PFIX')
		elif value < 0:
			#Append the rest of the sequence to the start
			sequence[:0] = self.generatePrefixNumbers((~value) >> 4, 'NFIX')
		#And finally return the sequence
		return sequence

	#This is expands the case that we have a double length instruction
	def expandDouble(self, doubleNode):
		instructionToken = doubleNode.getInstruc()
		#First we find the instrctionCode
		instrucCode = instructionToken.typed.instructionCode()
		#We want to know how far along the instruction was
		originalDist = doubleNode.distance
		label = doubleNode.label

		#To expand a double length instruction we turn it into a
		#PFIX op0 OPR op1 sequence where op0*16 + op1 is the
		#insturction code of the original instruction
		
		#If op0 is equal to 0 we must ignore the PFIX part and just do the OP
		#Otherwise we must do the PFIX part first and then the OP

		#First check if op0 != 0, in which case we generate the prefix
		if not int(instrucCode[0],16) == 0:
			prefixToken= self.translateToken(instructionToken,'PFIX')
			pOperandToken = self.translateToken(instructionToken,'NUMBER', int(instrucCode[0],16))
			prefixTree = self.createInstructionNode('Prefix', originalDist, prefixToken, pOperandToken)

		#Then we must generate the OPR op1 regardless
		operateToken = self.translateToken(instructionToken,'OPR')
		operateOperandToken = self.translateToken(instructionToken,'NUMBER', int(instrucCode[1],16))
		operateTree = self.createInstructionNode('Single', originalDist, operateToken, operateOperandToken)

		#Check if op0 = 0 (in base 16)
		if int(instrucCode[0],16) == 0:
			#If so we just return the OPR part
			doubleTree = operateTree
		else:
			#Otherwise we should link up PFIX and OPR and return them
			doubleTree = reps.LabelledNode(label, False,instructionNum = originalDist)
			doubleTree.add(prefixTree)
			doubleTree.add(operateTree)
		#We've converted exactly 1 insturction
		self.currentInstruc +=1
		return doubleTree

	'''
	The next section corrects offsets
	'''

	def offsetCorrect(self):
		#It helps to have a list of offset/reference pairs that we need to correct
		offsets = self.findOffsets()
		#We first assume that all offset instructions have length 0
		estimatedOffsetLengths = [0]*len(offsets)
		#If we jump to an instruction that doesn't exist, don't try to adjust the remaining jumps
		if self.hadError:
			return False
		#We do a loop until we haven't changed anything 
		while (self.offsetChanged):
			#We've not changed so far in the loop
			self.offsetChanged = False
			#We use a while loop since it's possible that we delete some jumps
			i = 0
			while i < len(offsets):
				#Update the distances of the tree
				self.expanded.generateDistances()
				self.correct(offsets, estimatedOffsetLengths, i)
				#While it may appear that we can 'skip a node'
				#That node is checked since another loop is called
				i+=1
		return True

	#We find Offsets and the instruction Num that they originally point to
	def findOffsets(self):
		offsets = []
		for child in self.expanded.children:
			#If it's a chain the last node must be an offset instruction
			#Or if it's labelled with offset, it's an offset instruction
			if ((child.label == 'Chain' and child.children[-1].label == 'Offset') or child.label == 'Offset'):
				#Iptr'=NextInst'+Oreg=CurrentInstr+1+Oreg
				requiredInstrucNum = self.buildValue(child)+child.instructionNum+1
				if requiredInstrucNum > self.expanded.maxInstrucNum():
					reportNode(child,"Offset Instruction has invalid value ",OffsetPrefixError)
					self.hadError = True
				offsets.append([child,requiredInstrucNum])
			#If it's not an offset instruction we don't want to do anything
		return offsets

	#This corrects individual jumps/calls
	def correct(self, listOffsets, estimatedLengths, index):
		#offsetNode is the node that contains the jump/call Instruction
		#If it's a chain it does refer ot the start of the chain
		#though the amount we need to jump is determiend from the end of the chain
		offsetNode = listOffsets[index][0]
		
		#destinationNode is the node that the jump/call should point to
		#We call this every time we correct because if we're jumping to a jump
		#It could have moved and we want to jump to the start of its prefix chain
		destinationNode = self.expanded.findInstrucAtNum(listOffsets[index][1])
		#How far we're currently moving
		desiredLink = destinationNode.distance
		currentLink = offsetNode.distance
		#How much we'll have to move given the current estimated offset
		#Movement = 
		estimatedMovement = desiredLink - currentLink - estimatedLengths[index]
		#Note that this == requiredMovement when estimatedLength == realLength

		#This new chain will do that much movement
		operandToken = offsetNode.rightMostEnd().getOperand()
		instrucToken = offsetNode.rightMostEnd().getInstruc()
		newOffset = self.generatePrefixSequence(offsetNode,estimatedMovement,instrucToken,operandToken)
		#And the length of it will be the new expected length
		newEstimatedLength = newOffset.numLeaves()

		#If we're moving to the next instruction delete this node
		if estimatedMovement==1-estimatedLengths[index]:
			#If there is none then the instruction is of the form J (next)
			#In which case we remove this chain altogether
			#Remove from the tree
			self.expanded.replaceChild(offsetNode,None)
			#Remove from list of pairs
			listOffsets.pop(index)
			#Remove from offset Lengths
			estimatedLengths.pop(index)
			self.offsetChanged = True
			#End this check
			return None
		#Otherwise we check to see if we need to adjust the estimated length

		elif not estimatedLengths[index] == newEstimatedLength:
			estimatedLengths[index] = newEstimatedLength
			self.offsetChanged = True
		#Regardless of updating the length we need to update all references to this node
		#With it's better version
		#Update the neccesarry references to the node
		listOffsets[index][0] = newOffset
		self.expanded.replaceChild(offsetNode,newOffset)
	
	'''
	Everything below is a helper method
	'''

	#This returns a new node ready to be annotated with the current distance of the node
	#along with the old node's original distance stored with it
	#we do NOT carry over the nodes children since those should be rebuilt
	def translateNode(self, node, offset = False):
		#For offset nodes we use a slightly different kind of node
		if offset:
			newNode = reps.OffsetZeroNode(node.label, node.terminal, instructionNum = node.distance)
		else:
			newNode = reps.LabelledNode(node.label, node.terminal, instructionNum = node.distance)
		#We would also like to have the node have it's instructions and operands attached
		if node.terminal:
			newNode.setInstruc(node.getInstruc())
			newNode.setOperand(node.getOperand())
		return newNode

	#This creates a node with the given instruction and operandTokens
	def createInstructionNode(self, label, instrucNum, instructionToken, operandToken):
		node = reps.LabelledNode(label, True, 0, instructionNum = instrucNum)
		node.setInstruc(instructionToken)
		node.setOperand(operandToken)
		return node

	#Return a new Token corresponding to an old one
	#We can change type and value value
	#We must not change the text or line/column number it corresponds to
	def translateToken(self, token, typed = None, value = None):
		#If the value isn't changed, change it to typed
		if (value == None):
			value = typed
		typed = reps.TokenType[typed]
		return reps.Token(typed, token.text, value, token.line, token.column)

	#This finds the operand value of a terminal node
	def operandValue(self,node):
		operandToken = node.getOperand()
		operandValue = int(operandToken.value)
		return operandValue

	#We want to calculate the stored value of a potential chain
	def buildValue(self,node):
		value = 0
		#If it's terminal just return the operandValue
		if node.terminal:
			return self.operandValue(node)
		#Otherwise eat through the chain
		for child in node.children:
			operandValue = self.operandValue(child)
			instruc = child.getInstruc().typed.name
			if instruc == 'PFIX':
				value = (value+operandValue) << 4
			elif instruc =='NFIX':
				value = (~value) + operandValue << 4
			else:
				assert(child == node.children[-1]),f'{instruc} Should not be the final node in a chain'
				value = value + operandValue
		return value