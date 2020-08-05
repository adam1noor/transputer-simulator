import warnings
import reps

#This is our general purpose reporting function,
#it's mostly used in the parser and lexer
def report(lineno, coloumno, message, errorType):
	#We want to provide an easy way of reporting errors.
	assert issubclass(errorType, Warning), 'Incorrect use of error reporting'
	if issubclass(errorType, RuntimeWarning):
		warnings.warn(f'Warning at line {lineno}[{coloumno}], {message}', errorType)
	else:
		warnings.warn(f'Error at line {lineno}[{coloumno}], {message}', errorType)

#This takes care of reporting a terminal Node and avoiding
#having to manually fetch the relevant lineno and columno
#every time you wish to report and invalid node
def reportNode(node, message, errorType):
	assert (isinstance(node, reps.Node)), 'Cannot reportNode something that isn\'t a node'
	if node.terminal:
		instrucToken = node.getInstruc()
		operandToken = node.getOperand()
		lineno = instrucToken.line
		columno = instrucToken.column
		text = f'{instrucToken.text} {operandToken.text}'
	else:
		lineno = node.children[0].getInstruc().line
		columno = node.children[0].getInstruc().column
		text = ''
		for child in node.children:
			text += f'{child.getInstruc().text} '
			text += f'{child.getOperand().text}'
	warnings.warn(f'Error at line {lineno}[{columno}], {message}: {text}', errorType)
