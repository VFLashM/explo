import interpreter
import transpiler

if __name__ == '__main__':
    import os
    import sys
    import logging
    import tempfile
    import subprocess
    logging.basicConfig(level=logging.DEBUG)
    
    path = sys.argv[1]
    content = open(path).read()

    code = tempfile.NamedTemporaryFile(suffix='_transpiled.c')
    m = interpreter.build_model(content)
    tstate = transpiler.State(code)
    m.transpile(tstate)
    code.flush()

    code.seek(0)
    print code.read()

    fd, out = tempfile.mkstemp(suffix='_compiled')
    os.close(fd)
    try:
        subprocess.check_call(['gcc', code.name, '-o', out, '-I.'])
        print 'Executing'
        rc = subprocess.call([out])
        print 'Done with rc=%s' % rc
    except subprocess.CalledProcessError as e:
        print e
        sys.exit(e.returncode)
    finally:
        if os.path.exists(out):
            os.remove(out)
    sys.exit(rc)
