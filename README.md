    # Mini-Python Compiler Pipeline

## Overview
This repository contains the core pipeline for a Mini-Python Compiler, focusing on the complete translation process from raw source code to intermediate representation. Built as a standalone systems architecture project, it seamlessly connects a lexical scanner and a BNF-based parser to an Intermediate Code Generator (ICG). 

The system prioritizes strict execution and technical transparency, designed to halt on syntax errors to mirror standard CPython behavior.

## Architectural Components

The compilation pipeline executes in three distinct phases:

1. **Lexical Analysis (Scanner):** Converts the raw Python source code into a stream of tokens (e.g., Identifiers, Strings, Keywords).
2. **Syntax Analysis (Parser):** Validates the token stream against BNF grammar rules, constructing both an Abstract Syntax Tree (AST) and a Concrete Syntax Tree (CST).
3. **Intermediate Code Generation (ICG):** Traverses the AST to produce low-level instructions. The generator handles complex control flows (such as `While` and `If` statements), binary operations, assignments, and returns.

## Intermediate Code Formats
To ensure the compilation process remains transparent and easily debuggable, the generator outputs the parsed logic into two legible formats:

* **Linear Three-Address Code (TAC):** A flattened, step-by-step representation of operations using generated temporary variables (`t0`, `t1`) and control flow labels (`L0`, `L1`).
* **Quadruple Table:** A highly structured execution table separating operations into `OP`, `ARG 1`, `ARG 2`, and `RESULT` columns for streamlined backend processing.

## Usage and Execution

The primary execution hook for the compiler is located in `icg.py`. 

To run the full pipeline on a target Python file, use the following command line execution:

    python icg.py <filename>

### Example Pipeline Output
When executed, the script will output the entire lifecycle of the code:
1. The original source code.
2. The complete token stream from the scanner.
3. The generated AST (and CST) from the parser.
4. The final TAC and Quadruple tables.