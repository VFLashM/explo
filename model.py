import ast
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
        ModelError.__init__(self, 'type mismatch %s vs %s' % (expected, got), ast_node)
        self.expected = expected
        self.got = got

class AlreadyDefined(ModelError):
    def __init__(self, name, ast_node):
        ModelError.__init__(self, 'already defined name: %s' % name, ast_node)
        self.name = name

class Undefined(ModelError):
    def __init__(self, name, ast_node):
        ModelError.__init__(self, 'undefined name: %s' % name, ast_node)
        self.name = name

class FatalError(ModelError):
    pass

class KindMismatch(ModelError):
    def __init__(self, name, ast_node):
        ModelError.__init__(self, ast_node, 'kind mismatch')
        self.name = name

class Node(object):
    def __init__(self, ast_node):
        self.ast_node = ast_node
        
class Var(Node):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.name = ast_node.name
        self.readonly = ast_node.readonly
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
                self.var.type.check_assignable_from(self.value.type, ast_node)
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

    def check_assignable_from(self, other, ast_node):
        if self != other:
            raise TypeMismatch(self, other, ast_node)

class Value(Expression):
    def __init__(self, value, type, ast_node):
        Expression.__init__(self, ast_node)
        self.value = value
        self.type = type

    def __str__(self):
        return 'Value(%s, %s)' % (self.value, self.type.name)

class Enum(Type):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.name = ast_node.name
        self.values = [Value(value, self, ast_node) for value in ast_node.values]

    def __str__(self):
        return 'Enum(%s, %s)' % (self.name, [v.value for v in self.values])

class FuncType(Type):
    def __init__(self, arg_types, return_type):
        self.arg_types = arg_types
        self.return_type = return_type

    def __str__(self):
        return 'FuncType(%s, %s)' % (map(str, self.arg_types), self.return_type)

class Tuple(Type):
    def __init__(self, members):
        self.members = members

class Call(Expression):
    def __init__(self, ast_node, context):
        self.callee = create_expression(ast_node.callee, context)
        self.args = [create_expression(arg, context) for arg in ast_node.args]
        if not isinstance(self.callee.type, FuncType):
            print type(self.callee.type), FuncType, isinstance(self.callee.type, FuncType)
            raise ModelError('Not callable: %s' % self.callee.type, ast_node)
        if len(self.callee.type.arg_types) != len(self.args):
            raise ModelError('Argument count mismatch', ast_node)
        for exp_type, got_arg in zip(self.callee.type.arg_types, self.args):
            exp_type.check_assignable_from(got_arg.type, ast_node)
        self.type = self.callee.type.return_type

    def __str__(self):
        return 'Call(%s, %s)' % (self.callee.name, map(str, self.args))

class Assignment(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.destination = context.resolve_term(ast_node.destination, ast_node)
        if not isinstance(self.destination, Var):
            raise ModelError('Destination is not assignable: %s' % self.destination, ast_node)
        self.value = create_expression(ast_node.value, context)
        self.destination.type.check_assignable_from(self.value.type, ast_node)
        if self.destination.readonly:
            raise ModelError('Variable is immutable: %s' % self.destination, ast_node)

    def __str__(self):
        return 'Assignment(%s = %s)' % (self.destination, self.value)

class If(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.condition = create_expression(ast_node.condition, context)
        bool_type = context.resolve_type(ast.SimpleType('Bool'))
        bool_type.check_assignable_from(self.condition.type, ast_node)
        
        self.on_true = Block(ast_node.on_true, context)
        if ast_node.on_false:
            self.on_false = Block(ast_node.on_false, context)
        else:
            self.on_false = None

        if self.on_false and self.on_true.type == self.on_false.type:
            self.type = self.on_true.type

    def __str__(self):
        return 'If(%s, %s, %s)' % (self.condition, self.on_true, self.on_false)

class While(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.condition = create_expression(ast_node.condition, context)
        bool_type = context.resolve_type(ast.SimpleType('Bool'))
        bool_type.check_assignable_from(self.condition.type, ast_node)
        self.body = Block(ast_node.body, context)

    def __str__(self):
        return 'While(%s, %s)' % (self.condition, self.body)

def create_expression(ast_node, context):
    if isinstance(ast_node, ast.Term):
        return context.resolve_term(ast_node.name, ast_node)
    elif isinstance(ast_node, ast.Call):
        return Call(ast_node, context)
    elif isinstance(ast_node, ast.Assignment):
        return Assignment(ast_node, context)
    elif isinstance(ast_node, ast.If):
        return If(ast_node, context)
    elif isinstance(ast_node, ast.While):
        return While(ast_node, context)
    elif isinstance(ast_node, ast.Value):
        type = context.resolve_type(ast_node.type)
        return Value(ast_node.value, type, ast_node)
    elif isinstance(ast_node, ast.Block):
        return Block(ast_node, context)
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
        self.body = Block(None, context)
        for arg in self.args:
            self.body.names.add(arg.var.name)
            self.body.terms[arg.var.name] = arg.var
        for st in ast_node.body.statements:
            self.body.add_statement(st)
        if self.return_type:
            self.return_type.check_assignable_from(self.body.type, ast_node)

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

    def add_term(self, term, ast_node, name=None):
        if name is None:
            name = term.name
        if name in self.names:
            raise AlreadyDefined(name, ast_node)
        self.names.add(name)
        self.terms[name] = term

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
                self.add_term(value, ast_node, value.value)
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

class Block(Expression, Context):
    def __init__(self, ast_node, parent):
        Context.__init__(self, parent)
        self.statements = []
        self.type = None
        if ast_node:
            for st in ast_node.statements:
                self.add_statement(st)

    def add_statement(self, ast_node):
        if isinstance(ast_node, ast.Definition):
            res = self.add_def(ast_node)
        else:
            res = create_expression(ast_node, self)
            self.type = res.type
        if res is not None:
            self.statements.append(res)

    def _indent(self, text):
        return '\n'.join('\t' + line for line in text.splitlines())

    def __str__(self):
        return 'Block {\n%s\n}' % '\n'.join(self._indent(str(st)) for st in self.statements)

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)

    import model # sigh, import self to have matching classes in builtins and here
    import parse
    import builtins
    
    path = sys.argv[1]
    content = open(path).read()
    
    program = parse.parse(content)
    b = builtins.Builtins()
    m = model.Block(program, b)
    print m
    
