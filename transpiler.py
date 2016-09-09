#!env python2.7
import sys
import contextlib
import model
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
        self.main = None

    def unique_name(self, name):
        self.temp_idx += 1
        return '__%s_%s' % (name, self.temp_idx)

    def temp_var(self, name, type, output):
        varname = self.unique_name(name)

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

def patch(fn):
    tname, mname = fn.__name__.split('_')
    type = getattr(model, tname)
    setattr(type, mname, fn)
    return fn

@patch
def Node_transpile(self, tstate, prelude, body, output):
    raise NotImplementedError(type(self))

@patch
def Builtin_transpile(self, tstate, prelude, body, output):
    output.string(self.name)

@patch
def Block_transpile(self, tstate, prelude, body, result):
    if not self.statements:
        if result:
            result.string('unit')
        else:
            body.string('{}')
        return
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

@patch
def Program_transpile(self, tstate, prelude, body, result):
    prelude.line('#include "builtins.h"')
    for st in self.statements:
        st.transpile(tstate, prelude, body, None)

@patch
def FuncType_transpile(self, tstate, prelude, body, result):
    if not hasattr(self, 'transname'):
        setattr(self, 'transname', tstate.unique_name('Functype'));
        body.string('typedef')
        self.return_type.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
        body.string('(*')
        body.string(self.transname)
        body.string(')(')
        for idx, atype in enumerate(self.arg_types):
            if idx != 0:
                body.string(',')
            atype.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
        body.string(');')
    result.string(self.transname)

@patch
def VarDef_transpile(self, tstate, prelude, body, result):
    if self.readonly:
        body.string('const')
    self.type.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    if self.name == 'main' and self.owner == None:
        setattr(self, 'transname', tstate.unique_name('main'))
        tstate.main = self
    else:
        setattr(self, 'transname', self.name)
    body.string(self.transname)
    if self.value:
        body.string('=')
        inlined = self.value.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.line(';')

@patch
def Enum_transpile(self, tstate, prelude, body, result):
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

@patch
def Value_transpile(self, tstate, prelude, body, result):
    if result:
        if isinstance(self.value, bool):
            result.string(str(self.value).lower())
        else:
            result.string(str(self.value))
    return True

@patch
def Function_transpile(self, tstate, prelude, body, result):
    if not hasattr(self, 'transname'):
        setattr(self, 'transname', tstate.unique_name('function'))
        
        prelude, body = prelude.inserter(), prelude.inserter()
        self.return_type.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
        body.string(self.transname)
        body.string('(')
        for idx, arg in enumerate(self.args):
            if idx != 0:
                body.string(',')
            arg.type.transpile(tstate, prelude, prelude, body)
            body.string(arg.var.name)
        body.string(') {')
        with tstate.set_flags(in_function=True):
            if not model.is_unit_type(self.return_type):
                bodypre = body.inserter(True)
                bodybody = body.inserter(True)
                bodyresult = body.inserter(True)
                bodyresult.string('return')
                self.body.transpile(tstate, bodypre, bodybody, bodyresult)
                bodyresult.line(';')
            else:
                self.body.transpile(tstate, body.inserter(True), body.inserter(True), None)
        body.line('};')
        
    result.string(self.transname)
    

@patch
def VarRef_transpile(self, tstate, prelude, body, result):
    result.string(self.var_def.transname)

@patch
def While_transpile(self, tstate, prelude, body, result):
    body.string('while (')
    self.condition.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.string(')')
    with tstate.set_flags(in_loop=True):
        self.body.transpile(tstate, prelude, body, None)

@patch
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

@patch
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

@patch
def Assignment_transpile(self, tstate, prelude, body, result):
    body.string(self.destination.name)
    body.string('=')
    self.value.transpile(tstate, prelude.inserter(), prelude.inserter(), body)
    body.line(';')

def transpile_model(m):
    tstate = State()
    output = Output()
    m.transpile(tstate, output.inserter(), output.inserter(), None)
    if tstate.main:
        tstate.main.type.return_type.transpile(tstate, output.inserter(), output.inserter(), output)
        output.string('main() { return %s(); }' % tstate.main.transname)
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

    m = model.build_model(content)
    print transpile_model(m)
