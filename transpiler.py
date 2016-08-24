import contextlib
import model
import interpreter

class Flags(object):
    __slots__ = ('in_function', 'in_loop', 'block_output')
    def __init__(self):
        for s in self.__slots__:
            setattr(self, s, False)
        self.block_output = None

class State(object):
    def __init__(self, stream):
        self.indent = 0
        self.stream = stream
        self._newline = True
        self.flags = Flags()
        
    def line(self, s):
        self.string(s)
        self.stream.write('\n')
        self._newline = True

    def string(self, s):
        if self._newline:
            self.stream.write('\t' * self.indent)
            self._newline = False
        else:
            self.stream.write(' ')
        self.stream.write(s)

@contextlib.contextmanager
def flags(state, **kwargs):
    old = {}
    for name, value in kwargs.items():
        assert name in state.flags.__slots__, 'invalid flag: %s' % name
        old[name] = getattr(state.flags, name)
        setattr(state.flags, name, value)
    yield
    for name, value in old.items():
        setattr(state.flags, name, value)

@contextlib.contextmanager
def indent(state):
    state.indent += 1
    yield
    state.indent -= 1

def Node_transpile(self, tstate):
    raise NotImplementedError(type(self))

def Block_transpile(self, tstate, mode='program'):
    tstate.line('{')
    with indent(tstate):
        for idx, st in enumerate(self.statements):
            if idx+1 == len(self.statements):
                if tstate.flags.block_output == True:
                    tstate.string('return')
                elif tstate.flags.block_output:
                    tstate.string(tstate.flags.block_output)
                    tstate.string('=')
            st.transpile(tstate)
            tstate.line(';')
    tstate.line('}')

def Program_transpile(self, tstate):
    tstate.line('#include "builtins.h"')
    for st in self.statements:
        st.transpile(tstate)

def VarDef_transpile(self, tstate):
    if self.var.readonly:
        tstate.string('const')
    self.var.type.transpile(tstate)
    tstate.string(self.var.name)
    if self.value:
        tstate.string('=')
        self.value.transpile(tstate)
    tstate.line(';')
    
def Type_transpile(self, tstate):
    tstate.string(self.name)

def TypeDef_transpile(self, tstate):
    tstate.string('typedef enum')
    tstate.string('{')
    for idx, value in enumerate(self.type.values):
        if idx != 0:
            tstate.string(',')
        tstate.string(value.value)
    if not self.type.values:
        tstate.string('empty')
    tstate.string('}')
    tstate.string(self.type.name)
    tstate.line(';')
    

def Value_transpile(self, tstate):
    if isinstance(self.value, bool):
        tstate.string(str(self.value).lower())
    else:
        tstate.string(str(self.value))

def FuncDef_transpile(self, tstate):
    if self.func.return_type:
        self.func.return_type.transpile(tstate)
    else:
        tstate.string('void')
    tstate.string(self.func.name)
    tstate.string('(')
    for idx, arg in enumerate(self.func.args):
        if idx != 0:
            tstate.string(',')
        arg.var.type.transpile(tstate)
        tstate.string(arg.var.name)
    tstate.string(')')
    with flags(tstate, in_function=True):
        self.func.body.transpile(tstate)

def Var_transpile(self, tstate):
    tstate.string(self.name)

def While_transpile(self, tstate):
    tstate.string('while (')
    self.condition.transpile(tstate)
    tstate.string(')')
    with flags(tstate, in_loop=True):
        self.body.transpile(tstate)
    
def If_transpile(self, tstate):
    tstate.string('if (')
    self.condition.transpile(tstate)
    tstate.string(')')
    self.on_true.transpile(tstate)
    if self.on_false:
        tstate.string('else')
        self.on_false.transpile(tstate)

def Call_transpile(self, tstate):
    self.callee.transpile(tstate)
    tstate.string('(')
    for idx, arg in enumerate(self.args):
        if idx != 0:
            tstate.string(',')
        arg.transpile(tstate)
    tstate.string(')')

def Assignment_transpile(self, tstate):
    tstate.string(self.destination.name)
    tstate.string('=')
    self.value.transpile(tstate)

def Function_transpile(self, tstate):
    tstate.string(self.name)
    
model.Node.transpile = Node_transpile
model.Block.transpile = Block_transpile
model.VarDef.transpile = VarDef_transpile
model.Type.transpile = Type_transpile
model.TypeDef.transpile = TypeDef_transpile
model.Value.transpile = Value_transpile
model.Program.transpile = Program_transpile
model.FuncDef.transpile = FuncDef_transpile
model.Var.transpile = Var_transpile
model.While.transpile = While_transpile
model.If.transpile = If_transpile
model.Call.transpile = Call_transpile
model.Assignment.transpile = Assignment_transpile
model.Function.transpile = Function_transpile

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()
    
    content = open(args.path).read()

    m = interpreter.build_model(content)
    tstate = State(sys.stdout)
    m.transpile(tstate)
