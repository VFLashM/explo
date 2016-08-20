from collections import namedtuple
import ast
import parse

class SemanticError(Exception):
    def __init__(self, error):
        Exception.__init__(self, error)
        self.node = None

class Type(object):
    pass

Enum = namedtuple('Enum', ['name', 'values'])
class Tuple(namedtuple('Tuple', ['types'])):
    @property
    def name(self):
        return '(%s)' % ', '.join(t.name for t in self.types)

class Program(object):
    def __init__(self):
        self._types = {}
        self._vars = {}
        self._funs = {}
        self._names = {}

    def _type_ref(self, t):
        if isinstance(t, tuple):
            t = map(self._type_ref, t)
            res = Tuple(t)
            if res.name not in self._types:
                self._types[res.name] = res
            else:
                res = self._types[res.name]
            return res
        else:
            if not t in self._names:
                raise SemanticError('undefined type: %s' % t)
            else:
                return self._names[t]
                

    def _add(self, d):
        if d.name in self._names:
            raise SemanticError('name already defined: %s' % d.name)
        if type(d) == ast.Enum:
            enum = Enum(d.name, d.values)
            self._types[d.name] = enum 
            self._names[d.name] = enum
        elif type(d) == ast.TypeAlias:
            self._names[d.name] = self._type_ref(d.target)
        else:
            assert False, 'Unexpected ast node: %s' % (d,)

    def add(self, d):
        try:
            self._add(d)
        except SemanticError as e:
            e.node = d

    def __str__(self):
        return ''
        pass

if __name__ == '__main__':
    import sys
    for path in sys.argv[1:]:
        content = open(path).read()
        defs = parse.parse(content)
        p = Program()
        for d in defs:
            p.add(d)
        print p
