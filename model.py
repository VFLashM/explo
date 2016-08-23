import logging
from collections import namedtuple
import ast
import parse
from error import SyntaxError

class ModelError(SyntaxError):
    def __init__(self, error, ast_node):
        self.ast_node = ast_node
        SyntaxError.__init__(self, error)

    def __str__(self):
        return '%s\nwhile parsing: %s\nfrom: %s' % (
            self.message,
            self.ast_node,
            getattr(self.ast_node, 'srcmap', None),
        )

class TypeMismatch(ModelError):
    def __init__(self, expected, got, ast_node):
        ModelError.__init__(self, 'type mismatch', ast_node)
        self.expected = expected
        self.got = got

class AlreadyDefined(ModelError):
    def __init__(self, name, ast_node):
        ModelError.__init__(self, 'already defined', ast_node)
        self.name = name

class Undefined(ModelError):
    def __init__(self, name, ast_node):
        ModelError.__init__(self, 'undefined', ast_node)
        self.name = name

class FatalError(ModelError):
    pass

class KindMismatch(ModelError):
    def __init__(self, name, ast_node):
        ModelError.__init__(self, ast_node, 'kind mismatch')
        self.name = name

        
def check_type_compatible(destination, source, ast_node):
    if destination != source:
        raise TypeMismatch(destination, source, ast_node)

class Node(object):
    def __init__(self, ast_node):
        self.ast_node = ast_node
        
class Var(Node):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.name = ast_node.name
        if ast_node.type is not None:
            self.type = context.resolve_type(ast_node.type)
        else:
            self.type = None

    def __str__(self):
        return 'Var(%s, %s)' % (self.name, self.type.name)

class VarDef(Node):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.var = Var(ast_node, context)
        if ast_node.value:
            self.value = create_expression(ast_node.value, context)
            if self.var.type is None:
                self.var.type = self.value.type
            else:
                check_type_compatible(self.var.type, self.value.type, ast_node)
        else:
            self.value = None
            if self.var.type is None:
                raise ModelError('No type specified', ast_node)
        if ast_node.type:
            self.type = context.resolve_type(ast_node.type)

    def __str__(self):
        return 'VarDef(%s = %s)' % (self.var, self.value)

class Expression(Node):
    def __init__(self, ast_node):
        Node.__init__(self, ast_node)
        self.type = None

class Type(Node):
    def __init__(self, ast_node):
        Node.__init__(self, ast_node)

class EnumValue(Expression):
    def __init__(self, parent, name):
        Expression.__init__(self, parent.ast_node)
        self.type = parent
        self.name = name

    def __str__(self):
        return 'EnumValue(%s)' % self.name

class Enum(Type):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.name = ast_node.name
        self.values = [EnumValue(self, value) for value in ast_node.values]

    def __str__(self):
        return 'Enum(%s, %s)' % (self.name, [v.name for v in self.values])

class FuncType(Type):
    def __init__(self, arg_types, return_type):
        self.arg_types = arg_types
        self.return_type = return_type

class Tuple(Type):
    def __init__(self, members):
        self.members = members

class Call(Expression):
    def __init__(self, ast_node, context):
        self.callee = create_expression(ast_node.callee, context)
        self.args = [create_expression(arg, context) for arg in ast_node.args]
        if not isinstance(self.callee.type, FuncType):
            raise ModelError('Not callable', ast_node)
        if len(self.callee.type.arg_types) != len(self.args):
            raise ModelError('Argument count mismatch', ast_node)
        for exp_type, got_arg in zip(self.callee.type.arg_types, self.args):
            check_type_compatible(exp_type, got_arg.type, ast_node)
        self.type = self.callee.type.return_type

class Assignment(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.destination = context.resolve_term(ast_node.destination, ast_node)
        if not isinstance(self.destination, Var):
            raise ModelError('Destination is not assignable: %s' % self.destination, ast_node)
        self.value = create_expression(ast_node.value, context)
        check_type_compatible(self.destination.type, self.value.type, ast_node)
        
def create_expression(ast_node, context):
    if isinstance(ast_node, ast.Term):
        return context.resolve_term(ast_node.name, ast_node)
    elif isinstance(ast_node, ast.Call):
        return Call(ast_node, context)
    elif isinstance(ast_node, ast.Assignment):
        return Assignment(ast_node, context)
    else:
        raise FatalError('unexpected node', ast_node)

class Function(Node):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.name = ast_node.name
        self.args = [VarDef(arg, context) for arg in ast_node.args]
        if ast_node.return_type:
            self.return_type = context.resolve_type(ast_node.return_type)
        else:
            self.return_type = None
        arg_types = [arg.var.type for arg in self.args]
        self.type = FuncType(arg_types, self.return_type)
        self.body = Block(context)
        for arg in self.args:
            self.body.names.add(arg.var.name)
            self.body.terms[arg.var.name] = arg.var
        for st in ast_node.body:
            self.body.add_statement(st)
        if self.return_type:
            check_type_compatible(self.return_type, self.body.return_type, ast_node)

    def __str__(self):
        return 'Func(%s, %s, %s) %s' % (self.name, map(str, self.args), self.return_type.name if self.return_type else None, self.body)

class Context(object):
    def __init__(self, parent):
        self.parent = parent
        self.types = {}
        self.terms = {}
        self.names = set()

    def resolve_term(self, name, ast_node):
        if name not in self.names:
            if self.parent:
                pres = self.parent.resolve_term(name, ast_node)
                if pres:
                    return pres
            raise Undefined(name, ast_node)
        if name not in self.terms:
            raise KindMismatch(name, ast_node)
        return self.terms[name]

    def resolve_type(self, ast_node):
        if isinstance(ast_node, ast.SimpleType):
            name = ast_node.name
            if name not in self.names:
                if self.parent:
                    pres = self.parent.resolve_type(ast_node)
                    if pres:
                        return pres
                raise Undefined(name, ast_node)
            if name not in self.types:
                raise KindMismatch(name, ast_node)
            return self.types[name]
        elif isinstance(ast_node, ast.Tuple):
            members = [self.resolve_type(member) for member in ast_node.members]
            return Tuple(members)
        else:
            raise FatalError('unexpected node', ast_node)

    def add_term(self, term, ast_node):
        if term.name in self.names:
            raise AlreadyDefined(term.name, ast_node)
        self.names.add(term.name)
        self.terms[term.name] = term

    def add_type(self, type, ast_node, name=None):
        if name is None:
            name = type.name
        if name in self.names:
            raise AlreadyDefined(name, ast_node)
        self.names.add(name)
        self.types[name] = type

    def add_def(self, ast_node):
        if isinstance(ast_node, ast.Enum):
            res = Enum(ast_node, self)
            self.add_type(res, ast_node)
            for value in res.values:
                self.add_term(value, ast_node)
        elif isinstance(ast_node, ast.TypeAlias):
            alias = self.resolve_type(ast_node.target)
            self.add_type(alias, ast_node, ast_node.name)
            res = None
        elif isinstance(ast_node, ast.Var):
            res = VarDef(ast_node, self)
            self.add_term(res.var, ast_node)
            return res
        elif isinstance(ast_node, ast.Func):
            res = Function(ast_node, self)
            self.add_term(res, ast_node)
        else:
            raise FatalError('unexpected node', ast_node)
        return res

class Block(Context):
    def __init__(self, parent):
        Context.__init__(self, parent)
        self.statements = []
        self.return_type = None

    def add_statement(self, ast_node):
        if isinstance(ast_node, ast.Definition):
            res = self.add_def(ast_node)
        else:
            res = create_expression(ast_node, self)
            self.return_type = res.type
        if res is not None:
            self.statements.append(res)

    def __str__(self):
        return 'Block {\n%s\n}' % '\n'.join('\t%s' % st for st in self.statements)

class BuiltinFunction(Function):
    def __init__(self, name, arg_types, return_type, context):
        arg_names = [chr(ord('a') + idx) for idx in range(len(arg_types))]
        arg_ast_nodes = []
        for name, type_name in zip(arg_names, arg_types):
            arg_ast_node = ast.Var(name, ast.SimpleType(type_name))
            arg_ast_nodes.append(arg_ast_node)
        if return_type:
            return_type = ast.SimpleType(return_type)
        ast_node = ast.Func(name, arg_ast_nodes, return_type, [])
        
        Function.__init__(self, ast_node, context)
        self.body = self

class BuiltinType(Type):
    def __init__(self, name):
        self.name = name

class PrintBuiltin(BuiltinFunction):
    def __init__(self, context):
        BuiltinFunction.__init__(self, 'print', ['*'], None, context)

class Builtins(Context):
    def __init__(self):
        Context.__init__(self, None)
        self.add_type(BuiltinType('*'), None)
        self.add_term(PrintBuiltin(self), None)

def build(content):
    statements = parse.parse(content)
    assert statements is not None, 'Parser returned none'
    builtins = Builtins()
    res = Block(builtins)
    for st in statements:
        res.add_statement(st)
    return res

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import sys
    for path in sys.argv[1:]:
        content = open(path).read()
        p = build(content)
        print p
