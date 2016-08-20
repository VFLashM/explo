import re
import ply.yacc as yacc
import ast
import lexer
import logging

tokens = lexer.tokens
start = 'def_list'

def p_error(t):
    print 'Syntax error in line %s: unexpected token: %s' % (t.lineno, t)
    lines = t.lexer.lexdata.splitlines()
    print lines[t.lineno - 1]

def p_def_list(p):
    '''def_list : def
                | def def_list
    '''
    res = [p[1]]
    if len(p) > 2:
        res += p[2]
    p[0] = res

def p_def_enum(p):
    '''def : ENUM TYPE LBRACE term_list RBRACE
           | ENUM TYPE LBRACE term_list COMMA RBRACE'''
    p[0] = ast.Enum(p[2], p[4])

def p_def_type_alias(p):
    '''def : TYPEKW TYPE EQ type'''
    p[0] = ast.TypeAlias(p[2], p[4])

def p_type(p):
    '''type : TYPE'''
    p[0] = p[1]

def p_type_tuple(p):
    '''type : LPAREN type_list RPAREN
            | LPAREN type_list COMMA RPAREN
    '''
    p[0] = p[2]

def p_term_list(p):
    '''term_list : TERM
                 | TERM COMMA term_list
    '''
    res = [p[1]]
    if len(p) > 3:
        res += p[3]
    p[0] = tuple(res)

def p_type_list(p):
    '''type_list : type
                 | type COMMA type_list
    '''
    res = [p[1]]
    if len(p) > 3:
        res += p[3]
    p[0] = tuple(res)

def p_def_var(p):
    '''def : LET TERM EQ expr
           | VAR TERM EQ expr
    '''
    readonly = p[1] == 'let'
    p[0] = ast.Var(p[2], None, readonly, p[4])

def p_def_var_typed(p):
    '''def : LET TERM COLON type EQ expr
           | VAR TERM COLON type EQ expr
    '''
    readonly = p[1] == 'let'
    p[0] = ast.Var(p[2], p[4], readonly, p[6])

    
def p_def_fn(p):
    '''def : FN TERM LPAREN arg_list RPAREN LBRACE statement_list RBRACE
           | FN TERM LPAREN arg_list RPAREN ARROW type LBRACE statement_list RBRACE'''
    if len(p) >= 11:
        p[0] = ast.Func(p[2], p[4], p[7], p[9])
    else:
        p[0] = ast.Func(p[2], p[4], None, p[7])

def p_expr_term(p):
    '''expr : TERM'''
    p[0] = p[1]

def p_expr_call(p):
    '''expr : expr LPAREN expr_list RPAREN
            | expr LPAREN expr_list COMMA RPAREN'''
    p[0] = ast.Call(p[1], p[3])

def p_expr_list(p):
    '''expr_list : expr
                 | expr COMMA expr_list
    '''
    res = [p[1]]
    if len(p) > 3:
        res += p[3]
    p[0] = tuple(res)

def p_arg_list(p):
    '''arg_list :
                | TERM COLON type
                | TERM COLON type COMMA arg_list
    '''
    p[0] = []
    if len(p) > 1:
        p[0].append(ast.Arg(p[1], p[3]))
    if len(p) > 5:
        p[0] += p[5]

def p_statement_list(p):
    '''statement_list : statement
                      | statement statement_list'''
    p[0] = [p[1]]
    if len(p) > 2:
        p[0] += p[2]

def p_statement(p):
    '''statement : expr
                 | def'''
    p[0] = p[1]

def parse(content, debug=False):
    lex = lexer.lexer()
    parser = yacc.yacc()
    return parser.parse(content, lexer=lex, debug=debug)

if __name__ == '__main__':
    import sys
    for path in sys.argv[1:]:
        content = open(path).read()

        parse(content, True)
        print
        print
        defs = parse(content)
        print '\n'.join(map(str, defs))
