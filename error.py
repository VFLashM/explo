class BaseError(Exception):
    pass

class SyntaxError(BaseError):
    pass

class InterpreterError(BaseError):
    pass

class ExecutionError(BaseError):
    pass
