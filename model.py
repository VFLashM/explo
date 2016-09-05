#!env python2.7
import ast
import error

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

class NotCompileTime(ModelError):
    def __init__(self, expr):
        ModelError.__init__(self, 'not compile time:\n%s\ndepends: %s' % (expr, map(str, expr.runtime_depends)), expr.ast_node)

class Node(object):
    def __init__(self, ast_node=None):
        self.ast_node = ast_node

class Builtin(Node):
    def __init__(self):
        Node.__init__(self, None)

class Expression(Node):
    def __init__(self, ast_node):
        Node.__init__(self, ast_node)
        #self.runtime_depends = None
        self.type = None

def check_assignable_from(a, b, c):
    pass

class VarDef(Node):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.function = context.function
        self.readonly = ast_node.readonly
        self.name = ast_node.name
        if ast_node.value:
            self.value = context.create_expression(ast_node.value)
            self.runtime_depends = self.value.runtime_depends
        else:
            self.value = None
            self.runtime_depends = []
            
        if ast_node.type:
            self.type = context.resolve_type(ast_node.type)
            if self.value:
                check_assignable_from(self.type, self.value.type, ast_node)
        else:
            self.type = self.value.type
        
        context.add_term(self.name, self, ast_node)
        context.assign_value(self.name, None)

    def __str__(self):
        return 'VarDef(%s %s: %s = %s)' % ('let' if self.readonly else 'var', self.name, self.type, self.value)

    def execute(self, context):
        if self.value:
            value = self.value.execute(context)
        else:
            value = None
        context.assign_value(self.name, value)

class VarRef(Expression):
    def __init__(self, ast_node, var_def, context):
        Expression.__init__(self, ast_node)
        self.var_def = var_def
        self.type = self.var_def.type
        if context.function == var_def.function or var_def.readonly:
            self.runtime_depends = self.var_def.runtime_depends
        else:
            self.runtime_depends = [self.var_def]

    def execute(self, context):
        return context.get_value(self.var_def.name)

    def __str__(self):
        return 'VarRef[%s](%s)' % (len(self.runtime_depends), self.var_def.name)

class Value(Expression):
    def __init__(self, value, type, ast_node):
        Expression.__init__(self, ast_node)
        self.value = value
        self.type = type
        self.runtime_depends = []

    def __str__(self):
        return 'Value(%s, %s)' % (self.value, self.type)

    def execute(self, context):
        return self

class FuncType(Node):
    def __init__(self, arg_types, return_type):
        self.arg_types = arg_types
        self.return_type = return_type

    def __str__(self):
        return 'FuncType(%s, %s)' % (map(str, self.arg_types), self.return_type)

class Call(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.callee = context.create_expression(ast_node.callee)
        self.args = [context.create_expression(arg) for arg in ast_node.args]
        if not isinstance(self.callee.type, FuncType):
            raise ModelError('Not callable: %s' % self.callee.type, ast_node)
        if len(self.callee.type.arg_types) != len(self.args):
            raise ModelError('Argument count mismatch', ast_node)
        for exp_type, got_arg in zip(self.callee.type.arg_types, self.args):
            check_assignable_from(exp_type, got_arg.type, ast_node)
        self.type = self.callee.type.return_type
        
        self.runtime_depends = set(self.callee.runtime_depends)
        for arg in self.args:
            self.runtime_depends |= set(arg.runtime_depends)
        self.runtime_depends = list(self.runtime_depends)

    def __str__(self):
        return '%s(%s)' % (self.callee, ', '.join(map(str, self.args)))

    def execute(self, context):
        callee = self.callee.execute(context)
        arg_context = Context(context, self)
        for arg, expr in zip(callee.args, self.args):
            val = expr.execute(context)
            arg_context.assign_value(arg.name, val)
        return callee.body.execute(arg_context)

class Assignment(Node):
    def __init__(self, ast_node, context):
        Node.__init__(self, ast_node)
        self.destination = context.resolve_term(ast_node.destination, ast_node)
        if not isinstance(self.destination, VarDef):
            raise ModelError('Destination is not assignable: %s' % self.destination, ast_node)
        self.value = context.create_expression(ast_node.value)
        check_assignable_from(self.destination.type, self.value.type, ast_node)
        if self.destination.readonly:
            raise ModelError('Variable is immutable: %s' % self.destination, ast_node)
        self.runtime_depends = self.value.runtime_depends

    def __str__(self):
        return 'Assignment(%s = %s)' % (self.destination, self.value)

    def execute(self, context):
        value = self.value.execute(context)
        context.assign_value(self.destination.name, value)

# class If(Expression):
#     def __init__(self, ast_node, context):
#         Expression.__init__(self, ast_node)
#         self.condition = create_expression(ast_node.condition, context)
#         bool_type = context.resolve_type(ast.SimpleType('Bool'))
#         bool_type.check_assignable_from(self.condition.type, ast_node)
        
#         self.on_true = Block(ast_node.on_true, context)
#         if ast_node.on_false:
#             self.on_false = Block(ast_node.on_false, context)
#         else:
#             self.on_false = None

#         if self.on_false and self.on_true.type == self.on_false.type:
#             self.type = self.on_true.type
            
#     def __str__(self):
#         return 'If(%s, %s, %s)' % (self.condition, self.on_true, self.on_false)

#     @property
#     def ex_mode(self):
#         res = ExecutionMode.worst(self.condition.ex_mode, self.on_true.ex_mode)
#         if self.on_false:
#             res = ExecutionMode.worst(res, self.on_false.ex_mode)
#         return res

# class While(Expression):
#     def __init__(self, ast_node, context):
#         Expression.__init__(self, ast_node)
#         self.condition = create_expression(ast_node.condition, context)
#         bool_type = context.resolve_type(ast.SimpleType('Bool'))
#         bool_type.check_assignable_from(self.condition.type, ast_node)
#         self.body = Block(ast_node.body, context)

#     def __str__(self):
#         return 'While(%s, %s)' % (self.condition, self.body)

#     @property
#     def ex_mode(self):
#         return ExecutionMode.worst(self.condition.ex_mode, self.body.ex_mode)


class Function(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        
        if ast_node.return_type:
            self.return_type = context.resolve_type(ast_node.return_type)
        else:
            self.return_type = None
            
        while True:
            try:
                arg_context = Context(context, self)
                self.args = [VarDef(arg, arg_context) for arg in ast_node.args]
                for a in self.args:
                    a.runtime_depends = [a]
                self.body = Block(ast_node.body, arg_context)
                break
            except NotCompileTime as e:
                raise

        self.runtime_depends = filter(lambda x: x not in self.args, self.body.runtime_depends)

        if self.return_type:
            check_assignable_from(self.return_type, self.body.type, ast_node)

        arg_types = [arg.type for arg in self.args]
        self.type = FuncType(arg_types, self.return_type)

    def __str__(self):
        return 'Func[%s](%s, %s) %s' % (len(self.runtime_depends), map(str, self.args), self.return_type, self.body)

    def execute(self, context):
        return self

class PrecompiledExpression(Node):
    def __init__(self, ast_node, value, expr):
        Node.__init__(self, ast_node)
        self.value = value
        self.expr = expr
        self.type = value.type
        self.runtime_depends = []

    def __str__(self):
        return 'PrecompiledExpression(%s)' % self.value

    def execute(self, context):
        return self.value

class Context(object):
    def __init__(self, parent, function=None):
        if not function and parent:
            function = parent.function
        self.parent = parent
        self.function = function
        self.terms = {}
        self.values = {}

    def _create_expression(self, ast_node):
        if isinstance(ast_node, ast.Term):
            var_def = self.resolve_term(ast_node.name, ast_node)
            if isinstance(var_def, VarDef):
                return VarRef(ast_node, var_def, self)
            else:
                return var_def
        elif isinstance(ast_node, ast.Func):
            return Function(ast_node, self)
        elif isinstance(ast_node, ast.Call):
            return Call(ast_node, self)
        elif isinstance(ast_node, ast.If):
            return If(ast_node, self)
        elif isinstance(ast_node, ast.While):
            return While(ast_node, self)
        elif isinstance(ast_node, ast.Value):
            vtype = self.resolve_type(ast_node.type)
            return Value(ast_node.value, vtype, ast_node)
        elif isinstance(ast_node, ast.Block):
            return Block(ast_node, self)
        else:
            raise FatalError('unexpected node: %s' % type(ast_node).__name__, ast_node)

    def create_expression(self, ast_node):
        res = self._create_expression(ast_node)
        if len(res.runtime_depends) == 0 and not isinstance(res, (Function, Builtin, VarRef)):
            value = res.execute(self)
            return PrecompiledExpression(ast_node, value, res)
        else:
            return res

    def resolve_term(self, name, ast_node):
        if name not in self.terms:
            if self.parent:
                pres = self.parent.resolve_term(name, ast_node)
                if pres:
                    return pres
            raise Undefined(name, ast_node)
        return self.terms[name]

    def resolve_type(self, ast_node):
        expr = self.create_expression(ast_node)
        if len(expr.runtime_depends) > 0:
            raise NotCompileTime(expr)
        value = expr.execute(self)
        if expr != value:
            return PrecompiledExpression(ast_node, value, expr)
        else:
            return value

    def add_term(self, name, value, ast_node):
        if name in self.terms:
            raise AlreadyDefined(name, ast_node)
        self.terms[name] = value

    def assign_value(self, name, value):
        self.values[name] = value

    def get_value(self, name):
        if name in self.values:
            return self.values[name]
        elif self.parent:
            return self.parent.get_value(name)
        else:
            raise Undefined(name, None)

class Block(Expression, Context):
    def __init__(self, ast_node, parent):
        Context.__init__(self, parent)
        Expression.__init__(self, ast_node)
        self.runtime_depends = []
        self.statements = []
        self.type = None
        for st in ast_node.statements:
            self.add_statement(st)

    def add_statement(self, ast_node):
        if isinstance(ast_node, ast.Var):
            res = VarDef(ast_node, self)
        elif isinstance(ast_node, ast.Assignment):
            res = Assignment(ast_node, self)
        else:
            res = self.create_expression(ast_node)
            self.type = res.type
        if len(res.runtime_depends) == 0:
            res.execute(self)
        self.statements.append(res)
        for rd in res.runtime_depends:
            if rd not in self.runtime_depends:
                self.runtime_depends.append(rd)
        return res

    def _indent(self, text):
        return '\n'.join('\t' + line for line in text.splitlines())

    def __str__(self):
        return 'Block {\n%s\n}' % ('\n'.join(self._indent(str(st)) for st in self.statements))

    def execute(self, context):
        for st in self.statements:
            res = st.execute(context)
        return res

class Program(Block):
    def __init__(self, ast_node, builtins):
        Block.__init__(self, ast_node, builtins)
    
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
    
