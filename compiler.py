import interpreter
import transpiler
import tempfile
import subprocess
import os
import error

class ExecutionError(error.BaseError):
    pass

class CompilationError(error.BaseError):
    pass
    
def compile(src, dst):
    try:
        subprocess.check_call(['gcc', src, '-o', dst, '-I.'])
    except subprocess.CalledProcessError:
        raise CompilationError()

def run_c(src, prefix=''):
    fd, binary = tempfile.mkstemp(prefix=prefix + '_', suffix='_compiled')
    try:
        os.close(fd)
        compile(src, binary)
        p = subprocess.Popen([binary], stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode < 0:
            raise ExecutionError(err)
        return p.returncode
    finally:
        os.remove(binary)

def run_model(m, prefix=''):
    code = tempfile.NamedTemporaryFile(prefix=prefix + '_', suffix='_transpiled.c')
    tstate = transpiler.State(code)
    m.transpile(tstate)
    code.flush()
    return run_c(code.name)

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('-o', '--output')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    
    content = open(args.path).read()
    prefix = os.path.basename(args.path)

    code = tempfile.NamedTemporaryFile(suffix='_transpiled.c', prefix=prefix + '_')
    m = interpreter.build_model(content)
    tstate = transpiler.State(code)
    m.transpile(tstate)
    code.flush()

    if args.debug:
        code.seek(0)
        print code.read()

    if args.output:
        compile(code.name, args.output)
    else:
        rc = run_c(code.name, prefix)
        sys.exit(rc)
