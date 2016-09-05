import sys
import ast
import model
import error

class BuiltinMetaType(model.Builtin):
    type = None
    compile_time = True
    def __str__(self):
        return 'BuiltinMetaType'
    
BUILTIN_META_TYPE = BuiltinMetaType()
BUILTIN_META_TYPE.type = BUILTIN_META_TYPE

# class BuiltinFunction(model.Node):
#     def __init__(self, name, arg_types, return_type, impl, ex_mode, context):
#         model.Node.__init__(self, None)
#         self.name = name
#         arg_names = [chr(ord('a') + idx) for idx in range(len(arg_types))]
#         arg_ast_nodes = []
#         for arg_name, type_name in zip(arg_names, arg_types):
#             arg_ast_node = ast.Var(arg_name, ast.SimpleType(type_name))
#             arg_ast_nodes.append(arg_ast_node)
#         self.args = [model.VarDef(arg_ast_node, context) for arg_ast_node in arg_ast_nodes]
#         if return_type:
#             self.return_type = context.resolve_type(ast.SimpleType(return_type))
#         else:
#             self.return_type = None
#         arg_types = [arg.var.type for arg in self.args]
#         self.type = model.FuncType(arg_types, self.return_type)
#         self.impl = impl
#         self._ex_mode = ex_mode

#     def execute(self, state):
#         return self

#     def call(self, state, args):
#         arg_values = [arg.value for arg in args]
#         ret_value = self.impl(state, arg_values)
#         if self.return_type:
#             return model.Value(ret_value, self.return_type, None)

#     def transpile(self, tstate, prelude, output, result):
#         result.string(self.name)

#     @property
#     def ex_mode(self):
#         return self._ex_mode

class BuiltinType(model.Builtin):
    def __init__(self, name):
        self.name = name
        self.type = BUILTIN_META_TYPE
        self.runtime_depends = []
        
    def __str__(self):
        return 'BuiltinType(%s)' % self.name

    def execute(self, context):
        return self

class Builtins(model.Context):
    def __init__(self, stdout=sys.stdout):
        model.Context.__init__(self, None)

        self.add_term('Int', BuiltinType('Int'), None)

        # def abort(*args):
    #         raise error.InterpreterError('abort')
        
    #     self.add_type(BuiltinAnyType(), None)
    #     self.add_function('print', ['Any'], None, lambda x, args: stdout.write(str(args[0]) + '\n'), model.ExecutionMode.runtime)
    #     self.add_function('abort', [], None, abort, model.ExecutionMode.runtime)
        
    #     bool_type = self.add_def(ast.Enum('Bool', ['false', 'true'])).type
    #     for v in bool_type.values:
    #         v.value = v.value == 'true'
    #     self.add_function('and', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] and args[1])
    #     self.add_function('or', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] or args[1])
    #     self.add_function('xor', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] != args[1])
    #     self.add_function('not', ['Bool'], 'Bool', lambda x, args: not args[0])
    #     self.add_function('beq', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] == args[1])
    #     self.add_function('bneq', ['Bool', 'Bool'], 'Bool', lambda x, args: args[0] != args[1])
        
    #     self.add_type(BuiltinType('Int'), None)
    #     self.add_function('add', ['Int', 'Int'], 'Int', lambda x, args: args[0] + args[1])
    #     self.add_function('sub', ['Int', 'Int'], 'Int', lambda x, args: args[0] - args[1])
    #     self.add_function('mul', ['Int', 'Int'], 'Int', lambda x, args: args[0] * args[1])
    #     self.add_function('div', ['Int', 'Int'], 'Int', lambda x, args: args[0] / args[1])
    #     self.add_function('mod', ['Int', 'Int'], 'Int', lambda x, args: args[0] % args[1])
    #     self.add_function('ieq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] == args[1])
    #     self.add_function('ineq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] != args[1])
    #     self.add_function('gt', ['Int', 'Int'], 'Bool', lambda x, args: args[0] > args[1])
    #     self.add_function('geq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] >= args[1])
    #     self.add_function('lt', ['Int', 'Int'], 'Bool', lambda x, args: args[0] < args[1])
    #     self.add_function('leq', ['Int', 'Int'], 'Bool', lambda x, args: args[0] <= args[1])

    # def add_function(self, name, args, return_type, impl, ex_mode=model.ExecutionMode.compile):
    #     fn = BuiltinFunction(name, args, return_type, impl, ex_mode, self)
    #     self.add_term(fn, None)
