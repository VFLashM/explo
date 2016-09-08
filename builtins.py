import sys
import ast
import model
import error

class BuiltinMetaType(model.Builtin):
    type = None
    runtime_depends = []
    def __str__(self):
        return 'BuiltinMetaType'
    
BUILTIN_META_TYPE = BuiltinMetaType()
BUILTIN_META_TYPE.type = BUILTIN_META_TYPE

class BuiltinType(model.Builtin):
    def __init__(self, name):
        self.name = name
        self.type = BUILTIN_META_TYPE
        self.runtime_depends = []
        
    def __str__(self):
        return 'BuiltinType(%s)' % self.name

    def execute(self, context):
        return self

class BuiltinFunction(model.Builtin):
    def __init__(self, name, arg_types, return_type, impl, compile_time, context):
        model.Builtin.__init__(self)
        self.name = name
        
        arg_types = [context.resolve_type(ast.Term(at)) for at in arg_types]
        if return_type:
            return_type = context.resolve_type(ast.Term(return_type))
        self.type = model.FuncType(arg_types, return_type)
        
        self.impl = impl
        self.runtime_depends = []
        if compile_time:
            self.call_runtime_depends = []
        else:
            self.call_runtime_depends = [self]

    def execute(self, context):
        return self

    def call(self, context, args):
        arg_values = [arg.value for arg in args]
        ret_value = self.impl(context, arg_values)
        if self.type.return_type:
            return model.Value(ret_value, self.type.return_type, None)

    def __str__(self):
        return 'BuiltinFunction[%s](%s)' % (len(self.runtime_depends), self.name)

class Builtins(model.Context):
    def __init__(self, stdout=sys.stdout):
        model.Context.__init__(self, None)

        self.add_term('Int', BuiltinType('Int'), None)
        self.add_function('print', ['Int'], None, lambda x, args: stdout.write(str(args[0]) + '\n'), False)

        # def abort(*args):
    #         raise error.InterpreterError('abort')
        
    #     self.add_type(BuiltinAnyType(), None)
         
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

    def add_function(self, name, args, return_type, impl, compile_time):
        fn = BuiltinFunction(name, args, return_type, impl, compile_time, self)
        self.add_term(name, fn, None)
