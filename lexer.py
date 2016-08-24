#!env python2.7
import logging
import ply.lex as lex

logger = logging.getLogger('lexer')

keywords = (
    'enum',
    'type',
    'fn',
    'let',
    'var',
    'if',
    'else',
    'while',
    )
tokens = (
    'ID',
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
    'INT',
    'FLOAT',
    ) + tuple(k.upper() for k in keywords)

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
t_INT = r'\-?[0-9]+'
t_FLOAT = r'\-?[0-9]+\.[0-9]+'
t_ignore = '\t '

def t_ID(t):
    r'[a-zA-Z][a-zA-Z_0-9]*'
    if t.value in keywords:
        t.type = t.value.upper()
    return t

def t_error(t):
    lines = t.lexer.lexdata.splitlines()
    line = lines[t.lineno - 1]
    error = 'Lexer error in line %s: unexpected symbol: %r\n%s' % (t.lineno, t.value[0], line)
    t.lexer.errors.append(error)
    logger.error(error)
    t.lexer.skip(1)

def t_comment(t):
    r'(/\*(.|\n)*?\*/)|(//.*)'
    t.lexer.lineno += t.value.count('\n')

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def lexer():
    res = lex.lex()
    res.errors = []
    return res

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()
    
    content = open(args.path).read()

    l = lexer()
    l.input(content)
    while True:
        tok = l.token()
        if not tok:
            sys.stdout.write('\n')
            break
    if l.errors:
        sys.exit(1)

    l = lexer()
    l.input(content)
    lines = content.splitlines()
    last_line = None
    while True:
        tok = l.token()
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


