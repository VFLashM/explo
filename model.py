import logging
from collections import namedtuple
import ast
import parse
from error import SyntaxError

class ModelError(SyntaxError):
    def __init__(self, error):
        Exception.__init__(self, error)
        self.node = None

    def __str__(self):
        return '%s\nwhile parsing %s' % (self.message, self.node)

Var = namedtuple('Var', ['name', 'type'])
VarDef = namedtuple('VarDef', ['var', 'value'])
        
Value = namedtuple('Value', ['type', 'value'])
Value.__str__ = lambda self: '%s: %s' % (self.value, self.type.name)
Call = namedtuple('Call', ['fn', 'args'])
Call.type = property(lambda self: self.fn.type.return_type)
Call.__str__ = lambda self: 'Call(%s, %s)' % (self.fn.name if isinstance(self.fn, Function) else self.fn, map(str, self.args))

Enum = namedtuple('Enum', ['name', 'values'])
FuncType = namedtuple('FuncType', ['args_types', 'return_type'])

Tuple = namedtuple('TupleBase', ['types'])
Tuple.name = property(lambda self: '(%s)' % ', '.join(t.name for t in self.types))
Tuple.__str__ = lambda self: 'Tuple%s' % self.name

Assignment = namedtuple('Assignment', ['var', 'value'])
Assignment.__str__ = lambda self: '%s = %s' % (self.var.name, self.value)

def Expression(node, namespace):
    if isinstance(node, ast.Call):
        fn = Expression(node.fn, namespace)
        if type(fn.type) != FuncType:
            raise ModelError('Not a function: %s' % fn)
        args = [Expression(arg, namespace) for arg in node.args]
        return Call(fn, args)
    else:
        return namespace.resolve_term(node)

def execute(node, state):
    assert node
    if isinstance(node, VarDef):
        state.add(node.var.name, None)
        if node.value:
            state[node.var.name] = execute(node.value, state)
    elif isinstance(node, Enum):
        pass
    elif isinstance(node, (Value, Function, BuiltinFunction)):
        return node
    elif isinstance(node, Var):
        return state[node.name]
    elif isinstance(node, Assignment):
        state[node.var.name] = execute(node.value, state)
    elif isinstance(node, Call):
        fn = execute(node.fn, state)
        args = [execute(a, state) for a in node.args]
        fnstate = State(state)
        for adef, aval in zip(fn.args, args):
            fnstate.add(adef.var.name, aval)
        return fn.body.execute(fnstate)
    else:
        raise NotImplementedError(repr(node))

class Block(object):
    def __init__(self, nodes, context):
        self.namespace = Namespace(context)
        self.statements = []
        self.type = None
        for node in nodes:
            if isinstance(node, ast.Definition):
                definition = self.namespace.add_def(node)
                if definition:
                    self.statements.append(definition)
                self.type = None
            elif isinstance(node, ast.Assignment):
                expr = Expression(node.value, self.namespace)
                var = self.namespace.resolve_term(node.name)
                assignment = Assignment(var, expr)
                self.statements.append(assignment)
            else:
                expr = Expression(node, self.namespace)
                self.statements.append(expr)
                self.type = expr.type
                
    def __str__(self):
        return '{\n%s\n}' % '\n'.join('  %s' % str(s) for s in self.statements)

    def execute(self, state):
        res = None
        for statement in self.statements:
            res = execute(statement, state)
        return res

    def call(self, state, fn):
        func = self.namespace.resolve_term(fn)
        assert isinstance(func, Function)
        assert not func.args
        return func.body.execute(state)

BuiltinFunction = namedtuple('BuiltinFunction', ['name', 'args', 'return_type', 'body', 'type'])
        
class Function(object):
    def __init__(self, node, context):
        self.name = node.name
        self.args = []
        
        self.return_type = None
        if node.return_type:
            self.return_type = context.resolve_type(node.return_type)

        arg_types = []
        self.namespace = Namespace(context)
        for arg in node.args:
            argvar = self.namespace.add_var(arg.name, arg.type)
            arg_types.append(argvar.var.type)
            self.args.append(argvar)
        self.body = Block(node.body, self.namespace)

        if self.return_type is not None:
            if self.body.type != self.return_type:
                raise ModelError('Return type mismatch, expected %s, got %s' % (self.return_type, self.body.type))
        
        self.type = FuncType(arg_types, self.return_type)

    def __str__(self):
        return_str = ''
        if self.return_type:
            return_str = ' -> %s' % self.return_type.name
        return 'fn %s(%s)%s %s' % (self.name, ', '.join(map(str, self.args)), return_str, self.body)

class State(object):
    def __init__(self, parent=None):
        self._parent = parent
        self._values = {}

    def add(self, key, value):
        assert not key in self._values, 'duplicate: %s' % key
        self._values[key] = value

    def __getitem__(self, key):
        if key in self._values:
            return self._values[key]
        else:
            return self._parent[key]

    def __setitem__(self, key, value):
        if key in self._values:
            self._values[key] = value
        else:
            self._parent[key] = value

class Namespace(object):
    def __init__(self, parent=None):
        self._parent = parent
        self._types = {}
        self._vars = {}
        self._funs = {}
        self._names = {}

    def resolve_term(self, term):
        if term in self._types:
            raise ModelError('"%s" is a type' % t)
        if term in self._names:
            return self._names[term]
        else:
            for t in self._types.values():
                if isinstance(t, Enum):
                    if term in t.values:
                        return Value(t, term)
        if self._parent:
            return self._parent.resolve_term(term)
        raise ModelError('Undeclared term: "%s"' % term)

    def resolve_type(self, t):
        if isinstance(t, list):
            t = map(self.resolve_type, t)
            res = Tuple(t)
            if res.name not in self._types:
                self._types[res.name] = res
            else:
                res = self._types[res.name]
            return res
        elif isinstance(t, basestring):
            if not t in self._names:
                if self._parent:
                    return self._parent.resolve_type(t)
                else:
                    raise ModelError('undefined type: %s' % t)
            else:
                return self._names[t]
        else:
            assert False, 'Unexpected type type: %r' % (t,)

    def _add_def(self, d):
        if d.name in self._names:
            raise ModelError('name already defined: %s' % d.name)
        if type(d) == ast.Enum:
            enum = Enum(d.name, d.values)
            self._types[d.name] = enum 
            self._names[d.name] = enum
            return enum
        elif type(d) == ast.TypeAlias:
            self._names[d.name] = self.resolve_type(d.target)
            return None
        elif type(d) == ast.Var:
            return self.add_var(d.name, d.type, d.value)
        elif type(d) == ast.Func:
            f = Function(d, self)
            self._names[d.name] = f
            self._funs[d.name] = f
            return f
        else:
            assert False, 'Unexpected ast node: %s' % (d,)

    def add_var(self, name, type, value=None):
        if value:
            value = Expression(value, self)
        if type is not None:
            type = self.resolve_type(type)
        if value is not None and type is not None and type != value.type:
            raise ModelError('Type mismatch: expected %s, got %s' % (type, value.type))
        if type is None and value is None:
            raise ModelError('Unable to determine type')
        if type is None:
            type = value.type
            if type is None:
                raise ModelError('Cannot assign void value: %s' % str(value))
        var = Var(name, type)
        var_def = VarDef(var, value)
        self._names[name] = var
        self._vars[name] = var
        return var_def

    def add_def(self, d):
        try:
            return self._add_def(d)
        except ModelError as e:
            e.node = d
            raise

    def __str__(self):
        return '\n'.join(map(str, self._names.values()))

class PrintBuiltin(object):
    def execute(self, state):
        print 'PRINT', state['arg'].value

def builtins():
    n = Namespace()
    f = BuiltinFunction('print', [VarDef(Var('arg', None), None)], None, PrintBuiltin(), FuncType([None], None))
    n._funs[f.name] = f
    n._names[f.name] = f
    return n

def build(content):
    defs = parse.parse(content)
    assert defs is not None, 'Parser returned none'
    return Block(defs, builtins())

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import sys
    for path in sys.argv[1:]:
        content = open(path).read()
        defs = parse.parse(content)
        p = Block(defs, builtins())
        print p
        state = State()
        p.execute(state)
        res = p.call(state, 'main')
        if res is not None:
            res = res.value
            assert isinstance(res, (long, int)), 'RC: %r' % (res,)
            sys.exit(res)
