import model
import interpreter

class State(object):
    def __init__(self, stream):
        self.stream = stream
        self._newline = True
        
    def line(self, s):
        self.string(s)
        self.stream.write('\n')
        self._newline = True

    def string(self, s):
        if self._newline:
            self._newline = False
        else:
            self.stream.write(' ')
        self.stream.write(s)

def Node_transpile(self, tstate):
    raise NotImplementedError(type(self))

def Block_transpile(self, tstate, mode='program'):
    tstate.line('{')
    for idx, st in enumerate(self.statements):
        if mode == 'function' and idx+1 == len(self.statements):
            tstate.string('return')
        st.transpile(tstate)
        tstate.line(';')
    tstate.line('}')

def Program_transpile(self, tstate):
    tstate.line('#include "builtins.h"')
    for st in self.statements:
        st.transpile(tstate)

def VarDef_transpile(self, tstate):
    self.var.type.transpile(tstate)
    tstate.string(self.var.name)
    if self.value:
        tstate.string('=')
        self.value.transpile(tstate)
    tstate.line(';')

def Type_transpile(self, tstate):
    tstate.string(self.name)

def Value_transpile(self, tstate):
    tstate.string(str(self.value))

def FuncDef_transpile(self, tstate):
    if self.func.return_type:
        self.func.return_type.transpile(tstate)
    else:
        tstate.string('void')
    tstate.string(self.func.name)
    tstate.string('(')
    tstate.string(')')
    self.func.body.transpile(tstate, 'function')

def Var_transpile(self, tstate):
    tstate.string(self.name)

model.Node.transpile = Node_transpile
model.Block.transpile = Block_transpile
model.VarDef.transpile = VarDef_transpile
model.Type.transpile = Type_transpile
model.Value.transpile = Value_transpile
model.Program.transpile = Program_transpile
model.FuncDef.transpile = FuncDef_transpile
model.Var.transpile = Var_transpile

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    path = sys.argv[1]
    content = open(path).read()

    m = interpreter.build_model(content)
    tstate = State(sys.stdout)
    m.transpile(tstate)
