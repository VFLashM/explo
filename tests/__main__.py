import sys
import os
import logging
import model
from error import SyntaxError
from model import RuntimeError
from model import Undefined

logger = logging.getLogger('test')

class TestFailure(Exception):
    pass

class NoSuccess(TestFailure):
    pass

class NoFailure(TestFailure):
    pass

class WrongFailure(TestFailure):
    pass

def check(path):
    with open(path) as f:
        lines = f.readlines()

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
        m = model.build(good)
    except SyntaxError as e:
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
            model.build(bad)
            raise TestFailure('No error on line: %s' % test_line)
        except SyntaxError as e:
            if not error_message.lower() in str(e).lower():
                raise WrongFailure('Wrong error on line: %s: %s' % (test_line, e))

    # runtime checks
    try:
        m.resolve_term('main', None)
    except model.Undefined:
        pass
    else:
        good_lines = []
        bad_line_indices = []

        for idx, line in enumerate(lines):
            if '//<error' in line and not line.strip().startswith('//'):
                lines[idx] = '\n'
            elif '//<runtime' in line and not line.strip().startswith('//'):
                bad_line_indices.append(idx)
            else:
                good_lines.append(line)

        good = ''.join(good_lines)
        try:
            model.run(model.build(good))
        except SyntaxError as e:
            raise NoSuccess('Syntax error: %s' % e)
        except RuntimeError as e:
            raise NoSuccess('Runtime error: %s' % e)

        for bad_idx in bad_line_indices:
            bad_lines = list(lines)
            test_line = bad_lines[bad_idx]
            error_message = test_line.split('//<runtime', 1)[1].strip()
            for other_bad_idx in bad_line_indices:
                if other_bad_idx != bad_idx:
                    bad_lines[other_bad_idx] = '\n'
            bad = ''.join(bad_lines)
            try:
                model.run(model.build(bad))
                raise TestFailure('No runtime error on line: %s' % test_line)
            except SyntaxError as e:
                raise TestFailure('Unexpected syntax error: %s' % e)
            except RuntimeError as e:
                if not error_message.lower() in str(e).lower():
                    raise WrongFailure('Wrong runtime error on line: %s: %s' % (test_line, e))
            
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
