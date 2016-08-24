import sys
import ast
import model
import error

class BuiltinFunction(model.Node):
    def __init__(self, name, arg_types, return_type, impl, context):
        model.Node.__init__(self, None)
        self.name = name
        arg_names = [chr(ord('a') + idx) for idx in range(len(arg_types))]
        arg_ast_nodes = []
        for arg_name, type_name in zip(arg_names, arg_types):
            arg_ast_node = ast.Var(arg_name, ast.SimpleType(type_name))
            arg_ast_nodes.append(arg_ast_node)
        self.args = [model.VarDef(arg_ast_node, context) for arg_ast_node in arg_ast_nodes]
        if return_type:
            self.return_type = context.resolve_type(ast.SimpleType(return_type))
        else:
            self.return_type = None
        arg_types = [arg.var.type for arg in self.args]
        self.type = model.FuncType(arg_types, self.return_type)
        self.impl = impl

    def execute(self, state):
        return self

    def call(self, state, args):
        arg_values = [arg.value for arg in args]
        ret_value = self.impl(state, arg_values)
        if self.return_type:
            return model.Value(ret_value, self.return_type, None)

    def transpile(self, tstate):
        tstate.string(self.name)

class BuiltinType(model.Type):
    def __init__(self, name):
        self.name = name
        
    def __str__(self):
        return 'BuiltinType(%s)' % self.name

class BuiltinAnyType(BuiltinType):
    def __init__(self):
        BuiltinType.__init__(self, 'Any')

    def check_assignable_from(self, other, ast_node):
        pass

class Builtins(model.Context):
    def __init__(self):
        model.Context.__init__(self, None)

        def abort(*args):
            raise error.InterpreterError('abort')
        
        self.add_type(BuiltinAnyType(), None)
        self.add_function('print', ['Any'], None, lambda x, args: sys.stdout.write(str(args[0]) + '\n'))
        self.add_function('abort', [], None, abort)
        
        bool_type = self.add_def(ast.Enum('Bool', ['false', 'true']))
        for v in bool_type.values:
            v.value = v.value == 'true'
        self.add_function('and', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] and args[1])
        self.add_function('or', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] or args[1])
        self.add_function('xor', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] != args[1])
        self.add_function('not', ['Bool'], 'Bool', lambda x, args: not args[0])
        self.add_function('beq', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] == args[1])
        self.add_function('bneq', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] != args[1])
        
        self.add_type(BuiltinType('Int'), None)
        self.add_function('add', ['Int', 'Int'], 'Int', lambda x, args: args[0] + args[1])
        self.add_function('sub', ['Int', 'Int'], 'Int', lambda x, args: args[0] - args[1])
        self.add_function('mul', ['Int', 'Int'], 'Int', lambda x, args: args[0] * args[1])
        self.add_function('div', ['Int', 'Int'], 'Int', lambda x, args: args[0] / args[1])
        self.add_function('mod', ['Int', 'Int'], 'Int', lambda x, args: args[0] % args[1])
        self.add_function('ieq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] == args[1])
        self.add_function('ineq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] != args[1])
        self.add_function('gt', ['Int', 'Int'], 'Bool', lambda x, args: args[0] > args[1])
        self.add_function('geq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] >= args[1])
        self.add_function('lt', ['Int', 'Int'], 'Bool', lambda x, args: args[0] < args[1])
        self.add_function('leq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] <= args[1])

    def add_function(self, name, args, return_type, impl):
        fn = BuiltinFunction(name, args, return_type, impl, self)
        self.add_term(fn, None)
