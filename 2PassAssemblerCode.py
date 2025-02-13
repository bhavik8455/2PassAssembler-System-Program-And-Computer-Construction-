from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from tabulate import tabulate
from collections import defaultdict

@dataclass
class Assembler:
    mot: Dict[str, str] = field(default_factory=lambda: {
        'STOP': '00', 'ADD': '01', 'SUB': '02', 'MULT': '03', 'MOVER': '04',
        'MOVEM': '05', 'COMP': '06', 'BC': '07', 'DIV': '08', 'READ': '09', 'PRINT': '10'
    })
    pot: Dict[str, str] = field(default_factory=lambda: {
        'START': '01', 'END': '02', 'ORIGIN': '03', 'EQU': '04', 'LTORG': '05'
    })
    dl: Dict[str, str] = field(default_factory=lambda: {'DC': '01', 'DS': '02'})
    registers: Dict[str, str] = field(default_factory=lambda: {
        'AREG': '01', 'BREG': '02', 'CREG': '03', 'DREG': '04'
    })
    
    def __post_init__(self):
        self.address = 0
        self.symbol_table = {}
        self.literal_table = {}
        self.duplicate_literals = {}
        self.pool_table = []
    
    def process_label(self, statement: str) -> Tuple[str, str]:
        parts = [part.strip() for part in statement.split(':')]
        if len(parts) > 1:
            label = parts[0]
            rest = parts[1]
            self.symbol_table[label] = str(self.address)
            return rest
        return statement
    
    def parse_instruction(self, statement: str) -> Tuple[str, str]:
        original_statement = statement
        statement = self.process_label(statement)
        
        parts = statement.replace(',', ' ').split()
        
        if not parts:
            return original_statement, ''
            
        if 'START' in parts[0]:
            self.address = int(parts[1])
            return original_statement, f"(AD,{self.pot['START']}) - (C, {self.address})"
            
        if parts[0] == 'END':
            output_lines, self.address = self.allocate_literals(self.pot['END'])
            return original_statement, output_lines or f"{self.address} (AD,{self.pot['END']}) - -"
            
        if parts[0] == 'LTORG':
            output_lines, self.address = self.allocate_literals(self.pot['LTORG'])
            return original_statement, output_lines
            
        if parts[0] == 'ORIGIN':
            try:
                expr = ' '.join(parts[1:])
                self.address = self.evaluate_expression(expr)
                return original_statement, ''
            except Exception as e:
                print(f"Error evaluating ORIGIN expression: {e}")
                return original_statement, ''
            
        if len(parts) > 1 and parts[1] == 'EQU':
            try:
                value = self.evaluate_expression(' '.join(parts[2:]))
                self.symbol_table[parts[0]] = str(value)
                return original_statement, ''
            except Exception as e:
                print(f"Error evaluating EQU expression: {e}")
                return original_statement, ''
            
        if parts[0] in self.dl or (len(parts) > 1 and parts[1] in self.dl):
            return self.handle_declaration(parts)
            
        return self.handle_regular_instruction(parts, original_statement)
    
    def handle_declaration(self, parts: List[str]) -> Tuple[str, str]:
        if len(parts) == 3:
            symbol, mnemonic, value = parts
            self.symbol_table[symbol] = str(self.address)
        else:
            mnemonic, value = parts
            
        dl_code = self.dl[mnemonic]
        output = ''
        
        if '=' in value:
            lit_index = self.add_literal(value)
            output = f"{self.address} (DL,{dl_code}) - (L,{lit_index})"
            self.address += 1
        else:
            size = 1 if dl_code == '01' else int(value)
            output = f"{self.address} (DL,{dl_code}) - {str(value).zfill(3)}"
            self.address += size
            
        return ' '.join(parts), output
    
    def handle_regular_instruction(self, parts: List[str], original_statement: str) -> Tuple[str, str]:
        if len(parts) == 1 and parts[0] == 'STOP':
            output = f"{self.address} (IS,{self.mot['STOP']}) - -"
            self.address += 1
            return original_statement, output
            
        if len(parts) > 2 and parts[1] in self.mot:
            self.symbol_table[parts[0]] = str(self.address)
            parts = parts[1:]
            
        mnemonic = parts[0]
        mot_code = self.mot.get(mnemonic, '')
        
        if len(parts) == 2:
            target = parts[1]
            if target not in self.symbol_table:
                self.symbol_table[target] = ''
            sym_index = list(self.symbol_table.keys()).index(target) + 1
            output = f"{self.address} (IS,{mot_code}) - (S,{sym_index})"
        else:
            reg = self.registers.get(parts[1].strip(','), '')
            target = parts[2]
            
            if '=' in target:
                lit_index = self.add_literal(target)
                output = f"{self.address} (IS,{mot_code}) {reg} (L,{lit_index})"
            else:
                if target not in self.symbol_table:
                    self.symbol_table[target] = ''
                sym_index = list(self.symbol_table.keys()).index(target) + 1
                output = f"{self.address} (IS,{mot_code}) {reg} (S,{sym_index})"
                
        self.address += 1
        return original_statement, output
    
    def add_literal(self, literal: str) -> int:
        if literal in self.literal_table:
            self.duplicate_literals[literal] = literal.strip("'")
            stripped_literal = literal.strip("'")
            self.literal_table[stripped_literal] = ''
            return list(self.literal_table.keys()).index(stripped_literal) + 1
        else:
            self.literal_table[literal] = ''
            return len(self.literal_table)
    
    def evaluate_expression(self, expr: str) -> int:
        try:
            return int(expr)
        except ValueError:
            modified_expr = expr
            for symbol, value in self.symbol_table.items():
                if symbol in expr and value:
                    modified_expr = modified_expr.replace(symbol, value)
            parts = modified_expr.split()
            if len(parts) == 3 and parts[1] in ['+', '-']:
                try:
                    left = int(parts[0])
                    right = int(parts[2])
                    if parts[1] == '+':
                        return left + right
                    else:
                        return left - right
                except ValueError:
                    raise ValueError(f"Unable to evaluate expression: {expr}")
            else:
                return int(modified_expr)
    
    def allocate_literals(self, end_value: str) -> Tuple[str, int]:
        if not self.literal_table:
            return '', self.address
            
        output_lines = []
        min_index = float('inf')
        
        for lit, value in self.literal_table.items():
            if not value:
                curr_index = list(self.literal_table.keys()).index(lit) + 1
                min_index = min(min_index, curr_index)
                
                self.literal_table[lit] = str(self.address)
                lit_value = str(lit.strip("'=")).zfill(3)
                output_lines.append(f"{self.address} (AD,{end_value}) - {lit_value}")
                self.address += 1
                
        if output_lines:
            self.pool_table.append(min_index)
            
        return '\n'.join(output_lines), self.address
    
    def pass1(self, assembly_code: str) -> List[Tuple[str, str]]:
        return [self.parse_instruction(stmt.strip()) 
                for stmt in assembly_code.strip().split('\n')
                if stmt.strip()]
    
    def pass2(self, pass1_output: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        machine_code = []
        
        for statement, intermediate in pass1_output:
            if not intermediate:
                machine_code.append((statement, ''))
                continue
                
            if isinstance(intermediate, list):
                intermediate = '\n'.join(intermediate)
            
            lc = intermediate.split()[0] if intermediate.split() else ''
            
            if '(S,' in intermediate or '(L,' in intermediate:
                parts = intermediate.split()
                if len(parts) >= 4:
                    table_type, index = parts[3].strip('()').split(',')
                    index = int(index) - 1
                    
                    if table_type == 'S':
                        address = list(self.symbol_table.values())[index]
                    else:
                        address = list(self.literal_table.values())[index]
                    
                    if len(parts) >= 3:
                        machine_code.append((statement, 
                                          f"{lc} {parts[1].split(',')[1].strip(')')} {parts[2].strip('()')} {address}"))
                    else:
                        machine_code.append((statement, 
                                          f"{lc} {parts[1].split(',')[1].strip(')')} - {address}"))
                else:
                    cleaned = ' '.join(part.split(',')[1].strip('()')
                                     if ',' in part else part.strip('()')
                                     for part in intermediate.split())
                    machine_code.append((statement, cleaned))
            else:
                cleaned = ' '.join(part.split(',')[1].strip('()')
                                 if ',' in part else part.strip('()')
                                 for part in intermediate.split())
                machine_code.append((statement, cleaned))
                
        return machine_code

def display_combined_output(pass1_output: List[Tuple[str, str]], 
                          pass2_output: List[Tuple[str, str]]) -> None:
    combined_output = []
    for (source, intermediate), (_, machine) in zip(pass1_output, pass2_output):
        combined_output.append([source, intermediate, machine])
    
    print('\nCombined Assembly Output:')
    print(tabulate(combined_output, 
                  headers=["Source Code", "Intermediate Code", "Machine Code"], 
                  tablefmt="grid"))

def display_tables(assembler: Assembler) -> None:
    print('\nSymbol Table:')
    symbol_tab = [(i+1, sym, val) for i, (sym, val) 
                 in enumerate(assembler.symbol_table.items())]
    print(tabulate(symbol_tab, 
                  headers=["Index", "Symbol", "Address"], 
                  tablefmt="grid"))
    
    if assembler.literal_table:
        print('\nLiteral Table:')
        literal_tab = [(i+1, lit, val) for i, (lit, val) 
                      in enumerate(assembler.literal_table.items())]
        print(tabulate(literal_tab, 
                      headers=["Index", "Literal", "Address"], 
                      tablefmt="grid"))
    
    if assembler.pool_table:
        print('\nPool Table:')
        pool_tab = [(i+1, entry) for i, entry 
                   in enumerate(assembler.pool_table)]
        print(tabulate(pool_tab, 
                      headers=["Index", "Literal Number"], 
                      tablefmt="grid"))

def run_assembler(code: str) -> None:
    assembler = Assembler()
    pass1_output = assembler.pass1(code)
    pass2_output = assembler.pass2(pass1_output)
    display_combined_output(pass1_output, pass2_output)
    display_tables(assembler)

if __name__ == "__main__":
    assembly_code = '''START 100
A DS 3
L1: MOVER AREG, B
ADD AREG, C
MOVEM AREG, D
D EQU A + 1
L2: PRINT D
ORIGIN A - 1
C  DC '=5'
ORIGIN L2 + 1
STOP
B DC '=19'
END'''

    run_assembler(assembly_code)