import sys
import re

# Token specifications derived from Group 10 Lexeme Specification
TOKEN_SPECIFICATION = [
    ('STRING',   r'"(?:\\.|[^"\\])*"'),    # String literal [cite: 21, 77]
    ('NUMBER',   r'\d+'),                  # Integer numbers [cite: 21, 77]
    ('ID',       r'[a-zA-Z_][a-zA-Z0-9_]*'), # Identifiers [cite: 21, 76]
    ('OP_PUNCT', r'[=+\-*/<>\:\(\)]'),     # Operators and Punctuation [cite: 21, 77]
    ('MISMATCH', r'.')                     # Catch-all for unexpected characters
]

KEYWORDS = {'if', 'while', 'print', 'return'} # Exact literal keyword matches [cite: 21, 77]

def lex(code):
    tokens = []
    # Combine regular expressions into one master regex for the DFA
    tok_re = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in TOKEN_SPECIFICATION)
    
    indent_stack = [0] # Stack to keep track of indentation levels contextually 
    
    # Split code into lines to handle INDENT/NEWLINE/DEDENT
    lines = code.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        # 1. Calculate Indentation
        indent_match = re.match(r'^[ \t]*', line)
        indentation = indent_match.group(0)
        indent_level = len(indentation)
        
        stripped_line = line[indent_level:]
        
        # Skip empty lines
        if not stripped_line:
            continue
            
        # 2. Handle INDENT / DEDENT based on the stack 
        if indent_level > indent_stack[-1]:
            indent_stack.append(indent_level)
            tokens.append(('INDENT', indentation))
        elif indent_level < indent_stack[-1]:
            while indent_level < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(('DEDENT', ''))
            if indent_level != indent_stack[-1]:
                raise RuntimeError(f"IndentationError at line {line_num}")
                
        # 3. Tokenize the rest of the line
        for mo in re.finditer(tok_re, stripped_line):
            kind = mo.lastgroup
            value = mo.group()
            
            if kind == 'MISMATCH':
                if value.strip() == '':
                    continue # Ignore intra-line whitespace
                raise RuntimeError(f'Unexpected character {value!r} on line {line_num}')
                
            # Check if an identifier is actually a keyword
            if kind == 'ID' and value in KEYWORDS:
                kind = 'KEYWORD'
                
            tokens.append((kind, value))
            
        # Emitted at the end of a physical line of code [cite: 21, 77]
        tokens.append(('NEWLINE', '\\n')) 
        
    # 4. Handle end of file DEDENTs
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(('DEDENT', ''))
        
    return tokens

if __name__ == '__main__':
    # Check if the user provided a filename argument
    if len(sys.argv) < 2:
        print("Usage: python scanner.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    
    try:
        # Open and read the external source code file
        with open(filename, 'r') as file:
            source_code = file.read()

        print(f"--- Mini-Python Scanner Output for '{filename}' ---\n")
        tokens = lex(source_code)
        
        for token in tokens:
            print(f"Token(Type: {token[0]:<10}, Value: {token[1]})")
            
    except FileNotFoundError:
        print(f"Error: Could not find file '{filename}'.")
    except RuntimeError as e:
        print(f"Lexical Error: {e}")