import reps
from errors import report
import warnings

#We define a warning for errors while parsing
class ParsingError(Warning):
	pass
warnings.filterwarnings('always',category = ParsingError)

'''Simple parser since we have the following CFG:
Prog -> stmt Prog | EOF
stmt ->  I | D ( | NEXT)
I -> ( N O I | S O ) ( | NEXT)

Where Stmt represents a sequence building a valid insturction

I Represents building up single legnth insturction/Operand pair
D represents a double length instruction
O represents a single length operand
P represents a prefix instruction
N represents a nfix instruction
S represents a non-preix single length instruction

NEXT represents signalling that we're moving to the next instruction
while it's not necessary we add support for it nonetheless
We will raise an error however if we detect NEXT twice in row, since
this suggests that an operation is misssing

P,O,N,D, NEXT are terminals

The CFG being right recursive makes writing the parser considerably easier as well

Also notice how all Double Instructions and Non-Prefix Instructions can signal that
the Stmt is coming to an end. This is useful for error handling

We leave the issue that Double Instructions might have nothing to run on to the run
time error checking since that's more appropriate.
'''
class Parser:
	def __init__(self,tokens):
		self.tokens = tokens
		#Keep track of how many tokens through we are
		self.current = 0
		#How many instructions we've consumed
		self.distance = 0
		#Intialise the tree that we're retruning
		self.stmts = reps.Node('Statements')
		self.hadError = False
		#We need slightly more advanced error handling here so we specify
		#A error handle for each potential statement
		self.currentStmtError=False

	def parse(self):
		#Keep going till we hit the EOF
		while not (self.atEnd()):
			#Match a stmt
			newStmt = self.buildStmt()
			if newStmt == None:
				#If we have an invalid stmt, don't return it
				break
			else:
				self.stmts.add(newStmt)
		#If we have an error return none
		if (self.hadError):
			return None
		#Otherwise collapse the layers and then return
		else:
			return self.stmts

	#This corresponds to matching the stmt in the CFG
	def buildStmt(self):
		#We have no errors at the start of the stmt
		self.currentStmtError=False
		#Since Stmt doesn't hold any data but instead contains links to other nodes
		#We use peek and not advance
		currentToken = self.peek()
		#If it's a single length insturction we build that up
		if self.isSingleLength(currentToken):
			singleNode = self.buildSingleChain()
			stmt = (singleNode)

		#If it's a double instruction, we build that
		elif self.isDoubleLength(currentToken):
			doubleNode= self.buildDouble()
			stmt = (doubleNode)

		#Otherwise we have a Parser Error for not having an instruction
		else:
			report(currentToken.line, currentToken.column, "Invalid Instruction : " + currentToken.text, ParsingError)
			self.currentStmtError = True
		#If we've had an error in the statement we let our error handler handle it
		if(self.currentStmtError):
			self.hadError = True
			self.errorHandle()
			return
		return stmt

	#This corresponds to matching I in the CFG
	def buildSingleChain(self):
		#First we check what type the next token
		currentToken = self.peek()

		#If we match S O we build that and return
		if not self.isPrefix(currentToken):
			operationNode = self.buildOperation()
			return operationNode

		#If we have a prefix we branch to match (P O) I
		tree = reps.Node('Chain', distance = self.distance)
		while self.isPrefix(currentToken):
			prefixNode = self.buildOperation()
			tree.add(prefixNode)
			currentToken = self.peek()
			
		#This sequence must end with a S O
		if self.isSingleLength(currentToken):
			operationNode = self.buildOperation()
			tree.add(operationNode)
		#If it doesn't end in S O we have an error
		#We check if a relevant error has already been raised. If so we don't raise another error
		elif self.currentStmtError == False:
			report(currentToken.line, currentToken.column, "Not a Single Length Instruction: " + currentToken.text, ParsingError)
			self.currentStmtError= True
		return tree

	#This corresponds to matching N O or P O in the CFG
	#Here we also account for the potential of matching NEXT if needed
	def buildOperation(self):
		#buildOperation consumes the next opeartion token so we use advance here
		operationToken = self.advance()
		#We match the next token with the appropriate type
		if self.isPrefix(operationToken):
			label = 'Prefix'
		elif self.isOffset(operationToken):
			label = 'Offset'
		else:
			label = 'Single'
		node = reps.Node(label, True, self.distance)
		
		operandToken = self.peek()
		#After checking if the following token is a Number we eat it and move on
		if self.isInteger(operandToken):
			self.advance()
			node.setInstruc(operationToken)
			node.setOperand(operandToken)
			self.distance +=1
			#We then check if the next Token is NEXT and if so we just consume it
			self.eatIfNext()
		#If not we have an error and we let the error handler in buildstmt handle it
		else:
			report(operandToken.line, operandToken.column, "Invalid Operand: " + operandToken.text, ParsingError)
			self.currentStmtError = True
		return node

	#This corresponds to matching D in the CFG
	def buildDouble(self):
		#buildDouble consumes input we use advance here
		token = self.advance()
		node = reps.Node('Double', True, self.distance)
		node.setInstruc(token)
		self.distance +=1
		#If the next Token is 'NEXT' we eat it and move on
		self.eatIfNext()
		return node

	#Our error handler eats tokens until we know for sure that we have the start
	#of the next statement
	def errorHandle(self):
		#We continue until we've either handled the error or reached the EOF
		handled = False
		while (not handled):
			#If the next token is the EOF we return and let the parser terminate
			if (self.atEnd()):
				return
			currentToken = self.advance()
			nextToken = self.peek()
			#We've just eatan a NEXT and so the next token is a new statement
			if self.typeOfToken(currentToken) == 'NEXT':
				return
			#We've just eaten a double and so we can go to the next statement safely
			if self.isDoubleLength(currentToken):
				#Eat the following token if it's type is 'NEXT'
				self.eatIfNext()
				return
			#If we reach a single length instruction that isn't a prefix
			if (self.isSingleLength(currentToken) and not self.isPrefix(currentToken)):
				#And the token after is an integer we've matched (N O) which is the other
				#way that STMT can terminate
				if self.isInteger(nextToken):
					#So we eat the next token and move on
					self.advance()
					#Match NEXT if it exists and move on
					self.eatIfNext()
					return

	'''
	Everything below is a helper method
	'''

	#Move to the next token
	def advance(self):
		self.current+=1
		return self.tokens[self.current - 1]

	#Check the next token
	def peek(self):
		return self.tokens[self.current]

	#Check if a token represents an integer
	def isInteger(self,typeToken):
		return(self.typeOfToken(typeToken)=='NUMBER')

	#Return the Instruction/Type a token is
	def typeOfToken(self,token):
		return token.typed.name

	#Check if a Token is a single Length Instruction
	def isSingleLength(self,typeToken):
		isInstruc = typeToken.typed.isInstruction()
		if isInstruc and len(typeToken.typed.instructionCode()) == 1:
			return True
		else:
			return False

	def isDoubleLength(self,typeToken):
		isInstruc = typeToken.typed.isInstruction()
		if isInstruc and len(typeToken.typed.instructionCode()) == 2:
			return True
		else:
			return False

	#Check if a Token is either the PFIX or NFIX instruction
	def isPrefix(self,typeToken):
		instrucType = self.typeOfToken(typeToken)
		return (instrucType == 'PFIX' or instrucType == 'NFIX')

	#Check if a Token is a jump that depends on Oreg
	def isOffset(self,typeToken):
		instrucType = self.typeOfToken(typeToken)
		return (instrucType == 'J' or instrucType == 'CJ' or instrucType == 'CALL')

	#Check if the next Token is of type NEXT and if so eats it
	def eatIfNext(self):
		if self.typeOfToken(self.peek()) == 'NEXT':
				self.advance()

	#Check if we're at the EOF
	def atEnd(self):
		return (self.typeOfToken(self.peek())=='EOF')