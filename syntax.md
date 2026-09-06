Statements vs expressions:
- a program is composed of a block of statements.
- statements may appear only within a block
- some statements contain their own child block of statements.
- statements do not resolve to a value. they simply exist, optionally causing 
  side effects
- expressions resolve to a value. however, an expression by itself may not be a 
  top-level constituent unit of a program; an expression must be contained 
  either by another expression, or by a statement.
- semicolon delimited statements.

## Expressions are RPN
- Function calls are represented as arg1 arg2 fn_name

Keywords:
- let
- fn
- types
  - (u)int[8, 16, 32, 64]
  - f32, f64
  - byte
  - pointer versions of all of these
  - void
- return

Operators:
- Basic arithmetic: +, -, *, /

Literals:
- integer literals
- float literals
- string literals

Statements:
- fn statement: for defining a function
  - syntax:
    fn name(arg1: type1, arg2: type2) -> return_type {
        ...
    };
- return statement: for returning a value from a function
- let statement: for creating a variable at the current scope
  - syntax:
    let x: type = value;
- = statement: assignment statement