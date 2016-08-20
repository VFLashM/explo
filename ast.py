from collections import namedtuple

Enum = namedtuple('Enum', ['name', 'values'])
TypeAlias = namedtuple('TypeAlias', ['name', 'target'])
Var = namedtuple('Var', ['name', 'type', 'readonly', 'value'])
Arg = namedtuple('ArgDef', ['name', 'type'])
Func = namedtuple('Func', ['name', 'args', 'return_type', 'body'])
Call = namedtuple('Call', ['fn', 'args'])

Expression = (Call)
Definition = (Enum, TypeAlias, Var, Func)

def func_str(self):
    body = '\n'.join('  ' + str(b) for b in self.body)
    return 'Func(name=%r, args=%r, return_type=%r) {\n%s\n}' % (self.name, self.args, self.return_type, body)
Func.__str__ = func_str
