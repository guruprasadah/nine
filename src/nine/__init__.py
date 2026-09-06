import argparse
from enum import Enum
from typing import Callable

from pydantic import BaseModel

class Token(BaseModel):
    pass

class CommaToken(Token):
    pass

class ColonToken(Token):
    pass

# literals
class LiteralToken(Token):
    pass

class IntegerLiteralToken(LiteralToken):
    value: int

class FloatLiteralToken(LiteralToken):
    digits: list[int]
    point: int

class StringLiteralToken(LiteralToken):
    value: str

class Keyword(Enum):
    LET = "let"
    FN = "fn"
    RETURN = "return"
class KeywordToken(Token):
    keyword: Keyword

class IdentifierToken(Token):
    name: str

class Symbol(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    EQ = "="
    LP_N = "("
    RP_N = ")"
    LP_S = "["
    RP_S = "]"
    LP_C = "{"
    RP_C = "}"
    COMMA = ","
    COLON = ":"
    SEMICOLON = ";"
    AMP = "&"
class SymbolToken(Token):
    symbol: Symbol

class EOFToken(Token):
    pass

class LexingState(Enum):
    NONE = "none"
    STRING = "string"

def lex_literal_number(program: str, pos: int, tokens: list[Token]) -> int:
    digits: list[int] = []
    pl = len(program)
    point = 0
    fp = False
    while pos < pl:
        if (c := program[pos]).isdigit():
            digits.append(int(program[pos]))
            if fp:
                point += 1
        elif c == "." and not fp:
            fp = True
        else:
            break
        pos += 1
    if not fp:
        num = 0
        for dig in digits:
            num = dig + num * 10
        tokens.append(IntegerLiteralToken(value=num))
    else:
        tokens.append(FloatLiteralToken(digits=digits, point=point))
    return pos

def lex_literal_string(program: str, pos: int, tokens: list[Token]):
    pos += 1
    buf: list[str] = []
    while pos < len(program):
        if (c := program[pos]) == '"':
            break
        buf.append(c)
        pos += 1
    else:
        pos += 1
        return pos
    tokens.append(StringLiteralToken(value="".join(buf)))
    pos += 1
    return pos

def lex_kw_or_id(program: str, pos: int, tokens: list[Token]):
    buf: list[str] = []
    while pos < len(program):
        c = program[pos]
        if all([(not c.isalpha()), (not c == "_"), (not c.isdigit())]):
            break
        buf.append(c)
        pos += 1
    lx = "".join(buf)
    if in_enum(lx, Keyword):
        tokens.append(KeywordToken(keyword=Keyword(lx)))
    else:
        tokens.append(IdentifierToken(name=lx))
    return pos

def in_enum(value: str, enum: type[Enum]) -> bool:
    return (kwv := "".join(value)) in [kw.value for kw in enum]

def lex(program: str) -> list[Token]:
    pos: int = 0
    pl = len(program)
    tokens = []
    buf: list[str] = []
    while pos < pl:
        c = program[pos]
        if c.isspace():
            pos += 1
            continue
        elif c in Symbol:
            tokens.append(SymbolToken(symbol=Symbol(c)))
            pos += 1
        elif c.isdigit():
            pos = lex_literal_number(program, pos, tokens)
        elif c == '"':
            pos = lex_literal_string(program, pos, tokens)
        elif c.isalnum() or c == "_":
            pos = lex_kw_or_id(program, pos, tokens)
        else:
            raise RuntimeError(f"Unexpected {c} in input stream")
    tokens.append(EOFToken())
    return tokens

class ASTNode(BaseModel):
    pass

class Expression(ASTNode):
    pass

class IntegerLiteralExpression(Expression):
    value: int

class FloatLiteralExpression(Expression):
    value: float

class StringLiteralExpression(Expression):
    value: str

class IdentifierExpression(Expression):
    name: str

class BinaryExpression(Expression):
    left: Expression
    right: Expression
    operator: Symbol

class Statement(ASTNode):
    pass

class LetStatement(Statement):
    identifier: str
    type: str
    initializer: Expression

def peek(tokens: list[Token], pos: int) -> Token | None:
    if pos < len(tokens):
        return tokens[pos]
    else:
        return None

def parse_expressio(tokens: list[Token], pos: int) -> tuple[Expression, int]:
    tk = peek(tokens, pos)
    if isinstance(tk, IntegerLiteralToken):
        return (IntegerLiteralExpression(value=tk.value), pos + 1)
    elif isinstance(tk, FloatLiteralToken):
        v = 0
        for d in tk.digits:
            v = d + (v * 10)
        return (FloatLiteralExpression(value=v/(10 ** tk.point)), pos + 1)
    elif isinstance(tk, StringLiteralToken):
        return (StringLiteralExpression(value=tk.value), pos + 1)
    else:
        raise RuntimeError(f"expected expression, got {type(tk).__name__} instead")

def parse_expression2(tokens: list[Token], pos: int) -> tuple[Expression, int]:
    stack: list[Expression] = []

    while True:
        tk = peek(tokens, pos)
        match tk:
            case IntegerLiteralToken():
                stack.append(IntegerLiteralExpression(value=tk.value))
                pos += 1
            case FloatLiteralToken():
                v = 0
                for d in tk.digits:
                    v = d + (v * 10)
                stack.append(FloatLiteralExpression(value=v/(10 ** tk.point)))
                pos += 1
            case StringLiteralToken():
                stack.append(StringLiteralExpression(value=tk.value))
                pos += 1
            case IdentifierToken():
                stack.append(IdentifierExpression(name=tk.name))
                pos += 1
            case SymbolToken(symbol=Symbol.ADD | Symbol.SUB | Symbol.MUL | Symbol.DIV as op):
                right = stack.pop()
                left = stack.pop()
                stack.append(BinaryExpression(left=left, right=right, operator=op))
                pos += 1
            case SymbolToken(symbol=Symbol.LP_N):
                pos += 1
                exp, pos = parse_expression2(tokens, pos)
                if not (isinstance(t:=peek(tokens, pos), SymbolToken) and t.symbol == Symbol.RP_N):
                    raise RuntimeError(f"Expected right paren, got {type(t).__name__} instead")
                stack.append(exp)
                pos += 1
            case _:
                pos -= 1
                break

    if len(stack) != 1:
        raise RuntimeError(f"Expected 1 expression, got {len(stack)} instead")

    return stack[0], pos + 1

def parse_let(tokens: list[Token], pos: int) -> tuple[ASTNode, int]:
    pos += 1
    iden = peek(tokens, pos)
    if not isinstance(iden, IdentifierToken):
        raise RuntimeError(f"expected identifier, got {type(iden).__name__} instead")
    pos += 1
    col = peek(tokens, pos)
    if not (isinstance(col, SymbolToken) and col.symbol == Symbol.COLON):
        raise RuntimeError(f"expected colon, got {type(col).__name__} instead")
    pos += 1
    typ = peek(tokens, pos)
    if not isinstance(typ, IdentifierToken):
        raise RuntimeError(f"expected type identifier, got {type(typ).__name__} instead")
    pos += 1
    eq = peek(tokens, pos)
    if not (isinstance(eq, SymbolToken) and eq.symbol == Symbol.EQ):
        raise RuntimeError(f"expected equal, got {type(eq).__name__} instead")
    pos += 1
    exp, pos = parse_expression2(tokens, pos)
    if not (isinstance(sem := peek(tokens, pos), SymbolToken) and sem.symbol == Symbol.SEMICOLON):
        raise RuntimeError(f"expected semicolon, got {type(sem).__name__} instead")
    pos += 1
    return LetStatement(identifier=iden.name, type=typ.name, initializer=exp), pos

def parse(tokens: list[Token]):
    pos = 0
    nodes: list[ASTNode] = []
    while True:
        tk = peek(tokens, pos)
        match tk:
            case KeywordToken(keyword=Keyword.LET):
                node, pos = parse_let(tokens=tokens, pos=pos)
                nodes.append(node)
            case EOFToken():
                break
    return nodes

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")

    args = parser.parse_args()

    with open(args.source, "r") as f:
        p = f.read()
        l = lex(p)
        print(l)
        print(parse(l))