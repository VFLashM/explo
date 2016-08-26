#!env python2.7
import sys
import contextlib
import model
import interpreter
import error

class InlinerError(error.CompileTimeError):
    def __init__(self, cause):
        self.cause = cause

class Output(object):
    def __init__(self, indent=False):
        self.indent = indent
        self.res = []
        self.newline = True

    def inserter(self, indent=False):
        op = Output(indent)
        self.res.append(op)
        self.newline = True
        return op

    def string(self, s):
        if not s:
            return
        if self.newline:
            self.res.append(s)
            self.newline = False
        else:
            space = True
            first = s[0]
            last = self.res[-1][-1]
            if first in '();,':
                space = False
            if last in '()':
                space = False
            if first == '{' and last == ')':
                space = True
            if space:
                s = ' ' + s
            self.res[-1] += s
        
    def line(self, s):
        self.string(s)
        self.newline = True

    def __str__(self):
        res = '\n'.join(filter(bool, map(str, self.res)))
        if self.indent:
            lines = res.splitlines(True)
            return ''.join('  ' + l for l in lines)
        else:
            return res

class State(object):
    flags = ('in_function', 'in_loop')
    
    def __init__(self):
        for key in self.flags:
            setattr(self, key, False)
        self.temp_idx = 0
        self.istate = interpreter.State()

    def temp_var(self, name, type, output):
        self.temp_idx += 1
        varname = '__%s_%s' % (name, self.temp_idx)

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

def inline(expr, tstate, prelude, body, result):
    if expr.ex_mode == model.ExecutionMode.compile and expr.type is not None:
        try:
            res = expr.execute(tstate.istate)
        except error.InterpreterError as e:
            raise InlinerError(e), None, sys.exc_info()[2]
        res.transpile(tstate, prelude, body, result)
        return True
    return False

def Block_transpile(self, tstate, prelude, body, result):
    if not self.statements:
        if result:
            result.string('unit')
        else:
            body.string('{}')
        return
    if inline(self, tstate, prelude, body, result):
        return True
    if len(self.statements) == 1 and result:
        self.statements[0].transpile(tstate, prelude, body, result)
        return
    if result and self.type:
        outvar = tstate.temp_var('block_result', self.type, prelude)
    else:
        outvar = None

    body.line('{')
    indented = body.inserter(True)
    for idx, st in enumerate(self.statements):
        if idx+1 == len(self.statements) and outvar:
            stpre = indented.inserter()
            stout = indented.inserter()
            indented.string(outvar)
            indented.string('=')
            st.transpile(tstate, stpre, stout, indented)
            indented.line(';')
        else:
            st.transpile(tstate, indented.inserter(), indented.inserter(), None)
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
        inlined = self.value.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
        if self.var.readonly and inlined:
            self.execute(tstate.istate)
    body.line(';')
    
def Type_transpile(self, tstate, prelude, body, result):
    result.string(self.name)

def Tuple_transpile(self, tstate, prelude, body, result):
    if self.members:
        raise NotImplementedError()
    else:
        result.string('Unit')

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
    return True

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
            bodypre = body.inserter(True)
            bodybody = body.inserter(True)
            bodyresult = body.inserter(True)
            bodyresult.string('return')
            self.func.body.transpile(tstate, bodypre, bodybody, bodyresult)
            bodyresult.line(';')
        else:
            self.func.body.transpile(tstate, body.inserter(True), body.inserter(True), None)
    body.line('};')

def Var_transpile(self, tstate, prelude, body, result):
    if inline(self, tstate, prelude, body, result):
        return True
    result.string(self.name)

def While_transpile(self, tstate, prelude, body, result):
    body.string('while (')
    self.condition.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.string(')')
    with tstate.set_flags(in_loop=True):
        self.body.transpile(tstate, prelude, body, None)
    
def If_transpile(self, tstate, prelude, body, result):
    if inline(self, tstate, prelude, body, result):
        return True
    if result and self.type:
        outvar = tstate.temp_var('if_result', self.type, prelude)
    else:
        outvar = None
    body.string('if (')
    self.condition.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.string(') {')
    indented = body.inserter(True)
    if outvar:
        cpre = indented.inserter()
        cbody = indented.inserter()
        indented.string(outvar)
        indented.string('=')
        self.on_true.transpile(tstate, cpre, cbody, indented)
        indented.line(';')
    else:
        self.on_true.transpile(tstate, indented.inserter(), indented.inserter(), None)
    
    if self.on_false:
        body.line('} else {')
        indented = body.inserter(True)
        if outvar:
            cpre = indented.inserter()
            cbody = indented.inserter()
            indented.string(outvar)
            indented.string('=')
            self.on_false.transpile(tstate, cpre, cbody, indented)
            indented.line(';')
        else:
            self.on_false.transpile(tstate, indented.inserter(), indented.inserter(), None)

    body.line('}')
        
    if outvar:
        result.string(outvar)

def Call_transpile(self, tstate, prelude, body, result):
    if inline(self, tstate, prelude, body, result):
        return True
    if result is None:
        result = body
    self.callee.transpile(tstate, prelude.inserter(), prelude.inserter(), result)
    result.string('(')
    for idx, arg in enumerate(self.args):
        if idx != 0:
            result.string(',')
        arg.transpile(tstate, prelude.inserter(), prelude.inserter(), result)
    result.string(')')
    if result == body:
        result.line(';')

def Assignment_transpile(self, tstate, prelude, body, result):
    body.string(self.destination.name)
    body.string('=')
    self.value.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.line(';')

def Function_transpile(self, tstate, prelude, body, result):
    result.string(self.name)
    
model.Node.transpile = Node_transpile
model.Block.transpile = Block_transpile
model.VarDef.transpile = VarDef_transpile
model.Type.transpile = Type_transpile
model.Tuple.transpile = Tuple_transpile
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
