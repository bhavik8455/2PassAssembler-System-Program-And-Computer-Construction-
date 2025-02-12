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
        
    def parse_instruction(self, statement: str) -> Tuple[str, str]:
        parts = statement.replace(',', ' ').split()
        
        if not parts:
            return statement, ''
            
        if 'START' in parts[0]:
            self.address = int(parts[1])
            return statement, f"(AD,{self.pot['START']}) - (C, {self.address})"
            
        if parts[0] == 'END':
            output_lines, self.address = self.allocate_literals(self.pot['END'])
            return statement, output_lines or f"{self.address} (AD,{self.pot['END']}) - -"
            
        if parts[0] == 'LTORG':
            output_lines, self.address = self.allocate_literals(self.pot['LTORG'])
            return statement, output_lines
            
        if parts[0] == 'ORIGIN':
            self.address = self.evaluate_expression(parts[1])
            return statement, ''
            
        if len(parts) > 1 and parts[1] == 'EQU':
            self.symbol_table[parts[0]] = str(self.evaluate_expression(parts[2]))
            return statement, ''
            
        if parts[0] in self.dl or (len(parts) > 1 and parts[1] in self.dl):
            return self.handle_declaration(parts)
            
        return self.handle_regular_instruction(parts)
    
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
    
    def handle_regular_instruction(self, parts: List[str]) -> Tuple[str, str]:
        if len(parts) == 1 and parts[0] == 'STOP':
            output = f"{self.address} (IS,{self.mot['STOP']}) - -"
            self.address += 1
            return 'STOP', output
            
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
        return ' '.join(parts), output
    
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
            for symbol, value in self.symbol_table.items():
                if symbol in expr and value:
                    expr = expr.replace(symbol, value)
            return eval(expr)
    
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
                
            if '(S,' in intermediate or '(L,' in intermediate:
                parts = intermediate.split()
                if len(parts) >= 4:
                    table_type, index = parts[3].strip('()').split(',')
                    index = int(index) - 1
                    
                    if table_type == 'S':
                        lc = list(self.symbol_table.values())[index]
                    else:
                        lc = list(self.literal_table.values())[index]
                        
                    machine_code.append((statement, 
                                      f"{parts[0]} {' '.join(parts[1:3])} {lc}"))
                else:
                    machine_code.append((statement, intermediate))
            else:
                cleaned = ''.join(c for c in intermediate 
                                if c.isdigit() or c.isspace() or c == '-')
                machine_code.append((statement, cleaned))
                
        return machine_code

def display_combined_output(pass1_output: List[Tuple[str, str]], 
                          pass2_output: List[Tuple[str, str]]) -> None:
    combined_output = []
    for (source, intermediate), (_, machine) in zip(pass1_output, pass2_output):
        combined_output.append([source, intermediate, machine])
    
    print('\n 2 Pass Assembly Output:')
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
    assembly_code = '''START 200
MOVER AREG, '=5'
MOVER BREG, '=1'
MOVEM BREG, A
LTORG
MOVER CREG, '=3'
MOVER DREG, '=1'
ADD CREG, B
LTORG
MOVER BREG, '=5'
MULT BREG, A
PRINT A
STOP 
A DS 1
B DC 2
END'''

    run_assembler(assembly_code)

