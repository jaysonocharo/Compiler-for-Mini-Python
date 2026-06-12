# parser2.py

import sys
from pprint import pprint

try:
    from scanner import lex
except ImportError:
    print("Error: Could not import 'lex' from scanner.py.")
    sys.exit(1)

# ==========================================
# CONCRETE SYNTAX TREE (CST)
# ==========================================
class CSTNode:
    def __init__(self, name):
        self.name = name
        self.children = []

    def add_child(self, child):
        if child:
            self.children.append(child)
        return child

class CSTLeaf:
    def __init__(self, token_type, value):
        self.token_type = token_type
        self.value = value

# --- Imported from parser.py: properly formatted CST printer ---
def print_cst(node, prefix="", is_last=True):
    """Recursively prints the CST in a clean ASCII tree format."""
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
# ABSTRACT SYNTAX TREE (AST) NODES
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
        self.left, self.op, self.right = left, op, right
    def __repr__(self): return f"BinOp({self.left} {self.op} {self.right})"

class AssignmentNode(ASTNode):
    def __init__(self, identifier, expression):
        self.identifier, self.expression = identifier, expression
    def __repr__(self): return f"Assign({self.identifier}, {self.expression})"

class PrintNode(ASTNode):
    def __init__(self, expression): self.expression = expression
    def __repr__(self): return f"Print({self.expression})"

class IfNode(ASTNode):
    def __init__(self, condition, body):
        self.condition, self.body = condition, body
    def __repr__(self): return f"If({self.condition}, Block({self.body}))"

class WhileNode(ASTNode):
    def __init__(self, condition, body):
        self.condition, self.body = condition, body
    def __repr__(self): return f"While({self.condition}, Block({self.body}))"

class ReturnNode(ASTNode):
    def __init__(self, expression=None): self.expression = expression
    def __repr__(self): return f"Return({self.expression})"

# ==========================================
# THE ERROR-RECOVERING PARSER
# ==========================================
class Parser:
    def __init__(self, tokens, source_code=""):
        self.tokens = tokens
        self.source_code = source_code
        self.source_lines = source_code.splitlines() if source_code else []
        self.last_error_line = 0
        self.current_token_idx = 0
        self.current_token = self.tokens[self.current_token_idx] if self.tokens else None
        self.errors = []
        self.current_line_idx = 0
        # CST root — kept consistent with parser.py naming style
        self.cst_root = CSTNode("<program>")
        self.cst_stack = [self.cst_root]

    # --- CST stack management (imported from parser.py pattern) ---
    def enter_rule(self, rule_name):
        """Creates a new CST node and pushes it onto the stack."""
        node = CSTNode(rule_name)
        self.cst_stack[-1].children.append(node)
        self.cst_stack.append(node)
        return node

    def exit_rule(self):
        """Pops the completed rule off the CST stack."""
        if len(self.cst_stack) > 1:
            self.cst_stack.pop()

    # def advance(self):
    #     self.current_token_idx += 1
    #     self.current_token = (
    #         self.tokens[self.current_token_idx]
    #         if self.current_token_idx < len(self.tokens)
    #         else None
    #     )
    def advance(self):
        # Increment the line tracker if we are moving past a newline
        if self.current_token and self.current_token[0] == 'NEWLINE':
            self.current_line_idx += 1
            
        self.current_token_idx += 1
        self.current_token = (
            self.tokens[self.current_token_idx]
            if self.current_token_idx < len(self.tokens)
            else None
        )
    
    
    def error(self, message):
        """Generates a user-friendly error with a visual caret pointer."""
        token_type = self.current_token[0] if self.current_token else "EOF"
        token_val = self.current_token[1] if self.current_token else "EOF"
        error_details = f"Syntax Error: {message}"

        if self.source_lines and self.current_line_idx < len(self.source_lines):
            line_idx = self.current_line_idx
            formatted_line = self.source_lines[line_idx].strip()
            
            # Place the caret at the end of the line for newlines/EOF
            if token_type in ['NEWLINE', 'EOF']:
                indent_idx = len(formatted_line)
            else:
                # Find the token visually on the current line
                indent_idx = formatted_line.find(str(token_val))
                if indent_idx == -1:
                    indent_idx = len(formatted_line) # Fallback
                
            visual = f"  ➜ Line {line_idx+1}: {formatted_line}\n"
            visual += " " * (indent_idx + 13) + "^\n"
            
            error_details = f"{visual}      {error_details}"

        self.errors.append(error_details)
        raise Exception("ParseError")

    def synchronize(self):
        """Skips tokens to find the start of the next statement."""
        # self.advance()
        # while self.current_token is not None:
        #     if self.current_token[0] == 'NEWLINE':
        #         self.advance()
        #         return
        #     if self.current_token[0] == 'KEYWORD' and self.current_token[1] in ['if', 'while', 'print', 'return']:
        #         return
        #     self.advance()

        # Remove the unconditional self.advance() here
        while self.current_token is not None:
            if self.current_token[0] == 'NEWLINE':
                self.advance() # Consume the newline and stop
                return
            if self.current_token[0] == 'KEYWORD' and self.current_token[1] in ['if', 'while', 'print', 'return']:
                return
            self.advance() # Advance only if we haven't found a sync point

    def match(self, expected_type, expected_value=None):
        if self.current_token is None:
            self.error(f"Expected {expected_type} but reached EOF")
            return "ERROR_VAL"

        token_type, token_value = self.current_token
        if token_type == expected_type and (expected_value is None or token_value == expected_value):
            # Log leaf to CST stack (imported from parser.py match pattern)
            self.cst_stack[-1].children.append(CSTLeaf(token_type, token_value))
            self.advance()
            return token_value
        else:
            val_msg = f" '{expected_value}'" if expected_value else ""
            self.error(f"Expected {expected_type}{val_msg}, got '{token_value}'")
            return "ERROR_VAL"

    # === Program & Statements ===
    def parse_program(self):
        self.enter_rule("<statement_list>")
        statements = self._parse_statement_list_body()
        self.exit_rule()
        return statements

    def _parse_statement_list_body(self):
        """Core loop for parsing a list of statements until DEDENT or EOF."""
        statements = []
        while self.current_token is not None and self.current_token[0] not in ['DEDENT']:
            try:
                stmt = self.parse_statement()
                if stmt:
                    statements.append(stmt)
            except Exception:
                self.synchronize()
        return statements

    def parse_statement(self):
        self.enter_rule("<statement>")
        node = None
        try:
            if self.current_token is None:
                self.error("Expected statement, got EOF")

            token_type, token_value = self.current_token

            if token_type == 'ID':
                node = self.parse_assignment()
            elif token_type == 'KEYWORD':
                if token_value == 'print':   node = self.parse_print()
                elif token_value == 'if':    node = self.parse_if()
                elif token_value == 'while': node = self.parse_while()
                elif token_value == 'return': node = self.parse_return()
                else:
                    self.error(f"Unexpected keyword '{token_value}'")
            else:
                self.error(f"Unexpected token '{token_value}'")
        except Exception:
            self.exit_rule()
            raise

        self.exit_rule()
        return node

    def parse_assignment(self):
        self.enter_rule("<assignment>")
        id_val = self.match('ID')
        self.match('OP_PUNCT', '=')
        expr = self.parse_expression()
        self.match('NEWLINE')
        self.exit_rule()
        return AssignmentNode(IdentifierNode(id_val), expr)

    def parse_print(self):
        self.enter_rule("<print_stmt>")
        self.match('KEYWORD', 'print')
        self.match('OP_PUNCT', '(')
        expr = self.parse_expression()
        self.match('OP_PUNCT', ')')
        self.match('NEWLINE')
        self.exit_rule()
        return PrintNode(expr)

    def parse_if(self):
        self.enter_rule("<if_stmt>")
        self.match('KEYWORD', 'if')
        cond = self.parse_condition()
        self.match('OP_PUNCT', ':')
        self.match('NEWLINE')
        self.match('INDENT')
        self.enter_rule("<statement_list>")
        body = self._parse_statement_list_body()
        self.exit_rule()
        self.match('DEDENT')
        self.exit_rule()
        return IfNode(cond, body)

    def parse_while(self):
        self.enter_rule("<while_stmt>")
        self.match('KEYWORD', 'while')
        cond = self.parse_condition()
        self.match('OP_PUNCT', ':')
        self.match('NEWLINE')
        self.match('INDENT')
        self.enter_rule("<statement_list>")
        body = self._parse_statement_list_body()
        self.exit_rule()
        self.match('DEDENT')
        self.exit_rule()
        return WhileNode(cond, body)

    def parse_return(self):
        self.enter_rule("<return_stmt>")
        self.match('KEYWORD', 'return')
        if self.current_token and self.current_token[0] != 'NEWLINE':
            expr = self.parse_expression()
        else:
            expr = None
        self.match('NEWLINE')
        self.exit_rule()
        return ReturnNode(expr)

    def parse_condition(self):
        self.enter_rule("<condition>")
        left = self.parse_expression()
        if self.current_token and self.current_token[1] in ['<', '>', '==']:
            op = self.current_token[1]
            self.cst_stack[-1].children.append(CSTLeaf(self.current_token[0], op))
            self.advance()
            right = self.parse_expression()
            self.exit_rule()
            return BinOpNode(left, op, right)
        self.error("Missing relational operator (<, >, ==)")
        return left

    def parse_expression(self):
        self.enter_rule("<expression>")
        left = self.parse_term()
        while self.current_token and self.current_token[1] in ['+', '-']:
            op = self.current_token[1]
            self.cst_stack[-1].children.append(CSTLeaf(self.current_token[0], op))
            self.advance()
            right = self.parse_term()
            left = BinOpNode(left, op, right)
        self.exit_rule()
        return left

    def parse_term(self):
        self.enter_rule("<term>")
        left = self.parse_factor()
        while self.current_token and self.current_token[1] in ['*', '/']:
            op = self.current_token[1]
            self.cst_stack[-1].children.append(CSTLeaf(self.current_token[0], op))
            self.advance()
            right = self.parse_factor()
            left = BinOpNode(left, op, right)
        self.exit_rule()
        return left

    def parse_factor(self):
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
        elif token_type == 'OP_PUNCT' and token_value == '(':
            self.match('OP_PUNCT', '(')
            node = self.parse_expression()
            self.match('OP_PUNCT', ')')
        else:
            self.error(f"Expected a variable or number, but got '{token_value}'")
            node = IdentifierNode("ERR")

        self.exit_rule()
        return node


# ==========================================
# EXECUTION HOOK
# ==========================================
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python parser2.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, 'r') as file:
            source_code = file.read()

        print(f"\n--- Compiling: {filename} ---")
        tokens = lex(source_code)

        print("\n>> SCANNER OUTPUT (TOKENS):")
        for token in tokens:
            t_type, t_val = token
            display_val = repr(t_val) if t_type in ['NEWLINE', 'STRING'] else t_val
            print(f"  Token(Type: {t_type:<10}, Value: {display_val})")
        print("-" * 50)

        parser = Parser(tokens, source_code)
        ast = parser.parse_program()

        if parser.errors:
            # --- Errors found: show errors only, suppress AST and CST ---
            print(f"\n❌ BUILD FAILED: Found {len(parser.errors)} Error(s)\n")
            for err in parser.errors:
                print(err)
                print()
            print("[Tip] Fix these syntax errors to successfully compile your code.")
        else:
            # --- No errors: show success, AST, and formatted CST ---
            print("✅ Parse successful!\n")

            print("--- Abstract Syntax Tree (AST) ---")
            pprint(ast, indent=2, width=80)

            print("\n--- Concrete Syntax Tree (CST) ---")
            print_cst(parser.cst_root)

    except FileNotFoundError:
        print(f"\n❌ Critical Compiler Failure: File '{filename}' not found.")
    except Exception as e:
        print(f"\n❌ Critical Compiler Failure: {e}")