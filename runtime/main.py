# main.py
#
# Entry point for running a Keshava (.msm) program.
#
# Usage:
#   python main.py sample.msm

import sys

from lexer import lexer
from parser import Parser, ParserError
from interpreter import Interpreter, msmRuntimeError


def run_file(path, input_values=None):
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    if input_values is None:
        input_values = []
        if not sys.stdin.isatty():
            piped_values = [line.rstrip("\n") for line in sys.stdin.read().splitlines() if line.rstrip("\n")]
            if piped_values:
                input_values = piped_values

    try:
        tokens = lexer(code)
    except RuntimeError as e:
        print(f"Lexer error: {e}")
        sys.exit(1)

    try:
        ast = Parser(tokens).parse()
    except ParserError as e:
        print(f"Syntax error: {e}")
        sys.exit(1)

    interpreter = Interpreter(input_values=input_values)
    try:
        interpreter.run(ast)
    except msmRuntimeError as e:
        print(f"Runtime error: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <file.msm> [input values...]")
        sys.exit(1)

    path = sys.argv[1]
    input_values = sys.argv[2:]
    run_file(path, input_values=input_values or None)


if __name__ == "__main__":
    main()
