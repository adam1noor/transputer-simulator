import reps
import warnings
from errors import reportNode

class PrefixError(Warning):
	pass
warnings.filterwarnings('always',category = PrefixError)

'''
This class checks that all prefix chains are valid.
While doing this we also removes leading PFIX 0 instructions
'''

class PrefixPreparer:
	def __init__(self, trees):
			self.trees = trees
			self.hadError = False

	def prepare(self):
		for sequence in self.trees.children:
			#We're only interested in Chain Nodes
			if sequence.label == 'Chain':
				self.checkChain(sequence, self.trees)
		if self.hadError:
			return None
		else: 
			return self.trees

	def checkChain(self, chain, parent):
		index = 0
		#We iterate through the chain and update it's length as we go
		while (index < chain.numChildren()):
			currentNode = chain.children[index]
			if index == 0:
				if self.uselessPrefix(currentNode):
					del chain.children[index]
				else:
					index +=1			
			else:
				self.checkTerminal(currentNode)
				index +=1
		if chain.numChildren()==1:
			parent.replaceChild(chain,currentNode)

	def uselessPrefix(self,prefixNode):
		#Find the opernad so we can check if it's 0
		operand = self.operandValue(prefixNode)
		#Find the instruction so we can check if it's PFIX
		instruction = prefixNode.getInstruc().typed.name
		#If we have PFIX 0 return True
		if instruction == 'PFIX' and operand == 0:
			return True
		else:
			return False

	def checkTerminal(self,instrucNode):
		validOperand = self.operandValid(instrucNode)
		if not validOperand:
			reportNode(instrucNode, "Invalid prefixing at", PrefixError)
			self.hadError = True

	'''
	Everything below is a helper method
	'''

	def operandValid(self,node):
		#We want to ensure that the operand at a node is in the range 0-15
		operand = self.operandValue(node)
		if operand <16 and operand >= 0:
			return True
		else:
			return False

	def operandValue(self,node):
		operandToken = node.getOperand()
		operandValue = int(operandToken.value)
		return operandValue