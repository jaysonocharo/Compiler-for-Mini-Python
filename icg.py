import sys 
from pprint import pprint  

try:
    from scanner import lex 
    from parser import (Parser, NumberNode, StringNode, IdentifierNode, 
                        BinOpNode, AssignmentNode, PrintNode, IfNode, 
                        WhileNode, ReturnNode, print_cst)
except ImportError as e:
    print(f"Error importing frontend modules: {e}")
    sys.exit(1)

class ICGenerator:
    def __init__(self):
        self.quadruples = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self):
        """Generates a new temporary variable (e.g., t0, t1, t2)."""
        temp = f"t{self.temp_count}"
        self.temp_count += 1
        return temp

    def new_label(self):
        """Generates a new label for control flow (e.g., L0, L1, L2)."""
        label = f"L{self.label_count}"
        self.label_count += 1
        return label

    def add_quad(self, op, arg1, arg2, result):
        """Appends a new quadruple to the intermediate code list."""
        self.quadruples.append((op, arg1, arg2, result))

    def generate(self, ast):
        """Entry point for the generator. Expects a list of AST statements."""
        for stmt in ast:
            self.visit(stmt)
        return self.quadruples

    def visit(self, node):
        """Dispatcher that calls the specific visit method based on node type."""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"No visit_{type(node).__name__} method defined.")

    # --- Visit Methods for AST Nodes ---
    def visit_NumberNode(self, node):
        return node.value

    def visit_StringNode(self, node):
        return node.value

    def visit_IdentifierNode(self, node):
        return node.name

    def visit_BinOpNode(self, node):
        left_val = self.visit(node.left)
        right_val = self.visit(node.right)
        temp = self.new_temp()
        self.add_quad(node.op, left_val, right_val, temp)
        return temp

    def visit_AssignmentNode(self, node):
        expr_result = self.visit(node.expression)
        id_name = node.identifier.name
        self.add_quad('=', expr_result, '', id_name)

    def visit_WhileNode(self, node):
        start_label = self.new_label()
        end_label = self.new_label()
        self.add_quad('LABEL', start_label, '', '')
        cond_result = self.visit(node.condition)
        self.add_quad('IFFALSE', cond_result, '', end_label)
        for stmt in node.body:
            self.visit(stmt)
        self.add_quad('GOTO', start_label, '', '')
        self.add_quad('LABEL', end_label, '', '')

    def visit_IfNode(self, node):
        end_label = self.new_label()
        cond_result = self.visit(node.condition)
        self.add_quad('IFFALSE', cond_result, '', end_label)
        for stmt in node.body:
            self.visit(stmt)
        self.add_quad('LABEL', end_label, '', '')

    def visit_PrintNode(self, node):
        expr_result = self.visit(node.expression)
        self.add_quad('PRINT', expr_result, '', '')

    def visit_ReturnNode(self, node):
        if node.expression:
            expr_result = self.visit(node.expression)
            self.add_quad('RETURN', expr_result, '', '')
        else:
            self.add_quad('RETURN', '', '', '')

def print_tac(quads):
    """Utility function to print quadruples as Linear Three-Address Code."""
    print(">> Linear TAC:")
    for op, arg1, arg2, res in quads:
        arg1 = str(arg1) if arg1 else ""
        arg2 = str(arg2) if arg2 else ""
        res = str(res) if res else ""
        if op == 'LABEL':
            print(f"{arg1}:")
        elif op == '=':
            print(f"  {res} = {arg1}")
        elif op in ('+', '-', '*', '/', '<', '>', '==', '<=', '>='):
            print(f"  {res} = {arg1} {op} {arg2}")
        elif op == 'IFFALSE':
            print(f"  if not {arg1} goto {res}")
        elif op == 'GOTO':
            print(f"  goto {arg1}")
        elif op == 'PRINT':
            print(f"  print {arg1}")
        elif op == 'RETURN':
            val = f" {arg1}" if arg1 else ""
            print(f"  return{val}")
    print()

def print_quadruples(quads):
    """Utility function to print quadruples in a legible table format."""
    print(">> Quadruple Table:")
    print(f"{'OP':<10} | {'ARG 1':<10} | {'ARG 2':<10} | {'RESULT':<10}")
    print("-" * 50)
    for op, arg1, arg2, res in quads:
        arg1 = str(arg1) if arg1 else ""
        arg2 = str(arg2) if arg2 else ""
        res = str(res) if res else ""
        if op == 'LABEL':
            print(f"{arg1 + ':':<48}")
        else:
            print(f"{op:<10} | {arg1:<10} | {arg2:<10} | {res:<10}")

# ========================================== 
# EXECUTION HOOK (The Full Compiler Pipeline) 
# ========================================== 
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python icg.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    
    try:
        with open(filename, 'r') as file:
            source_code = file.read()
            
        print(f"==========================================")
        print(f"        MINI-PYTHON COMPILER PIPELINE     ")
        print(f"==========================================\n")
        
        # 0. Original Code
        print(f"--- 0. SOURCE CODE ---")
        print(source_code)
        print("-" * 42 + "\n")
        
        # 1. Lexical Analysis
        print("--- 1. SCANNER OUTPUT (TOKEN STREAM) ---")
        tokens = lex(source_code)
        for token in tokens:
            val = repr(token[1]) if token[0] in ['NEWLINE', 'STRING'] else token[1]
            print(f"Token(Type: {token[0]:<10}, Value: {val})")
        print("-" * 42 + "\n")
        
        # 2. Syntax Analysis
        print("--- 2. PARSER OUTPUT (AST & CST) ---")
        # FIX: Passed source_code so the error formatter has context
        parser = Parser(tokens, source_code)
        ast = parser.parse_program()
        
        # --- STRICT CPYTHON BEHAVIOR: Halt on Syntax Errors ---
        if hasattr(parser, 'errors') and parser.errors:
            print(f"\n❌ BUILD FAILED: Found {len(parser.errors)} Syntax Error(s)\n")
            # FIX: Loop through and print the errors one by one!
            for err in parser.errors:
                print(err)
            print("\nCannot generate ICG for broken code.\n")
            sys.exit(1)
            
        print(">> Abstract Syntax Tree (AST):")
        pprint(ast, indent=2, width=80)
        
        # print("\n>> Concrete Syntax Tree (CST):")
        # for child in parser.cst_root.children:
        #     print_cst(child)
        # print("-" * 42 + "\n")

        print("\n>> Concrete Syntax Tree (CST):")
        print_cst(parser.cst_root)
        print("-" * 42 + "\n")
        
        # 3. Intermediate Code Generation
        print("--- 3. INTERMEDIATE CODE GENERATOR OUTPUT ---")
        generator = ICGenerator()
        quadruples = generator.generate(ast)
        
        print_tac(quadruples)
        print_quadruples(quadruples)
        
    except Exception as e:
        print(f"\n❌ Compiler Error: {e}")


