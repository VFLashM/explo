from collections import namedtuple

class Node(object):
    srcmap = None

class Type(Node):
    pass
    
class Expression(Node):
    pass

class Definition(Node):
    name = None

class Enum(Definition):
    def __init__(self, name, values):
        self.name = name
        self.values = values

    def __str__(self):
        return 'Enum(%s, %s)' % (self.name, self.values)

class TypeAlias(Definition):
    def __init__(self, name, target):
        self.name = name
        self.target = target

    def __str__(self):
        return 'TypeAlias(%s = %s)' % (self.name, self.target)

class Var(Definition):
    def __init__(self, name, type, readonly=True, value=None):
        self.name = name
        self.type = type
        self.readonly = readonly
        self.value = value

    def __str__(self):
        romod = 'let' if self.readonly else 'var'
        res = 'Var(%s %s' % (romod, self.name)
        if self.type:
            res += ': %s' % self.type
        if self.value:
            res += ' = %s' % self.value
        res += ')'
        return res

class Func(Definition):
    def __init__(self, name, args, return_type, body):
        self.name = name
        self.args = args
        self.return_type = return_type
        self.body = body

    def __str__(self):
        args = ', '.join(map(str, self.args))
        res = 'Func(%s, [%s]) {\n' % (self.name, args)
        for statement in self.body:
            res += '\t' + str(statement) + '\n'
        res += '}'
        return res

class Call(Expression):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def __str__(self):
        args = ', '.join(map(str, self.args))
        return 'Call(%s, [%s])' % (self.callee, args)

class Assignment(Expression):
    def __init__(self, destination, value):
        self.destination = destination
        self.value = value

    def __str__(self):
        return 'Assignment(%s = %s)' % (self.destination, self.value)

class Term(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Term(%s)' % self.name

class SimpleType(Type):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Type(%s)' % self.name

class Tuple(Type):
    def __init__(self, members):
        self.members = members

    def __str__(self):
        return 'Tuple(%s)' % ', '.join(map(str, self.members))

class Value(Expression):
    def __init__(self, value, type):
        self.value = value
        self.type = type

    def __str__(self):
        return 'Value(%s, %s)' % (self.value, self.type)

