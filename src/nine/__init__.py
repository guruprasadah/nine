import argparse
from enum import Enum, auto
from typing import Callable

from pydantic import BaseModel

class Token(BaseModel):
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
    CALL = "call"
    TRUE = "true"
    FALSE = "false"
    IF = "if"
    AND = "and"
    OR = "or"
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
        raise RuntimeError("Unterminated string literal")
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
    if lx in Keyword:
        tokens.append(KeywordToken(keyword=Keyword(lx)))
    else:
        tokens.append(IdentifierToken(name=lx))
    return pos

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

class PrimitiveKind(Enum):
    I8 = "i8"
    I16 = "i16"
    I32 = "i32"
    I64 = "i64"
    U8 = "u8"
    U16 = "u16"
    U32 = "u32"
    U64 = "u64"
    F32 = "f32"
    F64 = "f64"
    BOOL = "bool"
    STR = "str"

class PrimitiveType(BaseModel):
    kind: PrimitiveKind

class PointerType(BaseModel):
    pointee: "Type"

class FunctionType(BaseModel):
    parameters: tuple["Type", ...]
    return_type: "Type"

Type = PrimitiveType | PointerType | FunctionType

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

class BoolLiteralExpression(Expression):
    value: bool

class IdentifierExpression(Expression):
    name: str

class BinaryExpression(Expression):
    left: Expression
    right: Expression
    operator: Symbol | Keyword

class FunctionCallExpression(Expression):
    function: IdentifierExpression
    arguments: list[Expression]

class Statement(ASTNode):
    pass

class LetStatement(Statement):
    identifier: str
    type: Type
    initializer: Expression

class IfStatement(Statement):
    condition: Expression
    body: list[Statement]

class FunctionDeclStatement(Statement):
    identifier: str
    type: FunctionType
    body: list[Statement]

def is_sym(tokens: list[Token], pos: int, symbol: Symbol) -> bool:
    return isinstance(tk:=tokens[pos], SymbolToken) and tk.symbol == symbol

def peek(tokens: list[Token], pos: int) -> Token | None:
    if pos < len(tokens):
        return tokens[pos]
    else:
        return None

def parse_expression(tokens: list[Token], pos: int) -> tuple[Expression, int]:
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
            case KeywordToken(keyword=Keyword.TRUE | Keyword.FALSE):
                stack.append(BoolLiteralExpression(value=(tk.keyword==Keyword.TRUE)))
                pos += 1
            case IdentifierToken():
                stack.append(IdentifierExpression(name=tk.name))
                pos += 1
            case SymbolToken(symbol=Symbol.ADD | Symbol.SUB | Symbol.MUL | Symbol.DIV as op):
                if not len(stack) >= 2:
                    raise RuntimeError("At least 2 operands required for binary operator")
                right = stack.pop()
                left = stack.pop()
                stack.append(BinaryExpression(left=left, right=right, operator=op))
                pos += 1
            case KeywordToken(keyword=Keyword.CALL):
                if not stack:
                    raise RuntimeError("Expected function identifier")
                if not isinstance(stack[-1], IdentifierExpression):
                    raise RuntimeError(f"Expected function identifier, got {type(stack[-1]).__name__} instead")
                fc = FunctionCallExpression(function=stack[-1], arguments=stack[0:-1])
                stack.clear()
                stack.append(fc)
                pos += 1
            case KeywordToken(keyword=Keyword.AND | Keyword.OR as kw):
                if not len(stack) >= 2:
                    raise RuntimeError("At least 2 operands required for binary operator")
                right = stack.pop()
                left = stack.pop()
                stack.append(BinaryExpression(left=left, right=right, operator=kw))
                pos += 1
            case SymbolToken(symbol=Symbol.LP_N):
                pos += 1
                exp, pos = parse_expression(tokens, pos)
                t = peek(tokens, pos)
                if not is_sym(tokens, pos, Symbol.RP_N):
                    raise RuntimeError(f"Expected right paren, got {type(t).__name__} instead")
                stack.append(exp)
                pos += 1
            case _:
                break

    if len(stack) != 1:
        raise RuntimeError(f"Expected 1 expression, got {len(stack)} {stack} instead")

    return stack[0], pos

def quals_to_type(quals: list[str]) -> Type:
    if quals[-1] not in PrimitiveKind:
        raise RuntimeError("Fundamental type qualifier may appear only at the end")
    type = PrimitiveType(kind=PrimitiveKind(quals[-1]))
    for q in quals[::-1][1:]:
        if q == "ptr":
            type = PointerType(pointee=type)
        else:
            raise RuntimeError("Unknown type qualifier")
    return type

def parse_type(tokens: list[Token], pos: int, terminate: Callable[[Token], bool]) -> tuple[Type, int]:
    quals: list[str] = []
    while True:
        if terminate(tk := tokens[pos]):
            break
        if not isinstance(tk, IdentifierToken):
            raise RuntimeError(f"Unexpected {tk}")
        quals.append(tk.name)
        pos += 1
    return quals_to_type(quals), pos

def parse_let(tokens: list[Token], pos: int) -> tuple[Statement, int]:
    pos += 1
    iden = peek(tokens, pos)
    if not isinstance(iden, IdentifierToken):
        raise RuntimeError(f"expected identifier, got {type(iden).__name__} instead")
    pos += 1
    col = peek(tokens, pos)
    if not is_sym(tokens, pos, Symbol.COLON):
        raise RuntimeError(f"expected colon, got {type(col).__name__} instead")
    pos += 1
    v_type, pos = parse_type(tokens, pos, lambda x: isinstance(x, SymbolToken) and x.symbol == Symbol.EQ)
    pos += 1
    exp, pos = parse_expression(tokens, pos)
    sem = peek(tokens, pos)
    if not is_sym(tokens, pos, Symbol.SEMICOLON):
        raise RuntimeError(f"expected semicolon, got {type(sem).__name__} instead")
    pos += 1
    return LetStatement(identifier=iden.name, type=v_type, initializer=exp), pos

def parse_if(tokens: list[Token], pos: int) -> tuple[Statement, int]:
    pos += 1
    exp, pos = parse_expression(tokens, pos)
    tk = peek(tokens, pos)
    if not is_sym(tokens, pos, Symbol.LP_C):
        raise RuntimeError(f"Expected left curly parentheses, got {tk} instead")
    pos += 1
    body: list[Statement] = []
    body, pos = parse_block(tokens, pos, lambda x: isinstance(x, SymbolToken) and x.symbol == Symbol.RP_C)
    pos += 1
    return IfStatement(condition=exp,body=body), pos

def parse_expression_list(tokens: list[Token], pos: int, terminate: Callable[[Token], bool]) -> tuple[list[Expression], int]:
    exps: list[Expression] = []
    while not terminate(tokens[pos]):
        e, pos = parse_expression(tokens, pos)
        exps.append(e)
    return exps, pos

def parse_fn(tokens: list[Token], pos: int) -> tuple[Statement, int]:
    pos += 1
    tk = peek(tokens, pos)
    if not isinstance(tk, IdentifierToken):
        raise RuntimeError(f"Expected identifier, got {tk} instead")
    identifier = tk.name
    pos += 1
    tk = peek(tokens, pos)
    if not is_sym(tokens, pos, Symbol.LP_N):
        raise RuntimeError(f"Expected left parentheses, got {tk} instead")
    pos += 1
    arguments: list[tuple[str, Type]] = []
    while True:
        arg_identifier = tokens[pos]
        if not isinstance(arg_identifier, IdentifierToken):
            raise RuntimeError(f"Expected identifier, got {arg_identifier} instead")
        pos += 1
        col = peek(tokens, pos)
        if not is_sym(tokens, pos, Symbol.COLON):
            raise RuntimeError(f"Expected colon, got {col} instead")
        pos += 1
        typ, pos = parse_type(tokens, pos, lambda x: isinstance(x, SymbolToken) and x.symbol in (Symbol.COMMA, Symbol.RP_N))
        arguments.append((arg_identifier.name, typ))
        tk = peek(tokens, pos)
        if is_sym(tokens, pos, Symbol.COMMA):
            pos += 1
        elif is_sym(tokens, pos, Symbol.RP_N):
            break
        else:
            raise RuntimeError(f"Unexpected {tk}")
    pos += 1
    ret, pos = parse_type(tokens, pos, lambda x: isinstance(x, SymbolToken) and x.symbol == Symbol.LP_C)
    tk = peek(tokens, pos)
    if not is_sym(tokens, pos, Symbol.LP_C):
        raise RuntimeError(f"Expected left curly bracket, got {tk} instead")
    pos += 1
    body, pos = parse_block(tokens, pos, lambda x: isinstance(x, SymbolToken) and x.symbol == Symbol.RP_C)
    pos += 1
    f_type = FunctionType(parameters=tuple([x[1] for x in arguments]), return_type=ret)
    return FunctionDeclStatement(identifier=identifier, type=f_type, body=body), pos

def parse_statement(tokens: list[Token], pos: int) -> tuple[Statement, int] | None:
    tk = peek(tokens, pos)
    match tk:
        case KeywordToken(keyword=Keyword.LET):
            return parse_let(tokens=tokens, pos=pos)
        case KeywordToken(keyword=Keyword.IF):
            return parse_if(tokens=tokens, pos=pos)
        case KeywordToken(keyword=Keyword.FN):
            return parse_fn(tokens=tokens, pos=pos)
        case _:
            return None

def parse_block(tokens: list[Token], pos: int, terminate: Callable[[Token], bool]) -> tuple[list[Statement], int]:
    nodes: list[Statement] = []
    while True:
        st = parse_statement(tokens, pos)
        if st is None:
            if terminate(tokens[pos]):
                return nodes, pos
            else:
                raise RuntimeError(f"Unexpected {tokens[pos]}")
        else:
            nodes.append(st[0])
            pos = st[1]

def parse_program(tokens: list[Token]) -> list[Statement]:
    return parse_block(tokens, 0, lambda x: isinstance(x, EOFToken))[0]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")

    args = parser.parse_args()

    with open(args.source, "r") as f:
        p = f.read()
        l = lex(p)
        p = parse_program(l)
        print(p)
