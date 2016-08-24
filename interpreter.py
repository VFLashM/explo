import parse
import model
import builtins
import error

class State(object):
    def __init__(self, parent=None):
        self.parent = parent
        self.values = {}

    def add(self, name):
        assert name not in self.values
        self.values[name] = None

    def __setitem__(self, key, value):
        if key in self.values:
            self.values[key] = value
        elif self.parent:
            self.parent[key] = value
        else:
            assert False, key

    def __getitem__(self, key):
        if key in self.values:
            return self.values[key]
        elif self.parent:
            return self.parent[key]
        else:
            assert False, key

def Node_execute(self, state):
    raise NotImplementedError(type(self))

def Var_execute(self, state):
    res = state[self.name]
    if res is None:
        raise error.InterpreterError('variable not initialized: %s' % self.name)
    return res

def VarDef_execute(self, state):
    if self.value:
        value = self.value.execute(state)
    state.add(self.var.name)
    if self.value:
        state[self.var.name] = value

def Value_execute(self, state):
    return self

def Enum_execute(self, state):
    pass

def Call_execute(self, state):
    callee = self.callee.execute(state)
    args = [a.execute(state) for a in self.args]
    return callee.call(state, args)

def Assignment_execute(self, state):
    value = self.value.execute(state)
    state[self.destination.name] = value

def If_execute(self, state):
    cond = self.condition.execute(state)
    if cond.value:
        return self.on_true.execute(state)
    elif self.on_false:
        return self.on_false.execute(state)

def While_execute(self, state):
    while True:
        cond = self.condition.execute(state)
        if not cond.value:
            break
        self.body.execute(state)

def Function_execute(self, state):
    return self

def FuncDef_execute(self, state):
    pass

def TypeDef_execute(self, state):
    pass

def Function_call(self, state, args):
    fnstate = State(state)
    for avardef, avalue in zip(self.args, args):
        fnstate.add(avardef.var.name)
        fnstate[avardef.var.name] = avalue
    return self.body.execute(fnstate)

def Block_execute(self, state):
    res = None
    for st in self.statements:
        res = st.execute(state)
    return res

model.Node.execute = Node_execute
model.Var.execute = Var_execute
model.VarDef.execute = VarDef_execute
model.Value.execute = Value_execute
model.Enum.execute = Enum_execute
model.Call.execute = Call_execute
model.Assignment.execute = Assignment_execute
model.If.execute = If_execute
model.While.execute = While_execute
model.Function.execute = Function_execute
model.FuncDef.execute = FuncDef_execute
model.TypeDef.execute = TypeDef_execute
model.Function.call = Function_call
model.Block.execute = Block_execute

def build_model(content):
    program = parse.parse(content)
    builtins_context = builtins.Builtins()
    return model.Program(program, builtins_context)

def run_model(m):
    main = m.resolve_term('main', None)
    assert main, 'No main found'

    state = State()
    m.execute(state)
    res = main.call(state, [])
    if res and res.type.name == 'Int':
        return res.value
    else:
        return 0

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()
    
    content = open(args.path).read()

    m = build_model(content)
    rc = run_model(m)
    sys.exit(rc)
