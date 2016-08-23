import os
import model

class TestFailure(Exception):
    pass

def check(path):
    with open(path) as f:
        lines = f.readlines()
        
    good_lines = []
    bad_line_indices = []
        
    for idx, line in enumerate(lines):
        if '//<error' in line:
            bad_line_indices.append(idx)
        else:
            good_lines.append(line)

    good = '\n'.join(good_lines)
    try:
        model.build(good)
    except model.SemanticError as e:
        raise TestFailure('Model failure: %s' % e)
    
    for bad_idx in bad_line_indices:
        bad_lines = list(lines)
        test_line = bad_lines[bad_idx]
        error_message = test.line.split('//<error', 1)[1]
        for other_bad_idx in bad_line_indices:
            if other_bad_idx != bad_idx:
                bad_lines[other_bad_idx] = ''
        bad = '\n'.join(bad_lines)
        try:
            model.build(bad)
            raise TestFailure('No error on line: %s' % test_line)
        except model.SemanticError as e:
            if not error_message in str(e):
                raise TestFailure('Wrong error on line: %s: %s' % (test_line, e))
            
def check_all(root):
    for name in os.listdir(root):
        path = os.path.join(root, name)
        try:
            check(path)
            print 'SUCCESS:', path
        except TestFailure as e:
            print 'FAILURE:', path, e

if __name__ == '__main__':
    check_all(os.path.dirname(__file__))
