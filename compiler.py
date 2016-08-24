import interpreter
import transpiler

def compile(src, dst):
    subprocess.check_call(['gcc', src, '-o', dst, '-I.'])

if __name__ == '__main__':
    import os
    import sys
    import logging
    import tempfile
    import subprocess
    logging.basicConfig(level=logging.DEBUG)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('-o', '--output')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    
    content = open(args.path).read()

    code = tempfile.NamedTemporaryFile(suffix='_transpiled.c')
    m = interpreter.build_model(content)
    tstate = transpiler.State(code)
    m.transpile(tstate)
    code.flush()

    if args.debug:
        code.seek(0)
        print code.read()

    if args.output is None:
        fd, out = tempfile.mkstemp(suffix='_compiled')
        os.close(fd)
        try:
            compile(code.name, out)
            rc = subprocess.call([out])
        finally:
            if os.path.exists(out):
                os.remove(out)
        sys.exit(rc)
    else:
        compile(code.name, args.output)
