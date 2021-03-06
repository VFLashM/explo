from collections import namedtuple

class Node(object):
    srcmap = None

class Type(Node):
    pass
    
class Expression(Node):
    pass

class Definition(Node):
    name = None

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

class Func(Expression):
    def __init__(self, args, return_type, body):
        self.args = args
        self.return_type = return_type
        self.body = body

    def __str__(self):
        args = ', '.join(map(str, self.args))
        return 'Func(%s) %s' % (args, self.body)

class Call(Expression):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def __str__(self):
        args = ', '.join(map(str, self.args))
        return 'Call(%s, [%s])' % (self.callee, args)

class AttributeAccess(Expression):
    def __init__(self, obj, attribute):
        self.obj = obj
        self.attribute = attribute

    def __str__(self):
        return 'AttributeAccess(%s, %s)' % (self.obj, self.attribute)

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

class If(Expression):
    def __init__(self, condition, on_true, on_false):
        self.condition = condition
        self.on_true = on_true
        self.on_false = on_false

    def __str__(self):
        return 'If(%s, %s, %s)' % (self.condition, self.on_true, self.on_false)

class While(Expression):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __str__(self):
        return 'While(%s, %s)' % (self.condition, self.body)

class Block(Expression):
    def __init__(self, statements):
        self.statements = statements

    def __str__(self):
        if not self.statements:
            return '{}'
        res = '{\n'
        for statement in self.statements:
            res += '\t' + str(statement).replace('\n', '\n\t') + '\n'
        res += '}'
        return res
        
class Program(Block):
    def __str__(self):
        return 'Program %s' % Block.__str__(self)

class Enum(Expression):
    def __init__(self, values):
        self.values = values
        
    def __str__(self):
        return 'Enum(%s)' % ', '.join(self.values)
