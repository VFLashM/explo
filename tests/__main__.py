import sys
import os
import logging
import model
import interpreter
import error
import compiler
import parse
import transpiler
import traceback

logger = logging.getLogger('test')

ERROR_TYPES = (
    error.CompileTimeError,
    error.CodeSyntaxError,
    parse.ParserError,
    model.ModelError,
    transpiler.InlinerError,
    error.ExecutionTimeError,
    error.InterpreterError,
    )
ERRORS = dict((e.__name__, e) for e in ERROR_TYPES)
ERRORS['RuntimeError'] = error.ExecutionTimeError # useful alias
ERRORS['SyntaxError'] = error.CodeSyntaxError # useful alias

class TestFailure(Exception):
    def __init__(self, msg, code):
        Exception.__init__(self, msg)
        self.code = code
        self.cause = None

class NoSuccess(TestFailure):
    def __init__(self, code, cause):
        TestFailure.__init__(self, 'received %s' % type(cause).__name__, code)
        self.cause = cause

class NoFailure(TestFailure):
    def __init__(self, code, expected):
        TestFailure.__init__(self, 'expected %s(%s)' % (expected[0].__name__, expected[1]), code)
        self.expected = expected

class WrongFailure(TestFailure):
    def __init__(self, code, expected, cause):
        TestFailure.__init__(self, 'expected %s(%s), received %s' % (expected[0].__name__, expected[1], type(cause).__name__), code)
        self.expected = expected
        self.cause = cause
    
class TestFile(object):
    def __init__(self, path, verbose=False):
        if verbose: print 'Parsing %s' % path
        self.path = path
        self.lines = open(path).read().splitlines()
        self.count = 1
        self.errors = {}
        self.output = []
        self.no_run = False
        for idx, line in enumerate(self.lines):
            if '//<' in line:
                code, command = line.split('//<', 1)
                if not code.strip().startswith('//'):
                    parts = command.split(' ', 1)
                    name = parts[0].strip()
                    if len(parts) > 1:
                        value = parts[1].strip()
                    else:
                        value = ''
                    if name == 'Output':
                        self.output.append(value)
                    elif name in ERRORS:
                        self.errors[idx] = ERRORS[name], value
                        self.count += 1
                    else:
                        assert False, 'Unknown test command: %s' % name
            if line.strip().startswith('//!no_run'):
                self.no_run = True

    def build_code(self, error_idx=None):
        test_lines = list(self.lines)
        for idx, line in enumerate(test_lines):
            if idx in self.errors and idx != error_idx:
                test_lines[idx] = ''
        test_code = '\n'.join(test_lines)
        return test_code

    def _check(self, verbose, run_interpreter, run_compiler):
        print 'Checking %s' % self.path
        good = self.build_code(None)
        if verbose: print 'Checking normal run'
        try:
            if verbose: print 'Building model'
            m = interpreter.build_model(good)
            if not self.no_run:
                if run_interpreter:
                    if verbose: print 'Checking interpreter'
                    interpreter.run_model(m)
                if run_compiler:
                    if verbose: print 'Checking compiler'
                    compiler.run_model(m)
        except Exception as e:
            raise NoSuccess(good, e), None, sys.exc_info()[2]

        for idx, edef in self.errors.items():
            etype, message = edef
            bad = self.build_code(idx)
            if verbose: print 'Checking error run: %s %s' % (etype.__name__, message)
            if verbose: print 'Building model'
            try:
                m = interpreter.build_model(bad)
            except Exception as e:
                if not issubclass(type(e), etype) or message not in str(e):
                    raise WrongFailure(bad, edef, e), None, sys.exc_info()[2]
                continue
            else:
                if issubclass(etype, error.CodeSyntaxError):
                    raise NoFailure(bad, edef)

            if self.no_run:
                raise NoFailure(bad, edef)

            if run_interpreter:
                if verbose: print 'Checking interpreter'
                try:
                    interpreter.run_model(m)
                except Exception as e:
                    if not issubclass(type(e), etype) or message not in str(e):
                        raise WrongFailure(bad, edef, e), None, sys.exc_info()[2]
                else:
                    raise NoFailure(bad, edef)

            if run_compiler:
                if verbose: print 'Checking compiler'
                try:
                    compiler.run_model(m)
                except error.ExecutionTimeError as e:
                    if not issubclass(type(e), etype) or message not in str(e):
                        raise WrongFailure(bad, edef, e), None, sys.exc_info()[2]
                else:
                    raise NoFailure(bad, edef)

    def check(self, verbose=False, no_interpreter=False, no_compiler=False):
        try:
            self._check(verbose, not no_interpreter, not no_compiler)
            return True
        except TestFailure as e:
            if verbose:
                traceback.print_exc()
                if e.cause:
                    print 'Cause: %s(%s)' % (type(e.cause).__name__, e.cause)
                print 'For code:'
                print e.code
            else:
                print 'ERROR:', e

def gather_tests(path, verbose=False):
    if os.path.isfile(path):
        return [TestFile(path, verbose)]
    else:
        res = []
        for name in os.listdir(path):
            ipath = os.path.join(path, name)
            if not name.startswith('.') and (os.path.isdir(ipath) or name.endswith('.epl')):
                res += gather_tests(ipath, verbose)
        return res

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='*')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--no-run', action='store_true')
    parser.add_argument('--no-compiler', action='store_true')
    parser.add_argument('--no-interpreter', action='store_true')
    args = parser.parse_args()
    
    test_set = []
    if args.path:
        for path in args.path:
            test_set += gather_tests(path, args.verbose)
    else:
        root = os.path.dirname(__file__)
        test_set += gather_tests(root, args.verbose)
            
    test_count = sum(t.count for t in test_set)
    print 'Collected %s test files with %s test cases' % (len(test_set), test_count)
    
    failed = 0
    for test_file in test_set:
        if not test_file.check(args.verbose,
                               args.no_interpreter or args.no_run,
                               args.no_compiler or args.no_run):
            failed += 1
    if failed:
        print '%s tests failed' % failed
        sys.exit(1)
    else:
        print 'All succeeded'
        
