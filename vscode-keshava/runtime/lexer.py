import re
from tokens import KEYWORDS


# -------------------------------------------------
# Remove Keshava comments
# -------------------------------------------------
def remove_comments(code):
    # Remove multi-line comments
    code = re.sub(
        r'Tippani\s*\{[\s\S]*?\}',
        '',
        code,
        flags=re.MULTILINE
    )

    # Remove single-line comments
    code = re.sub(
        r'^\s*Tippani.*$',
        '',
        code,
        flags=re.MULTILINE
    )

    return code


# -------------------------------------------------
# Token Specification
# -------------------------------------------------
TOKEN_SPECIFICATION = [

    ('NUMBER',      r'\d+(?:\.\d+)?'),

    ('STRING',      r'"(?:\\.|[^"\\\n])*"'),

    ('ID',          r'[A-Za-z_][A-Za-z0-9_]*'),

    ('EQ',          r'=='),
    ('NE',          r'!='),
    ('LE',          r'<='),
    ('GE',          r'>='),

    ('LT',          r'<'),
    ('GT',          r'>'),

    ('ASSIGN',      r'='),

    ('PLUS',        r'\+'),
    ('MINUS',       r'-'),
    ('MULT',        r'\*'),
    ('DIV',         r'/'),
    ('MOD',         r'%'),

    ('LPAREN',      r'\('),
    ('RPAREN',      r'\)'),

    ('LBRACE',      r'\{'),
    ('RBRACE',      r'\}'),
    ('LBRACKET',    r'\['),
    ('RBRACKET',    r'\]'),

    ('SEMICOLON',   r';'),
    ('COMMA',       r','),

    ('NEWLINE',     r'\n'),

    ('SKIP',        r'[ \t]+'),

    ('MISMATCH',    r'.'),
]


regex = '|'.join(
    '(?P<%s>%s)' % pair
    for pair in TOKEN_SPECIFICATION
)


# -------------------------------------------------
# Lexer
# -------------------------------------------------
def lexer(code):

    # Remove all comments first
    code = remove_comments(code)

    tokens = []

    line = 1

    for mo in re.finditer(regex, code):

        kind = mo.lastgroup
        value = mo.group()

        if kind == "NEWLINE":
            line += 1
            continue

        elif kind == "SKIP":
            continue

        elif kind == "ID":
            kind = KEYWORDS.get(value, "IDENTIFIER")

        elif kind == "MISMATCH":
            raise RuntimeError(
                f"Unexpected character '{value}' at line {line}"
            )

        tokens.append((kind, value))

    return tokens


# -------------------------------------------------
# Testing
# -------------------------------------------------
if __name__ == "__main__":

    with open("sample.smp", "r", encoding="utf-8") as f:
        code = f.read()

    tokens = lexer(code)

    for token in tokens:
        print(token)
