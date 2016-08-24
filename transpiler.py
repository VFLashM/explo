import model
import interpreter

def Node_transpile(self, out):
    raise NotImplementedError(type(self))

model.Node.transpile = Node_transpile

if __name__ == '__main__':
    import sys
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    path = sys.argv[1]
    content = open(path).read()

    m = interpreter.build_model(content)
    m.transpile(sys.stdout)
