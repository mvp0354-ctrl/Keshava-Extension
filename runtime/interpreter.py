# interpreter.py
#
# Tree-walking interpreter for Keshava.
# Executes the AST produced by parser.py.

import sys

from ast_nodes import (
    Program, VarDeclaration, Assignment, Print, If, While,
    For, Break, Continue, Function, Return, FunctionCall, BinaryOp,
    UnaryOp, Number, String, Boolean, Identifier, Input, ListLiteral,
    IndexExpr, Import
)


class ReturnSignal(Exception):
    """Used internally to unwind the call stack on a return statement."""
    def __init__(self, value):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class msmRuntimeError(Exception):
    pass


class Environment:
    """A single scope of variables, chained to its parent scope."""

    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def declare(self, name, value):
        self.vars[name] = value

    def get(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise msmRuntimeError(f"Undefined variable '{name}'")

    def set(self, name, value):
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        # If it was never declared, define it in the current scope.
        self.vars[name] = value


class Interpreter:
    def __init__(self, base_dir=None, input_values=None):
        self.global_env = Environment()
        self.functions = {}
        self.base_dir = base_dir or "."
        self.input_values = list(input_values or [])
        self.input_index = 0

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self, program: Program):
        for statement in program.statements:
            self.execute(statement, self.global_env)

    # ------------------------------------------------------------------
    # Statement execution
    # ------------------------------------------------------------------

    def execute(self, node, env):
        method_name = f"exec_{type(node).__name__}"
        method = getattr(self, method_name, None)
        if method is None:
            raise msmRuntimeError(f"No exec method for node type {type(node).__name__}")
        return method(node, env)

    def exec_VarDeclaration(self, node: VarDeclaration, env):
        value = self.evaluate(node.value, env)
        if isinstance(node.value, Input):
            value = self.coerce_input_value(value, node.datatype)
        env.declare(node.name, value)

    def exec_Assignment(self, node: Assignment, env):
        value = self.evaluate(node.value, env)
        if isinstance(node.value, Input):
            value = self.coerce_input_value(value, None)
        env.set(node.name, value)

    def exec_Print(self, node: Print, env):
        value = self.evaluate(node.value, env)
        print(self.stringify(value))

    def exec_If(self, node: If, env):
        if self.evaluate(node.condition, env):
            self.execute_block(node.true_block, Environment(env))
        elif node.false_block is not None:
            self.execute_block(node.false_block, Environment(env))

    def exec_While(self, node: While, env):
        while self.evaluate(node.condition, env):
            try:
                self.execute_block(node.body, Environment(env))
            except ContinueSignal:
                continue
            except BreakSignal:
                break

    def exec_For(self, node: For, env):
        loop_env = Environment(env)
        if node.initializer is not None:
            self.execute(node.initializer, loop_env)

        while True:
            if node.condition is not None and not self.evaluate(node.condition, loop_env):
                break
            try:
                self.execute_block(node.body, Environment(loop_env))
            except ContinueSignal:
                pass
            except BreakSignal:
                break
            if node.update is not None:
                if isinstance(node.update, FunctionCall):
                    self.call_function(node.update, loop_env)
                else:
                    self.execute(node.update, loop_env)

    def exec_Function(self, node: Function, env):
        self.functions[node.name] = node

    def exec_Import(self, node: Import, env):
        module_path = self.resolve_module_path(node.module_name)
        self.load_module(module_path)

    def exec_Return(self, node: Return, env):
        value = self.evaluate(node.value, env) if node.value is not None else None
        raise ReturnSignal(value)

    def exec_Break(self, node: Break, env):
        raise BreakSignal()

    def exec_Continue(self, node: Continue, env):
        raise ContinueSignal()

    def exec_FunctionCall(self, node: FunctionCall, env):
        # A function call used as a standalone statement.
        self.call_function(node, env)

    def execute_block(self, statements, env):
        for statement in statements:
            self.execute(statement, env)

    # ------------------------------------------------------------------
    # Expression evaluation
    # ------------------------------------------------------------------

    def evaluate(self, node, env):
        method_name = f"eval_{type(node).__name__}"
        method = getattr(self, method_name, None)
        if method is None:
            raise msmRuntimeError(f"No eval method for node type {type(node).__name__}")
        return method(node, env)

    def eval_Number(self, node: Number, env):
        return node.value

    def eval_String(self, node: String, env):
        return node.value

    def eval_Boolean(self, node: Boolean, env):
        return node.value

    def eval_ListLiteral(self, node: ListLiteral, env):
        return [self.evaluate(value, env) for value in node.values]

    def eval_IndexExpr(self, node: IndexExpr, env):
        target = self.evaluate(node.target, env)
        index = self.evaluate(node.index, env)
        try:
            return target[index]
        except TypeError as exc:
            raise msmRuntimeError("Index must be an integer") from exc
        except IndexError as exc:
            raise msmRuntimeError(f"Index {index} is out of range") from exc

    def eval_Input(self, node: Input, env):
        if self.input_index < len(self.input_values):
            value = self.input_values[self.input_index]
            self.input_index += 1
            return value

        if sys.stdin.isatty():
            try:
                value = input("Enter value: ")
            except EOFError:
                raise msmRuntimeError("Input required but no value was provided")
            self.input_values.append(value)
            self.input_index += 1
            return value

        raise msmRuntimeError("Input required but no value was provided")

    def eval_Identifier(self, node: Identifier, env):
        return env.get(node.name)

    def eval_FunctionCall(self, node: FunctionCall, env):
        return self.call_function(node, env)

    def eval_UnaryOp(self, node: UnaryOp, env):
        value = self.evaluate(node.operand, env)
        if node.operator == "-":
            return -value
        if node.operator == "Nahi":
            return not bool(value)
        raise msmRuntimeError(f"Unknown unary operator '{node.operator}'")

    def eval_BinaryOp(self, node: BinaryOp, env):
        op = node.operator

        if op == "Aur":
            return bool(self.evaluate(node.left, env)) and bool(self.evaluate(node.right, env))
        if op == "Athava":
            return bool(self.evaluate(node.left, env)) or bool(self.evaluate(node.right, env))

        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)

        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise msmRuntimeError("Division by zero")
            return left / right
        if op == "%":
            if right == 0:
                raise msmRuntimeError("Modulo by zero")
            return left % right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right

        raise msmRuntimeError(f"Unknown operator '{op}'")

    # ------------------------------------------------------------------
    # Function calls
    # ------------------------------------------------------------------

    def call_function(self, node: FunctionCall, env):
        if node.name in {"append", "length", "type", "int", "str", "bool", "range"}:
            return self.call_builtin_function(node.name, node.arguments, env)

        if node.name not in self.functions:
            raise msmRuntimeError(f"Undefined function '{node.name}'")

        func = self.functions[node.name]
        if len(func.params) != len(node.arguments):
            raise msmRuntimeError(
                f"Function '{node.name}' expects {len(func.params)} argument(s), "
                f"got {len(node.arguments)}"
            )

        call_env = Environment(self.global_env)
        for param, arg_expr in zip(func.params, node.arguments):
            call_env.declare(param, self.evaluate(arg_expr, env))

        try:
            self.execute_block(func.body, call_env)
        except ReturnSignal as ret:
            return ret.value

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def load_module(self, module_path):
        from lexer import lexer
        from parser import Parser

        with open(module_path, "r", encoding="utf-8") as fh:
            code = fh.read()

        tokens = lexer(code)
        ast = Parser(tokens).parse()
        self.run(ast)

    def resolve_module_path(self, module_name):
        import os

        candidate = os.path.join(self.base_dir, module_name)
        if os.path.isfile(candidate + ".msm"):
            return candidate + ".msm"
        if os.path.isfile(candidate):
            return candidate
        raise msmRuntimeError(f"Unable to import module '{module_name}'")

    def call_builtin_function(self, name, args, env):
        if name == "append":
            if len(args) != 2:
                raise msmRuntimeError("append expects 2 arguments")
            target = self.evaluate(args[0], env)
            value = self.evaluate(args[1], env)
            target.append(value)
            return target

        if name == "length":
            if len(args) != 1:
                raise msmRuntimeError("length expects 1 argument")
            return len(self.evaluate(args[0], env))

        if name == "type":
            if len(args) != 1:
                raise msmRuntimeError("type expects 1 argument")
            value = self.evaluate(args[0], env)
            if isinstance(value, bool):
                return "Satyam"
            if isinstance(value, int) or isinstance(value, float):
                return "Sankhya"
            if isinstance(value, str):
                return "Paatha"
            if isinstance(value, list):
                return "Suchi"
            return type(value).__name__

        if name == "int":
            if len(args) != 1:
                raise msmRuntimeError("int expects 1 argument")
            return int(self.evaluate(args[0], env))

        if name == "str":
            if len(args) != 1:
                raise msmRuntimeError("str expects 1 argument")
            return self.stringify(self.evaluate(args[0], env))

        if name == "bool":
            if len(args) != 1:
                raise msmRuntimeError("bool expects 1 argument")
            return bool(self.evaluate(args[0], env))

        if name == "range":
            values = [self.evaluate(arg, env) for arg in args]
            if not 1 <= len(values) <= 3:
                raise msmRuntimeError("range expects 1 to 3 arguments")
            return list(range(*values))

        raise msmRuntimeError(f"Unknown builtin function '{name}'")

    @staticmethod
    def stringify(value):
        if value is True:
            return "Satya"
        if value is False:
            return "Asatya"
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def coerce_input_value(value, datatype):
        if datatype in {"Sankhya", "INT"}:
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise msmRuntimeError(f"Cannot convert input '{value}' to an integer") from exc
        if datatype in {"Satyam", "BOOL"}:
            try:
                return str(value).strip().lower() in {"true", "satya", "1", "yes"}
            except Exception as exc:
                raise msmRuntimeError(f"Cannot convert input '{value}' to a boolean") from exc
        return str(value)
