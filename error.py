class BaseError(Exception):
    pass

class CompileTimeError(BaseError):
    pass

class ExecutionTimeError(BaseError):
    pass

class CodeSyntaxError(CompileTimeError):
    pass

class TranspilerError(CompileTimeError):
    pass

class CompilerError(CompileTimeError):
    pass

class InterpreterError(ExecutionTimeError):
    pass

class BinaryExecutionError(ExecutionTimeError):
    pass
