import reps
import warnings
from errors import report

#We create a specific kinda of error at every part of the interpreter
class LexicalError(Warning):
	pass
warnings.filterwarnings('always',category = LexicalError)

class Scanner:
	def __init__(self,code):
		#We initialise to the state where we have no code and no tokens
		self.tokens = []
		self.code = code
		#Keeps track of the start of the current lexeme
		self.start = 0
		#Keeps track of how charecters through the code we are
		self.current = 0
		#Keeps track of the number of lines we've read
		#And how far through the current line we are
		self.lineno = 1
		self.column = 0
		#It's useful to have the list of instructions
		self.instructList = self.instrucList()
		self.hadError = False;

	#This scans the text for tokens one token at a time
	#Until we reach the end of the code
	def scanTokens(self):
		while not (self.finished()):
			#Match for a token and then update the current start point and column
			self.scanToken()
			self.column += self.current-self.start
			self.start = self.current
		#Finish off by adding an EOF
		self.addToken('EOF', None, 'EOF')
		if (self.hadError):
			return None
		else:
			return self.tokens

	#Are we at the end of the code?
	def finished(self):
		return self.current >= len(self.code)

	#Scan the next token until we're done
	def scanToken(self):
		char = self.advance()
		#If the next charecter is a letter we are only interested
		#in it if it the start of an instruction
		if self.isAlpha(char):
			#Check if the following word is an insturction
			isInstruc = self.isInstruc()
			#If we have an instruction we add it and move on to the next token
			if (isInstruc):
				name = self.code[self.start:self.current]
				self.addToken(name, name)
				return
			#If we don't match here the error is caught at the end of the scan
			#and the token is rejected there

		#If the charecter is a "-" and the one after is a digit, we have a number
		if (char == "-" and self.isDigit(self.peek())):
			self.number()
			return

		#If the next charecter is a digit we make an integer token
		if self.isDigit(char):
			self.number()
			return

		#If we've hit a space or a 	tab then we move onto the next token
		if char == ' ' or char == '\t':
			return

		#If we're at a new line we increment the line counter
		if char == '\n':
			self.addToken('NEXT','NEWLINE',text = 'NEWLINE')
			self.lineno += 1
			self.column = 0
			return

		if char == ';':
			self.addToken('NEXT',';')
			return

		#If nothing matches then we have a lexical error
		#We create the unmatched string and then print it
		unmatched = self.code[self.start:self.current]
		report(self.lineno, self.column, "Unrecognised token: " + unmatched, LexicalError)
		self.hadError = True

	#Text is overrideable but in most cases is left as it is
	def addToken(self, typed, value, text = None):
		#Since python doesn't allowing using self in function defintions we hack around it
		#by initalising text to None
		if (text == None):
			text = self.code[self.start:self.current]
		#We want to turn the type of tokens into proper Token Types
		typed = reps.TokenType[typed]
		self.tokens.append(reps.Token(typed, text, value, self.lineno, self.column))

	'''
	Everything below is a helper method
	'''

	#Move forward by 1 and return the next charecter
	def advance(self):
		#We add the current charecter to the token we're considering
		self.current +=1
		return self.code[self.current - 1]

	#Just return the next charecter
	def peek(self):
		#First we check if we're at the end
		if (self.finished()):
			return None
		#If not we'll return the current charecter
		else:
			return self.code[self.current]

	#This allows us to proccess what Tokens are instructions
	def instrucList(self):
		instrucs = []
		#We only want to include instructions 
		for i in reps.TokenType:
			if i.isInstruction():
				instrucs.append(i.name)
		instrucs = sorted(instrucs, key = len, reverse = True)
		return instrucs

	#We want to check if the following word is an insturction
	def isInstruc(self):
		#Keep going till we have the whole word processed
		while(self.isAlpha(self.peek())):
			self.advance()
		#If it matches an instruction we have a match
		for posIdent in self.instructList:
			if (self.code[self.start:self.current] == posIdent):
				return True
		return False

	#We need this since char can be None and the inbuilt method
	#Only works for strings
	def isAlpha(self,char):
		try:
			return (char.isalpha())
		except:
			return False

	#Checks if a certain charecter can be an integer
	def isDigit(self,char):
		try:
			int(char)
			return True
		except:
			return False

	#We proccess this number until it ends
	def number(self):
		while (self.isDigit(self.peek())):
			self.advance()
		self.addToken('NUMBER',int(self.code[self.start:self.current]))