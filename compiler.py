#!env python2.7
import interpreter
import transpiler
import tempfile
import subprocess
import os
import error

if os.name == 'nt':
    EXT = '.exe'
else:
    EXT = ''

def compile(src, dst):
    p = subprocess.Popen(['gcc' + EXT, src, '-o', dst, '-I.'], stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise error.CompilerError(err)

def run_c(src, prefix=''):
    fd, binary = tempfile.mkstemp(prefix=prefix + '_', suffix='_compiled' + EXT)
    try:
        os.close(fd)
        compile(src, binary)
        p = subprocess.Popen([binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode < 0:
            raise error.BinaryExecutionError((p.returncode, out, err))
        return p.returncode, out, err
    finally:
        os.remove(binary)

def run_model(m, prefix=''):
    transpiled = transpiler.transpile_model(m)
    fd, cpath = tempfile.mkstemp(prefix=prefix + '_', suffix='_transpiled.c')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(transpiled)
        return run_c(cpath)
    finally:
        if os.path.exists(cpath):
            os.remove(cpath)

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

    m = interpreter.build_model(content)
    cfd, cpath = tempfile.mkstemp(suffix='_transpiled.c', prefix=prefix + '_')
    try:
        transpiled = transpiler.transpile_model(m)

        if args.debug:
            for idx, line in enumerate(transpiled.splitlines()):
                print '%s\t%s' % (idx+1, line)

        with os.fdopen(cfd, 'w') as f:
            f.write(transpiled)

        if args.output:
            compile(cpath, args.output)
        else:
            rc, out, err = run_c(cpath, prefix, pipe=True)
            sys.stdout.write(out)
            sys.stderr.write(err)
            sys.exit(rc)
    finally:
        if os.path.exists(cpath):
            os.remove(cpath)
