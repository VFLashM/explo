import logging
import ply.lex as lex

logger = logging.getLogger('lexer')

keywords = {
    'enum' : 'ENUM',
    'type' : 'TYPEKW',
    'fn' : 'FN',
    'let' : 'LET',
    'var' : 'VAR',
    }
tokens = (
    'TERM',
    'TYPE',
    'LPAREN',
    'RPAREN',
    'LBRACE',
    'RBRACE',
    'LESS',
    'GREATER',
    'COMMA',
    'COLON',
    'EQ',
    'ARROW',
    ) + tuple(keywords.values())

t_TYPE = r'[A-Z][a-zA-Z_]*'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LBRACE = r'\{'
t_RBRACE  = r'\}'
t_COMMA = r'\,'
t_COLON = r'\:'
t_LESS  = r'\<'
t_GREATER = r'\>'
t_EQ = r'='
t_ARROW = '->'
t_ignore = '\t '

def t_TERM(t):
    r'[a-z0-9][a-zA-Z_]*'
    if t.value in keywords:
        t.type = keywords[t.value]
    return t

def t_error(t):
    print 'Lexer error in line %s: unexpected symbol: %r' % (t.lineno, t.value[0])
    lines = t.lexer.lexdata.splitlines()
    print lines[t.lineno - 1]
    t.lexer.skip(1)

def t_comment(t):
    r'(/\*(.|\n)*?\*/)|(//.*)'
    t.lexer.lineno += t.value.count('\n')

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def lexer():
    return lex.lex()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import sys
    
    for path in sys.argv[1:]:
        content = open(path).read()
        lexer = lex.lex()
        lexer.input(content)

        lines = content.splitlines()
        last_line = None
        while True:
            tok = lexer.token()
            if not tok:
                sys.stdout.write('\n')
                break
            if last_line != tok.lineno:
                last_line = tok.lineno
                sys.stdout.write('\n')
                line = lines[tok.lineno - 1]
                prefix = len(line) - len(line.lstrip())
                sys.stdout.write(' ' * prefix)
            else:
                sys.stdout.write(' ')
            sys.stdout.write('%s(%r)' % (tok.type, tok.value))
        
        
