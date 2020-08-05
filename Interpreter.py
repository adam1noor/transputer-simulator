#We will use the inbuilt warnings from python as they do the job fine.
#As we're provding an interpreter we want warnings to show everytime we run into one.
#And we will import the various parts of the interpreter next
from vm import VM
import lexer
import parsing
import prefixChecking
import expanding
#We need this so that we can take in arguments at launch
import sys

#This provides a wrapper for the series of steps executed
class Interpreter:
	def __init__(self):
		#The VM is the only thing that persists throughout running chunks of code
		#The lexer and parser are better off refershing line numbers and such when 
		#made to run on a new chunk of code
		self.vm = VM()
		
	def run(self,code):
		#First we scan for tokens
		scanner = lexer.Scanner(code.upper())
		tokens = scanner.scanTokens()
		#We use None as a way to return Errors
		if (tokens == None):
			print("Lexical error encountered. Not executing")
			return 

		#Next we parse the tokens we've generated into trees
		parser = parsing.Parser(tokens)
		trees = parser.parse()
		if (trees == None):
			print("Parsing error encountered. Not executing")
			return

		#The next section forms a middle end, that changes the not so assembly code so far
		#into proper assembly code that the actual transputer would be able to handle

		#We should check for any prefix errors that may come up and be undetecable
		#at run time after we expand out illegal operands in the expansion step

		prefixChanger= prefixChecking.PrefixPreparer(trees)
		trees = prefixChanger.prepare()
		if (trees == None):
			print("Illegal prefix sequence encountered. Not executing")
			return

		#Then we use an expander to expand out double length instructions
		#And operands longer than 4 bits
		#We also check if there is any overflow when expanding out jumps

		expander = expanding.Expander(trees)
		trees = expander.expand()
		if (trees == None):
			print("Ran into a problem while correcting Jumps. Not executing")
			return
		
		#After this we're ready to interpret!
		self.vm.run(trees)

#This provides a way to read an entire file of assembly code at once
def read_file(filePath):
	#We need to initialse a VM
	interp = Interpreter()
	#Now we load the contents of the flie
	with open(filePath,"r") as f:
		contents = f.read()
	#Get the VM to run it
	interp.run(contents)

#This provides a REPL environment,
def repl():
	#This allows us to properly take input from the user
	#And return it in a way that the interpreter will accept
	def readCode(prompt, followLine):
		response = ""
		line = input(prompt)
		#We check if the user just wants to exit
		if (line == ""):
			return response
		#If not we add the response and move to the next line
		response += line
		while (True):
			line = input(followLine)
			#If nothing is entered we return what we've got so far
			if (line == ""):
				break
			#If it isn't empty add the response on a new line
			response += ("\n" + line)
		return response

	#We need to initialse a VM
	interp = Interpreter()
	#Provide options to end, print or intereact
	print ("Welcome to the REPL \n Please enter instructions as appropriate")
	print ("Type 'print' to print the current state of the VM or press Enter to leave REPL")
	while True:
		instructions = readCode("> "," >")
		if instructions == "":
			break
		elif instructions.upper() == "PRINT":
			print(interp)
		else:
			interp.run(instructions)

def start():
	arguments = sys.argv
	#We offer the user options here according how many arguments are provided
	#The if statement checks if 1 argument is provided and that it has the correct file extension
	#If no argument is provided we enter the REPL environment
	if (len(arguments) == 2) and (len(arguments[1]) > 3) and (arguments[1][-3:] == ".tn"):
		read_file(arguments[1])
	elif (len(arguments)== 1) :
		repl()
	else:
		print("Usage: interpreter.py [file name].tn , or to access the REPL: interpreter.py")

	input("Press Enter to close...")

start()