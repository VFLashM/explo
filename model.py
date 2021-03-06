#!env python2.7
import sys
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

class NoValue(ModelError):
    def __init__(self, ast_node):
        ModelError.__init__(self, 'no value specified for readonly variable', ast_node)

class FatalError(ModelError):
    pass

class NotCompileTime(ModelError):
    def __init__(self, expr):
        ModelError.__init__(self, 'not compile time:\n%s\ndepends: %s' % (expr, map(str, expr.runtime_depends)), expr.ast_node)

class NoSuchAttribute(ModelError):
    def __init__(self, obj, attr, ast_node):
        ModelError.__init__(self, 'no such attribute: %s' % attr, ast_node)
        self.obj = obj
        self.attr = attr

class NotInitialized(ModelError):
    def __init__(self, name):
        ModelError.__init__(self, 'not initialized: %s' % name, None)

class Node(object):
    def __init__(self, ast_node=None):
        self.ast_node = ast_node

class Builtin(Node):
    def __init__(self):
        self.name = None
        Node.__init__(self, None)

class BuiltinMetaType(Builtin):
    type = None
    runtime_depends = []
    attr_types = {}
    def __str__(self):
        return 'BuiltinMetaType'
    
BUILTIN_META_TYPE = BuiltinMetaType()
BUILTIN_META_TYPE.type = BUILTIN_META_TYPE

class Expression(Node):
    def __init__(self, ast_node):
        Node.__init__(self, ast_node)
        #self.runtime_depends = None
        self.type = None

def is_unit_type(a):
    if isinstance(a, PrecompiledExpression):
        a = a.value
    return isinstance(a, Builtin) and a.name == 'Unit'

def check_assignable_from(a, b, c):
    if is_unit_type(a):
        return True
    if isinstance(a, PrecompiledExpression):
        a = a.value
    if isinstance(b, PrecompiledExpression):
        b = b.value
    if a != b:
        raise TypeMismatch(a, b, c)

class VarDef(Node):
    def __init__(self, ast_node, context, is_argument=False):
        Node.__init__(self, ast_node)
        self.owner = context.owner
        self.readonly = ast_node.readonly
        self.name = ast_node.name
        if ast_node.value:
            self.value = context.create_expression(ast_node.value)
            self.runtime_depends = list(self.value.runtime_depends)
        elif self.owner is None or (self.readonly and not is_argument):
            raise NoValue(ast_node)
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

    def __str__(self):
        return 'VarDef(%s %s: %s = %s)' % ('let' if self.readonly else 'var', self.name, self.type, self.value)

    def execute(self, context):
        context.register_value(self.name)
        if self.value:
            value = self.value.execute(context)
            context.assign_value(self.name, value)

class VarRef(Expression):
    def __init__(self, ast_node, var_def, context):
        Expression.__init__(self, ast_node)
        self.var_def = var_def
        self.type = self.var_def.type
        if context.owner == var_def.owner or var_def.readonly:
            self.runtime_depends = list(self.var_def.runtime_depends)
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
        if len(self.callee.runtime_depends) == 0:
            callee = self.callee.execute(context)
            self.runtime_depends += callee.call_runtime_depends

    def __str__(self):
        return '%s(%s)' % (self.callee, ', '.join(map(str, self.args)))

    def execute(self, context):
        callee = self.callee.execute(context)
        args = [arg.execute(context) for arg in self.args]
        return callee.call(context, args)

class AttributeAccess(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.obj = context.create_expression(ast_node.obj)
        self.attribute = ast_node.attribute
        if self.attribute in self.obj.type.attr_types:
            self.type = self.obj.type.attr_types[self.attribute]
        elif len(self.obj.runtime_depends) == 0:
            obj = self.obj.execute(context)
            if self.attribute in obj.attr_types:
                self.type = obj.attr_types[self.attribute]
            else:
                raise NoSuchAttribute(self.obj.type, self.attribute, ast_node)
        else:
            raise NoSuchAttribute(self.obj.type, self.attribute, ast_node)
            
        self.runtime_depends = list(self.obj.runtime_depends)

    def __str__(self):
        return 'AttributeAccess(%s, %s)' % (self.obj, self.attribute)

    def execute(self, context):
        obj = self.obj.execute(context)
        return obj.get_attr(context, self.attribute)

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
        self.runtime_depends = list(self.value.runtime_depends)

        if self.destination in self.runtime_depends:
            self.destination.runtime_depends += list(self.runtime_depends)
            self.destination.runtime_depends.remove(self.destination)
        else:
            self.destination.runtime_depends = list(self.runtime_depends)
        
        if self.destination.owner != context.owner:
            self.runtime_depends.append(self.destination)

    def __str__(self):
        return 'Assignment(%s = %s)' % (self.destination.name, self.value)

    def execute(self, context):
        value = self.value.execute(context)
        context.assign_value(self.destination.name, value)

class If(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.condition = context.create_expression(ast_node.condition)
        bool_type = context.resolve_type(ast.Term('Bool'))
        check_assignable_from(bool_type, self.condition.type, ast_node)

        self.on_true = Block(ast_node.on_true, context)
        self.runtime_depends = self.condition.runtime_depends + self.on_true.runtime_depends
        if ast_node.on_false:
            self.on_false = Block(ast_node.on_false, context)
            self.runtime_depends += self.on_false.runtime_depends
        else:
            self.on_false = None

        if self.on_false and self.on_true.type == self.on_false.type:
            self.type = self.on_true.type
            
    def __str__(self):
        return 'If(%s, %s, %s)' % (self.condition, self.on_true, self.on_false)

    def execute(self, context):
        condition = self.condition.execute(context)
        if condition.value:
            return self.on_true.execute(context)
        elif self.on_false:
            return self.on_false.execute(context)

class While(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)
        self.context = Context(context, self)
        self.condition = self.context.create_expression(ast_node.condition)
        bool_type = self.context.resolve_type(ast.Term('Bool'))
        check_assignable_from(bool_type, self.condition.type, ast_node)
        self.body = Block(ast_node.body, self.context)
        self.runtime_depends = self.condition.runtime_depends + self.body.runtime_depends
        for rd in self.runtime_depends:
            if not isinstance(rd, VarDef):
                break
            if len(rd.runtime_depends) > 0:
                break
            if rd.owner != context.owner:
                break
        else:
            self.runtime_depends = []

    def __str__(self):
        return 'While[%s](%s, %s)' % (len(self.runtime_depends), self.condition, self.body)

    def execute(self, context):
        while self.condition.execute(context).value:
            self.body.execute(context)

class Enum(Expression):
    def __init__(self, ast_node, context):
        self.values = ast_node.values
        self.runtime_depends = []
        self.type = BUILTIN_META_TYPE
        self.attr_types = {}
        for value in self.values:
            self.attr_types[value] = self

    def execute(self, context):
        return self

    def get_attr(self, context, name):
        assert name in self.values
        return Value(name, self, None)

    def __str__(self):
        return 'Enum(%s)' % ', '.join(self.values)

class Function(Expression):
    def __init__(self, ast_node, context):
        Expression.__init__(self, ast_node)

        self.return_type = context.resolve_type(ast_node.return_type)
            
        while True:
            try:
                arg_context = Context(context, self)
                self.args = [VarDef(arg, arg_context, True) for arg in ast_node.args]
                for a in self.args:
                    a.runtime_depends = [a]
                self.body = Block(ast_node.body, arg_context)
                break
            except NotCompileTime as e:
                raise

        self.runtime_depends = []
        self.call_runtime_depends = filter(lambda x: x not in self.args, self.body.runtime_depends)

        if self.return_type:
            check_assignable_from(self.return_type, self.body.type, ast_node)

        arg_types = [arg.type for arg in self.args]
        self.type = FuncType(arg_types, self.return_type)

    def __str__(self):
        return 'Func[%s](%s, %s) %s' % (len(self.call_runtime_depends), map(str, self.args), self.return_type, self.body)

    def execute(self, context):
        return self

    def call(self, context, args):
        arg_context = Context(context, self)
        for arg, val in zip(self.args, args):
            arg_context.register_value(arg.name)
            arg_context.assign_value(arg.name, val)
        return self.body.execute(arg_context)

class PrecompiledExpression(Node):
    def __init__(self, ast_node, value, expr):
        Node.__init__(self, ast_node)
        self.value = value
        self.expr = expr
        self.type = expr.type
        self.runtime_depends = []

    def __str__(self):
        return '!(%s)' % self.expr

    def execute(self, context):
        return self.value

class RuntimeContext(object):
    def __init__(self, parent):
        self.parent = parent
        self.names = set()
        self.values = {}

    def register_value(self, name):
        if name in self.names:
            raise AlreadyDefined(name, None)
        self.names.add(name)

    def assign_value(self, name, value):
        if name in self.names:
            self.values[name] = value
        elif self.parent:
            self.parent.assign_value(name, value)
        else:
            raise Undefined(name, None)

    def get_value(self, name):
        if name in self.names:
            if name in self.values:
                return self.values[name]
            else:
                raise NotInitialized(name)
        elif self.parent:
            return self.parent.get_value(name)
        else:
            raise Undefined(name, None)

class Context(RuntimeContext):
    def __init__(self, parent, owner=None):
        RuntimeContext.__init__(self, parent)
        if not owner and parent:
            owner = parent.owner
        self.owner = owner
        self.terms = {}

    def _create_expression(self, ast_node):
        if isinstance(ast_node, ast.Term):
            term = self.resolve_term(ast_node.name, ast_node)
            if isinstance(term, VarDef):
                return VarRef(ast_node, term, self)
            else:
                return term
        elif isinstance(ast_node, ast.Enum):
            return Enum(ast_node, self)
        elif isinstance(ast_node, ast.AttributeAccess):
            return AttributeAccess(ast_node, self)
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
        if len(res.runtime_depends) == 0 and not isinstance(res, (Function, Builtin, Value)):
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
        if ast_node is None:
            return self.resolve_term('Unit', ast_node)
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

class Block(Expression, Context):
    def __init__(self, ast_node, parent, import_terms=False):
        if import_terms:
            Context.__init__(self, None)
            self.terms = parent.terms.copy()
        else:
            Context.__init__(self, parent)
        Expression.__init__(self, ast_node)
        self.runtime_depends = []
        self.statements = []
        self.type = self.resolve_type(None)
        for st in ast_node.statements:
            self.add_statement(st)

    def add_statement(self, ast_node):
        if isinstance(ast_node, ast.Var):
            res = VarDef(ast_node, self)
            self.type = self.resolve_type(None)
        elif isinstance(ast_node, ast.Assignment):
            res = Assignment(ast_node, self)
            self.type = self.resolve_type(None)
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
        res = None
        for st in self.statements:
            res = st.execute(context)
        return res

class Program(Block):
    def __init__(self, ast_node, builtins):
        Block.__init__(self, ast_node, builtins, True)
    
    def __str__(self):
        return '\n'.join(map(str, self.statements))

def build_model(code, output=sys.stdout):
    import model # sigh, import self to have matching classes in builtins and here
    import parse
    import builtins

    program_ast = parse.parse(code)
    builtins_context = builtins.Builtins(output)
    program_model = model.Program(program_ast, builtins_context)
    return program_model

def run_model(m):
    #main = m.resolve_term('main', None)
    main = m.get_value('main')
    res = main.call(m, [])
    if res:
        return res.value

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('path')
    args = parser.parse_args()
    
    content = open(args.path).read()
    m = build_model(content)
    print m
    if args.run:
        res = run_model(m)
        print 'res=%s' % res
    
    
