import logging
from collections import namedtuple
import ast
import parse

class SemanticError(Exception):
    def __init__(self, error):
        Exception.__init__(self, error)
        self.node = None

    def __str__(self):
        return '%s\nwhile parsing %s' % (self.message, self.node)

class Var(object):
    def __init__(self, name, type, value=None):
        self.name = name
        self.type = type
        self.value = value
        assert name
        assert type, 'Var %r does not have a type' % name
        
    def __str__(self):
        res = '%s: %s' % (self.name, self.type.name)
        if self.value is not None:
            res += ' = %s' % str(self.value)
        return res

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

def Expression(node, namespace):
    if isinstance(node, ast.Call):
        fn = Expression(node.fn, namespace)
        if type(fn.type) != FuncType:
            raise SemanticError('Not a function: %s' % fn)
        args = [Expression(arg, namespace) for arg in node.args]
        return Call(fn, args)
    else:
        return namespace.resolve_term(node)

class Block(object):
    def __init__(self, nodes, context):
        self.namespace = Namespace(context)
        self.statements = []
        self.type = None
        for node in nodes:
            if isinstance(node, ast.Definition):
                definition = self.namespace.add_def(node)
                self.statements.append(definition)
                self.type = None
            else:
                expr = Expression(node, self.namespace)
                self.statements.append(expr)
                self.type = expr.type
                
    def __str__(self):
        return '{\n%s\n}' % '\n'.join('  %s' % str(s) for s in self.statements)
        
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
            arg_types.append(argvar.type)
            self.args.append(argvar)
        self.body = Block(node.body, self.namespace)

        if self.return_type is not None:
            if self.body.type != self.return_type:
                raise SemanticError('Return type mismatch, expected %s, got %s' % (self.return_type, self.body.type))
        
        self.type = FuncType(arg_types, self.return_type)

    def __str__(self):
        return_str = ''
        if self.return_type:
            return_str = ' -> %s' % self.return_type.name
        return 'fn %s(%s)%s %s' % (self.name, ', '.join(map(str, self.args)), return_str, self.body)

class Namespace(object):
    def __init__(self, parent=None):
        self._parent = parent
        self._types = {}
        self._vars = {}
        self._funs = {}
        self._names = {}

    def resolve_term(self, term):
        if term in self._types:
            raise SemanticError('"%s" is a type' % t)
        if term in self._names:
            return self._names[term]
        else:
            for t in self._types.values():
                if isinstance(t, Enum):
                    if term in t.values:
                        return Value(t, term)
        if self._parent:
            return self._parent.resolve_term(term)
        raise SemanticError('Undeclared term: "%s"' % term)

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
                    raise SemanticError('undefined type: %s' % t)
            else:
                return self._names[t]
        else:
            assert False, 'Unexpected type type: %r' % (t,)
                

    def _add_def(self, d):
        if d.name in self._names:
            raise SemanticError('name already defined: %s' % d.name)
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
            raise SemanticError('Type mismatch: expected %s, got %s' % (type, value.type))
        if type is None and value is None:
            raise SemanticError('Unable to determine type')
        if type is None:
            type = value.type
            if type is None:
                raise SemanticError('Cannot assign void value: %s' % str(value))
        var = Var(name, type, value)
        self._names[name] = var
        self._vars[name] = var
        return var

    def add_def(self, d):
        try:
            return self._add_def(d)
        except SemanticError as e:
            e.node = d
            raise

    def __str__(self):
        return '\n'.join(map(str, self._names.values()))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import sys
    for path in sys.argv[1:]:
        content = open(path).read()
        defs = parse.parse(content)
        p = Namespace()
        for d in defs:
            p.add_def(d)
        print p
