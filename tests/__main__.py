import sys
import os
import logging
import model
import interpreter
import error
import compiler

logger = logging.getLogger('test')

class TestFailure(Exception):
    pass

class NoSuccess(TestFailure):
    pass

class NoFailure(TestFailure):
    pass

class WrongFailure(TestFailure):
    pass

def runtime_check(path):
    prefix = os.path.basename(path)
    lines = open(path).readlines()
    for idx, line in enumerate(lines):
        if '//<error' in line and not line.strip().startswith('//'):
            lines[idx] = '\n'

    content = ''.join(lines)
    m = interpreter.build_model(content)
    
    try:
        m.resolve_term('main', None)
    except model.Undefined:
        return
    
    good_lines = []
    bad_line_indices = []

    for idx, line in enumerate(lines):
        if '//<runtime' in line and not line.strip().startswith('//'):
            bad_line_indices.append(idx)
        else:
            good_lines.append(line)

    good = ''.join(good_lines)
    try:
        m = interpreter.build_model(good)
    except error.SyntaxError as e:
        raise NoSuccess('Syntax error: %s' % e)
    try:
        interpreter.run_model(m)
    except error.InterpreterError as e:
        raise NoSuccess('Interpreter runtime error: %s' % e)
    try:
        compiler.run_model(m, prefix)
    except error.ExecutionError as e:
        raise NoSuccess('Compiler runtime error: %s' % e)

    for bad_idx in bad_line_indices:
        bad_lines = list(lines)
        test_line = bad_lines[bad_idx]
        error_message = test_line.split('//<runtime', 1)[1].strip()
        for other_bad_idx in bad_line_indices:
            if other_bad_idx != bad_idx:
                bad_lines[other_bad_idx] = '\n'
        bad = ''.join(bad_lines)
        try:
            m = interpreter.build_model(bad)
        except error.SyntaxError as e:
            raise TestFailure('Unexpected syntax error: %s' % e)
        try:
            interpreter.run_model(m)
            raise TestFailure('No interpreter runtime error on line: %s' % test_line)
        except error.InterpreterError as e:
            if not error_message.lower() in str(e).lower():
                raise WrongFailure('Wrong interpreter runtime error on line: %s: %s' % (test_line, e))
        try:
            compiler.run_model(m, prefix)
            raise TestFailure('No compiler runtime error on line: %s' % test_line)
        except error.ExecutionError as e:
            if not error_message.lower() in str(e).lower():
                raise WrongFailure('Wrong compiler runtime error on line: %s: %s' % (test_line, e))


def check(path):
    lines = open(path).readlines()

    # syntax checks
    good_lines = []
    bad_line_indices = []
        
    for idx, line in enumerate(lines):
        if '//<error' in line and not line.strip().startswith('//'):
            bad_line_indices.append(idx)
        else:
            good_lines.append(line)

    good = ''.join(good_lines)
    try:
        m = interpreter.build_model(good)
    except error.SyntaxError as e:
        raise NoSuccess('Syntax error: %s' % e)
    
    for bad_idx in bad_line_indices:
        bad_lines = list(lines)
        test_line = bad_lines[bad_idx]
        error_message = test_line.split('//<error', 1)[1].strip()
        for other_bad_idx in bad_line_indices:
            if other_bad_idx != bad_idx:
                bad_lines[other_bad_idx] = '\n'
        bad = ''.join(bad_lines)
        try:
            interpreter.build_model(bad)
            raise TestFailure('No error on line: %s' % test_line)
        except error.SyntaxError as e:
            if not error_message.lower() in str(e).lower():
                raise WrongFailure('Wrong error on line: %s: %s' % (test_line, e))

    # runtime checks
    runtime_check(path)
                
def check_all(root):
    success = True
    for name in os.listdir(root):
        if not name.endswith('.epl'):
            continue
        path = os.path.join(root, name)
        logger.info('Checking: %s', path)
        try:
            check(path)
            logger.info('SUCCESS: %s', path)
        except TestFailure as e:
            logger.warn('FAILURE: %s %s %s', path, type(e), e)
            success = False
    return success

logging.basicConfig(level=logging.DEBUG)
if not check_all(os.path.dirname(__file__)):
    sys.exit(1)
