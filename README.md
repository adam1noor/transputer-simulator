# transputer-simulator
A simulator of the Transputer by Inmos

The simulator as provided is fully operational but unfinished in regards to the instructions implemented. It's designed to be straightforward to add new instructions however.

To use the simulator create a text file, write the code you wish to execute and change the extension of that file to .tn . Then open a shell in the directory containing the simulator and type 

>./python3 Interpreter.py filename.tn

Alternatively a R£PL is available by typing

>./python3 Interpreter.py
