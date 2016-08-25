#!env python2.7
import ast
import error

class ExecutionMode(str):
    @staticmethod
    def worst(old, new):
        assert new is not None
        assert old is not None
        if old == ExecutionMode.compile or new == ExecutionMode.runtime:
            return new
        else:
            return old

ExecutionMode.compile = ExecutionMode('compile')
ExecutionMode.dual = ExecutionMode('dual')
ExecutionMode.runtime = ExecutionMode('runtime')

class ModelError(error.CodeSyntaxError):
    def __init__(self, message, ast_node):
        error.CodeSyntaxError.__init__(self, message)
        self.ast_node = ast_node

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
        ModelError.__init__(self, 'kind mismatch', ast_node)
        self.name = name

class NotCompileTime(ModelError):
    def __init__(self, expr):
        ModelError.__init__(self, 'not compile time:\n%s' % expr, expr.ast_node)

class Node(object):
    def __init__(self, ast_node):
        self.ast_node = ast_node

    @property
    def ex_mode(self):
        raise NotImplementedError(type(self))

class Definition(Node):
    @property
    def ex_mode(self):
        return ExecutionMode.compile

class Type(Node):
    def __init__(self, ast_node):
        Node.__init__(self, ast_node)

    def check_assignable_from(self, other, ast_node):
        if self != other:
            raise TypeMismatch(self, other, ast_node)

class TypeDef(Definition):
    def __init__(self, ast_node, context):
        Definition.__init__(self, ast_node)
        self.type = Enum(ast_node, context)
        
    def __str__(self):
        return 'TypeDef(%s)' % self.type

class Expression(Node):
    def __init__(self, ast_node):
        Node.__init__(self, ast_node)
        self.type = None

class Var(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.name = ast_node.name
        self.readonly = ast_node.readonly
        if ast_node.type is not None:
            self.type = context.resolve_type(ast_node.type)
        else:
            self.type = None
        if self.readonly:
            self.var_ex_mode = ExecutionMode.compile
        else:
            self.var_ex_mode = ExecutionMode.runtime
    
    def __str__(self):
        return 'Var(%s, %s)' % (self.name, self.type.name)

    @property
    def ex_mode(self):
        return self.var_ex_mode

class VarDef(Definition):
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

    @property
    def ex_mode(self):
        if self.value:
            return self.value.ex_mode
        else:
            return ExecutionMode.compile

class Value(Expression):
    def __init__(self, value, type, ast_node):
        Expression.__init__(self, ast_node)
        self.value = value
        self.type = type

    def __str__(self):
        return 'Value(%s, %s)' % (self.value, self.type.name)

    @property
    def ex_mode(self):
        return ExecutionMode.compile

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
        Expression.__init__(self, ast_node)
        self.callee = create_expression(ast_node.callee, context)
        self.args = [create_expression(arg, context) for arg in ast_node.args]
        if not isinstance(self.callee.type, FuncType):
            raise ModelError('Not callable: %s' % self.callee.type, ast_node)
        if len(self.callee.type.arg_types) != len(self.args):
            raise ModelError('Argument count mismatch', ast_node)
        for exp_type, got_arg in zip(self.callee.type.arg_types, self.args):
            exp_type.check_assignable_from(got_arg.type, ast_node)
        self.type = self.callee.type.return_type
        
    def __str__(self):
        return 'Call[%s](%s, [%s])' % (self.ex_mode, self.callee.name, ', '.join(map(str, self.args)))

    @property
    def ex_mode(self):
        res = self.callee.ex_mode
        for arg in self.args:
            res = ExecutionMode.worst(res, arg.ex_mode)
        return res

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

    @property
    def ex_mode(self):
        return ExecutionMode.worst(self.value.ex_mode, self.destination.ex_mode)

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

    @property
    def ex_mode(self):
        res = ExecutionMode.worst(self.condition.ex_mode, self.on_true.ex_mode)
        if self.on_false:
            res = ExecutionMode.worst(res, self.on_false.ex_mode)
        return res

class While(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.condition = create_expression(ast_node.condition, context)
        bool_type = context.resolve_type(ast.SimpleType('Bool'))
        bool_type.check_assignable_from(self.condition.type, ast_node)
        self.body = Block(ast_node.body, context)

    def __str__(self):
        return 'While(%s, %s)' % (self.condition, self.body)

    @property
    def ex_mode(self):
        return ExecutionMode.worst(self.condition.ex_mode, self.body.ex_mode)

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

class Function(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.name = ast_node.name
        self.args = [VarDef(arg, context) for arg in ast_node.args]
        if ast_node.return_type:
            self.return_type = context.resolve_type(ast_node.return_type)
        else:
            self.return_type = None

        arg_context = Context(context)
        for arg in self.args:
            arg_context.add_term(arg.var, None)
            
        self.body = Block(ast_node.body, arg_context)
        if self.return_type:
            self.return_type.check_assignable_from(self.body.type, ast_node)

        arg_types = [arg.var.type for arg in self.args]
        self.type = FuncType(arg_types, self.return_type)

        ex_mode = self.ex_mode
        for arg in self.args:
            arg.var.var_ex_mode = ex_mode

    def __str__(self):
        return 'Func(%s, %s, %s) %s' % (self.name, map(str, self.args), self.return_type.name if self.return_type else None, self.body)

    @property
    def ex_mode(self):
        return self.body.ex_mode

class FuncDef(Definition):
    def __init__(self, ast_node, context):
        self.func = Function(ast_node, context)

    def __str__(self):
        return 'FuncDef(%s)' % self.func

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
            res = TypeDef(ast_node, self)
            self.add_type(res.type, ast_node)
            for value in res.type.values:
                self.add_term(value, ast_node, value.value)
        elif isinstance(ast_node, ast.TypeAlias):
            alias = self.resolve_type(ast_node.target)
            self.add_type(alias, ast_node, ast_node.name)
            res = None
        elif isinstance(ast_node, ast.Var):
            res = VarDef(ast_node, self)
            self.add_term(res.var, ast_node)
        elif isinstance(ast_node, ast.Func):
            res = FuncDef(ast_node, self)
            self.add_term(res.func, ast_node)
        else:
            raise FatalError('unexpected node', ast_node)
        return res

class Block(Expression, Context):
    def __init__(self, ast_node, parent):
        Context.__init__(self, parent)
        Expression.__init__(self, ast_node)
        self.statements = []
        self.type = None
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
        return res

    def _indent(self, text):
        return '\n'.join('\t' + line for line in text.splitlines())

    def __str__(self):
        return 'Block[%s] {\n%s\n}' % (self.ex_mode, '\n'.join(self._indent(str(st)) for st in self.statements))

    @property
    def ex_mode(self):
        res = ExecutionMode.compile
        for st in self.statements:
            res = ExecutionMode.worst(res, st.ex_mode)
        return res

class Program(Block):
    def __init__(self, *args, **kwargs):
        Block.__init__(self, *args, **kwargs)
        if self.ex_mode != ExecutionMode.compile:
            raise NotCompileTime(self)
    
    def __str__(self):
        return '\n'.join(map(str, self.statements))

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)

    import model # sigh, import self to have matching classes in builtins and here
    import parse
    import builtins

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()
    
    content = open(args.path).read()
    
    program = parse.parse(content)
    b = builtins.Builtins()
    m = model.Program(program, b)
    print m
    
