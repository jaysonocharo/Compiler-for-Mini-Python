import sys
from pprint import pprint

# Importing lexer
try:
    from scanner import lex
except ImportError:
    print("Error: Could not import 'lex' from scanner.py. Ensure both files are in the same directory.")
    sys.exit(1)

class ParseError(Exception):
    pass

# ==========================================
# 1. CONCRETE SYNTAX TREE (CST) NODES
# ==========================================
class CSTNode:
    def __init__(self, name):
        self.name = name
        self.children = []

class CSTLeaf:
    def __init__(self, token_type, value):
        self.token_type = token_type
        self.value = value

def print_cst(node, prefix="", is_last=True):
    """Recursively prints the CST in a clean ASCII format."""
    branch = "└── " if is_last else "├── "
    
    if isinstance(node, CSTLeaf):
        val = repr(node.value) if node.token_type in ['NEWLINE', 'STRING'] else node.value
        print(f"{prefix}{branch}{node.token_type}: {val}")
    else:
        print(f"{prefix}{branch}{node.name}")
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            print_cst(child, new_prefix, i == len(node.children) - 1)


# ==========================================
# 2. ABSTRACT SYNTAX TREE (AST) NODES
# ==========================================
class ASTNode: pass

class NumberNode(ASTNode):
    def __init__(self, value): self.value = value
    def __repr__(self): return f"Num({self.value})"

class StringNode(ASTNode):
    def __init__(self, value): self.value = value
    def __repr__(self): return f"Str({self.value})"

class IdentifierNode(ASTNode):
    def __init__(self, name): self.name = name
    def __repr__(self): return f"Id({self.name})"

class BinOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left; self.op = op; self.right = right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class AssignmentNode(ASTNode):
    def __init__(self, identifier, expression):
        self.identifier = identifier; self.expression = expression
    def __repr__(self): return f"Assign({self.identifier}, {self.expression})"

class PrintNode(ASTNode):
    def __init__(self, expression): self.expression = expression
    def __repr__(self): return f"Print({self.expression})"

class IfNode(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition; self.body = body
    def __repr__(self): return f"If({self.condition}, Block({self.body}))"

class WhileNode(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition; self.body = body
    def __repr__(self): return f"While({self.condition}, Block({self.body}))"

class ReturnNode(ASTNode):
    def __init__(self, expression):
        self.expression = expression
    def __repr__(self):
        # Handle cases where there is a bare 'return'
        if self.expression:
            return f"Return({self.expression})"
        return "Return()"


# ==========================================
# 3. THE RECURSIVE-DESCENT PARSER
# ==========================================
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_idx = 0
        self.current_token = self.tokens[self.current_token_idx] if self.tokens else None
        
        # CST Tracking State
        self.cst_root = CSTNode("<program>")
        self.cst_stack = [self.cst_root]

    def enter_rule(self, rule_name):
        """Creates a new CST node and pushes it onto the stack."""
        node = CSTNode(rule_name)
        self.cst_stack[-1].children.append(node)
        self.cst_stack.append(node)

    def exit_rule(self):
        """Pops the completed rule off the CST stack."""
        self.cst_stack.pop()

    def advance(self):
        self.current_token_idx += 1
        if self.current_token_idx < len(self.tokens):
            self.current_token = self.tokens[self.current_token_idx]
        else:
            self.current_token = None

    def match(self, expected_type, expected_value=None):
        """Matches a token and automatically logs it as a leaf in the CST."""
        if self.current_token is None:
            self.error(f"Expected {expected_type} but reached end of file.")

        token_type, token_value = self.current_token
        
        if token_type == expected_type and (expected_value is None or token_value == expected_value):
            # Log to the Concrete Syntax Tree
            self.cst_stack[-1].children.append(CSTLeaf(token_type, token_value))
            
            self.advance()
            return token_value
        else:
            val_msg = f" '{expected_value}'" if expected_value else ""
            self.error(f"Expected {expected_type}{val_msg}, got {token_type} '{token_value}'")

    def error(self, message):
        raise ParseError(f"Syntax Error: {message}")

    # --- Phase 1: Program & Statements ---
    def parse_program(self):
        self.enter_rule("<program>")
        ast = self.parse_statement_list()
        
        if self.current_token is not None:
             self.error(f"Unexpected token at end of file: {self.current_token}")
             
        self.exit_rule()
        return ast

    def parse_statement_list(self):
        self.enter_rule("<statement_list>")
        statements = []
        statements.append(self.parse_statement())
        
        while self.current_token and (
            self.current_token[0] == 'ID' or 
            (self.current_token[0] == 'KEYWORD' and self.current_token[1] in ['print', 'if', 'while'])
        ):
            statements.append(self.parse_statement())
            
        self.exit_rule()
        return statements

    def parse_statement(self):
        self.enter_rule("<statement>")
        if self.current_token is None:
            self.error("Expected statement, got EOF")

        token_type, token_value = self.current_token

        if token_type == 'ID':
            node = self.parse_assignment()
        elif token_type == 'KEYWORD':
            if token_value == 'print':
                node = self.parse_print()
            elif token_value == 'if':
                node = self.parse_if()
            elif token_value == 'while':
                node = self.parse_while()
            elif token_value == 'return':        # <-- NEW ROUTE
                node = self.parse_return()
        else:        
            self.error(f"Expected start of a statement, got {token_type} '{token_value}'")
            
        self.exit_rule()
        return node

    # --- Phase 3: Specific Statements ---
    def parse_assignment(self):
        self.enter_rule("<assignment>")
        id_val = self.match('ID')
        self.match('OP_PUNCT', '=')
        expr_node = self.parse_expression()
        self.match('NEWLINE')
        self.exit_rule()
        return AssignmentNode(IdentifierNode(id_val), expr_node)

    def parse_print(self):
        self.enter_rule("<print_stmt>")
        self.match('KEYWORD', 'print')
        self.match('OP_PUNCT', '(')
        expr_node = self.parse_expression()
        self.match('OP_PUNCT', ')')
        self.match('NEWLINE')
        self.exit_rule()
        return PrintNode(expr_node)

    def parse_if(self):
        self.enter_rule("<if_stmt>")
        self.match('KEYWORD', 'if')
        cond_node = self.parse_condition()
        self.match('OP_PUNCT', ':')
        self.match('NEWLINE')
        self.match('INDENT')
        body_nodes = self.parse_statement_list()
        self.match('DEDENT')
        self.exit_rule()
        return IfNode(cond_node, body_nodes)

    def parse_while(self):
        self.enter_rule("<while_stmt>")
        self.match('KEYWORD', 'while')
        cond_node = self.parse_condition()
        self.match('OP_PUNCT', ':')
        self.match('NEWLINE')
        self.match('INDENT')
        body_nodes = self.parse_statement_list()
        self.match('DEDENT')
        self.exit_rule()
        return WhileNode(cond_node, body_nodes)

    # --- Phase 2: Expressions & Precedence (Arithmetic & Relational Expression )---
    def parse_condition(self):
        self.enter_rule("<condition>")
        left_node = self.parse_expression()
        
        valid_rel_ops = ['<', '>', '==', '<=', '>=']
        if self.current_token and self.current_token[0] == 'OP_PUNCT' and self.current_token[1] in valid_rel_ops:
            op = self.current_token[1]
            self.match('OP_PUNCT', op)
            right_node = self.parse_expression()
            self.exit_rule()
            return BinOpNode(left_node, op, right_node)
        else:
            self.error(f"Expected relational operator ({', '.join(valid_rel_ops)}) in condition")

    def parse_expression(self):
        """Handles Addition and Subtraction (Lowest Math Precedence)"""
        self.enter_rule("<expression>")
        left_node = self.parse_term()
        
        while self.current_token and self.current_token[0] == 'OP_PUNCT' and self.current_token[1] in ['+', '-']:
            op = self.current_token[1]
            self.match('OP_PUNCT', op)
            right_node = self.parse_term()
            left_node = BinOpNode(left_node, op, right_node)
            
        self.exit_rule()
        return left_node

    def parse_term(self):
        """Handles Multiplication and Division (Medium Math Precedence)"""
        self.enter_rule("<term>")
        left_node = self.parse_factor()
        
        while self.current_token and self.current_token[0] == 'OP_PUNCT' and self.current_token[1] in ['*', '/']:
            op = self.current_token[1]
            self.match('OP_PUNCT', op)
            right_node = self.parse_factor()
            left_node = BinOpNode(left_node, op, right_node)
            
        self.exit_rule()
        return left_node

    def parse_factor(self):
        """Handles Values and Brackets (Highest Math Precedence)"""
        self.enter_rule("<factor>")
        if self.current_token is None:
            self.error("Expected factor, got EOF")

        token_type, token_value = self.current_token

        if token_type == 'NUMBER':
            val = self.match('NUMBER')
            node = NumberNode(val)
            
        elif token_type == 'STRING':
            val = self.match('STRING')
            node = StringNode(val)
            
        elif token_type == 'ID':
            val = self.match('ID')
            node = IdentifierNode(val)
            
        # BRACKET HANDLING
        elif token_type == 'OP_PUNCT' and token_value == '(':
            self.match('OP_PUNCT', '(')           
            node = self.parse_expression()        
            self.match('OP_PUNCT', ')')           
            
        else:
            self.error(f"Expected ID, NUMBER, STRING, or '(', got {token_type} '{token_value}'")
            
        self.exit_rule()
        return node
    
    def parse_return(self):
        self.enter_rule("<return_stmt>")
        self.match('KEYWORD', 'return')
        
        # Look ahead: if the next token isn't a NEWLINE, there must be an expression to return!
        if self.current_token and self.current_token[0] != 'NEWLINE':
            expr_node = self.parse_expression()
        else:
            expr_node = None
            
        self.match('NEWLINE')
        self.exit_rule()
        return ReturnNode(expr_node)


# ==========================================
# EXECUTION HOOK
# ==========================================
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python parser.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    
    try:
        with open(filename, 'r') as file:
            source_code = file.read()
            
        # 1. Scanner Phase
        print(f"--- Mini-Python Compiler Frontend ---")
        print(f"Reading file: {filename}\n")
        tokens = lex(source_code)
        
        print("--- Scanner Output (Token Stream) ---")
        for token in tokens:
            val = repr(token[1]) if token[0] in ['NEWLINE', 'STRING'] else token[1]
            print(f"Token(Type: {token[0]:<10}, Value: {val})")
        print("-" * 37 + "\n")
        
        # 2. Parser Phase
        parser = Parser(tokens)
        ast = parser.parse_program()
        
        print("✅ Parse successful!\n")
        
        # Output AST
        print("--- Abstract Syntax Tree (AST) ---")
        pprint(ast, indent=2, width=80)
        
        # Output CST
        print("\n--- Concrete Syntax Tree (CST) ---")
        # Start printing from the first child to skip the redundant root wrapper
        for child in parser.cst_root.children:
            print_cst(child)
            
    except FileNotFoundError:
        print(f"Error: Could not find file '{filename}'.")
    except Exception as e:
        print(f"\n❌ {e}")



# BNF
# <program> ::= <statement_list>
# <statement_list> ::= <statement> <statement_list_tail>
# <statement_list_tail> ::= <statement_list> | ε

# <statement> ::= <simple_stmt> | <compound_stmt>
# <simple_stmt> ::= <assignment> | <print_stmt> | <return_stmt>
#<return_stmt> ::= "return" <expression> "NEWLINE" | "return" "NEWLINE"


# <assignment> ::= "ID" "=" <expression> "NEWLINE"
# <print_stmt> ::= "print" "(" <expression> ")" "NEWLINE"

# <compound_stmt> ::= <if_stmt> | <while_stmt>
# <if_stmt> ::= "if" <condition> ":" "NEWLINE" "INDENT" <statement_list> "DEDENT"
# <while_stmt> ::= "while" <condition> ":" "NEWLINE" "INDENT" <statement_list> "DEDENT"

# <condition> ::= <expression> <rel_op> <expression>

# <expression> ::= <term> <expression_tail>
# <expression_tail> ::= <arith_op> <expression> | ε

# <term> ::= "ID" | "NUMBER" | "STRING"
# <rel_op> ::= "<" | ">"
# <arith_op> ::= "+" | "-" | "*" | "/"

# # To execute parser, run python parser.py samplesnippet.mpy

