import contextlib
import model
import interpreter

class Output(object):
    def __init__(self):
        self.res = []

    def inserter(self):
        op = Output()
        self.res.append(op)
        return op

    def string(self, s):
        self.res.append(s + ' ')
        
    def line(self, s):
        self.res.append(s + '\n')

    def __str__(self):
        return ''.join(map(str, self.res))

class State(object):
    flags = ('in_function', 'in_loop')
    
    def __init__(self):
        for key in self.flags:
            setattr(self, key, False)
        self.temp_idx = 0

    def temp_var(self, type, output):
        self.temp_idx += 1
        varname = 'temp_var_%s' % self.temp_idx

        type.transpile(self, output.inserter(), output.inserter(), output)
        output.string(varname)
        output.line(';')
        
        return varname
        
    @contextlib.contextmanager
    def set_flags(self, **kwargs):
        old = {}
        for name, value in kwargs.items():
            assert name in self.flags, 'invalid flag: %s' % name
            old[name] = getattr(self, name)
            setattr(self, name, value)
        yield
        for name, value in old.items():
            setattr(self, name, value)

def Node_transpile(self, tstate, prelude, body, output):
    raise NotImplementedError(type(self))

def Block_transpile(self, tstate, prelude, body, result):
    if len(self.statements) == 1 and result:
        self.statements[0].transpile(tstate, prelude, body, result)
        return
    if result and self.type:
        outvar = tstate.temp_var(self.type, prelude)
    else:
        outvar = None

    body.line('{')
    for idx, st in enumerate(self.statements):
        if idx+1 == len(self.statements) and outvar:
            stpre = body.inserter()
            stout = body.inserter()
            body.string(outvar)
            body.string('=')
            st.transpile(tstate, stpre, stout, body)
        else:
            st.transpile(tstate, body.inserter(), body.inserter(), None)
        body.line(';')
    body.line('}')

    if outvar:
        result.string(outvar)

def Program_transpile(self, tstate, prelude, body, result):
    prelude.line('#include "builtins.h"')
    for st in self.statements:
        st.transpile(tstate, prelude, body, None)

def VarDef_transpile(self, tstate, prelude, body, result):
    if self.var.readonly:
        body.string('const')
    self.var.type.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.string(self.var.name)
    if self.value:
        body.string('=')
        self.value.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.line(';')
    
def Type_transpile(self, tstate, prelude, body, result):
    result.string(self.name)

def TypeDef_transpile(self, tstate, prelude, body, result):
    body.string('typedef enum')
    body.string('{')
    for idx, value in enumerate(self.type.values):
        if idx != 0:
            body.string(',')
        body.string(value.value)
    if not self.type.values:
        body.string('empty')
    body.string('}')
    body.string(self.type.name)
    body.line(';')

def Value_transpile(self, tstate, prelude, body, result):
    if result:
        if isinstance(self.value, bool):
            result.string(str(self.value).lower())
        else:
            result.string(str(self.value))

def FuncDef_transpile(self, tstate, prelude, body, result):
    if self.func.return_type:
        self.func.return_type.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    else:
        body.string('void')
    body.string(self.func.name)
    body.string('(')
    for idx, arg in enumerate(self.func.args):
        if idx != 0:
            body.string(',')
        arg.var.type.transpile(tstate, prelude, prelude, body)
        body.string(arg.var.name)
    body.string(') {')
    with tstate.set_flags(in_function=True):
        if self.func.return_type:
            bodypre = body.inserter()
            bodybody = body.inserter()
            body.string('return')
            self.func.body.transpile(tstate, bodypre, bodybody, body)
            body.line(';')
        else:
            self.func.body.transpile(tstate, body.inserter(), body.inserter(), None)
    body.line('};')

def Var_transpile(self, tstate, prelude, body, result):
    result.string(self.name)

def While_transpile(self, tstate, prelude, body, result):
    body.string('while (')
    self.condition.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.string(')')
    with tstate.set_flags(in_loop=True):
        self.body.transpile(tstate, prelude, body, None)
    
def If_transpile(self, tstate, prelude, body, result):
    if result and self.type:
        outvar = tstate.temp_var(self.type, prelude)
    else:
        outvar = None
    body.string('if (')
    self.condition.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.string(') {')
    if outvar:
        cpre = body.inserter()
        cbody = body.inserter()
        body.string(outvar)
        body.string('=')
        self.on_true.transpile(tstate, cpre, cbody, body)
    else:
        self.on_true.transpile(tstate, body.inserter(), body.inserter(), None)
    body.line(';')
    
    if self.on_false:
        body.line('} else {')
        if outvar:
            cpre = body.inserter()
            cbody = body.inserter()
            body.string(outvar)
            body.string('=')
            self.on_false.transpile(tstate, cpre, cbody, body)
        else:
            self.on_false.transpile(tstate, body.inserter(), body.inserter(), None)
        body.line(';')

    body.line('}')
        
    if outvar:
        result.string(outvar)

def Call_transpile(self, tstate, prelude, body, result):
    if result is None:
        result = body
    self.callee.transpile(tstate, prelude.inserter(), prelude.inserter(), result)
    result.string('(')
    for idx, arg in enumerate(self.args):
        if idx != 0:
            result.string(',')
        arg.transpile(tstate, prelude.inserter(), prelude.inserter(), result)
    result.string(')')

def Assignment_transpile(self, tstate, prelude, body, result):
    body.string(self.destination.name)
    body.string('=')
    self.value.transpile(tstate, prelude.inserter(), prelude.inserter(), body)

def Function_transpile(self, tstate, prelude, body, result):
    result.string(self.name)
    
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

def transpile_model(m):
    tstate = State()
    output = Output()
    m.transpile(tstate, output.inserter(), output.inserter(), None)
    return str(output)

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
    print transpile_model(m)
