import re
import ply.yacc as yacc
import ast
import lexer
import logging
from error import ParserError

logger = logging.getLogger('parser')
tokens = lexer.tokens
start = 'def_list'

def p_error(t):
    if t is None:
        logger.error('unexpected end of file')
        return
    lines = t.lexer.lexdata.splitlines()
    line = lines[t.lineno - 1]
    error = 'Syntax error in line %s: unexpected token: %s\n%s' % (t.lineno, t, line)
    t.lexer.errors.append(error)
    logger.error(error)

def _process_list(p, sep=1):
    if len(p) == 1:
        p[0] = []
    elif len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2+sep]]

def p_def_list(p):
    '''def_list : def
                | def_list def
    '''
    _process_list(p, sep=0)

def p_optional_comma(p):
    '''optional_comma :
                      | COMMA
    '''
    pass

def p_def_enum(p):
    '''def : ENUM ID LBRACE id_list optional_comma RBRACE'''
    p[0] = ast.Enum(p[2], p[4])

def p_id_list(p):
    '''id_list :
               | ID
               | id_list COMMA ID
    '''
    _process_list(p)

def p_def_type_alias(p):
    '''def : TYPE ID EQ type'''
    p[0] = ast.TypeAlias(p[2], p[4])

def p_type_simple(p):
    '''type : ID'''
    p[0] = p[1]

def p_type_tuple(p):
    '''type : LPAREN RPAREN
            | LPAREN type_list optional_comma RPAREN
    '''
    if len(p) > 3:
        p[0] = p[2]
    else:
        p[0] = ()

def p_type_list(p):
    '''type_list : type
                 | type_list COMMA type
    '''
    _process_list(p)

def p_def_var(p):
    '''def : LET ID EQ expr
           | VAR ID EQ expr
    '''
    readonly = p[1] == 'let'
    p[0] = ast.Var(p[2], None, readonly, p[4])

def p_def_var_typed(p):
    '''def : LET ID COLON type
           | VAR ID COLON type
           | LET ID COLON type EQ expr
           | VAR ID COLON type EQ expr
    '''
    readonly = p[1] == 'let'
    if len(p) > 6:
        value = p[6]
    else:
        value = None
    p[0] = ast.Var(p[2], p[4], readonly, value)

    
def p_def_fn(p):
    '''def : FN ID LPAREN arg_def_list RPAREN LBRACE statement_list RBRACE
           | FN ID LPAREN arg_def_list RPAREN ARROW type LBRACE statement_list RBRACE'''
    if len(p) >= 11:
        p[0] = ast.Func(p[2], p[4], p[7], p[9])
    else:
        p[0] = ast.Func(p[2], p[4], None, p[7])

def p_expr_simple(p):
    '''expr : ID'''
    p[0] = p[1]

def p_expr_call(p):
    '''expr : expr LPAREN expr_list optional_comma RPAREN'''
    p[0] = ast.Call(p[1], p[3])

def p_expr_list(p):
    '''expr_list : expr
                 | expr_list COMMA expr
    '''
    _process_list(p)

def p_arg_def(p):
    '''arg_def : ID COLON type'''
    p[0] = ast.Arg(p[1], p[3])

def p_arg_def_list(p):
    '''arg_def_list :
                    | arg_def
                    | arg_def_list COMMA arg_def
    '''
    _process_list(p)

def p_statement_list(p):
    '''statement_list :
                      | statement
                      | statement_list statement'''
    _process_list(p, sep=0)

def p_statement(p):
    '''statement : expr
                 | def
                 | ID EQ expr'''
    if len(p) > 2:
        p[0] = ast.Assignment(p[1], p[3])
    else:
        p[0] = p[1]

def parse(content, debug=False):
    lex = lexer.lexer()
    parser = yacc.yacc()
    res = parser.parse(content, lexer=lex, debug=debug)
    if res is None:
        errors = '\n'.join(lex.errors)
        if not errors:
            errors = 'unexpected end of file'
        raise ParserError(errors)
    return res

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import sys
    for path in sys.argv[1:]:
        content = open(path).read()

        parse(content, True)
        print
        print
        defs = parse(content)
        print '\n'.join(map(str, defs))
