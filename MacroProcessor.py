from tabulate import tabulate

def read_source_file(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file.readlines()]

def process_pass1(lines):
    mnt = []  # Macro Name Table
    mdt = []  # Macro Definition Table
    ala = []  # Argument List Array
    
    current_macro = None
    macro_def = []
    in_macro = False
    mdt_index = 1  # Initialize MDT index
    ala_index = 1  # Initialize ALA index
    
    for i, line in enumerate(lines, 1):
        parts = line.split()
        if not parts:
            continue
            
        if parts[0] == 'MACRO':
            in_macro = True
            continue
            
        if in_macro:
            if current_macro is None:
                current_macro = parts[0]
                # Extract arguments and create separate entries
                args = [arg for arg in parts[1:] if arg.startswith('&')]
                if args:
                    args = [arg.strip(',') for arg in args]
                    for arg in args:
                        ala.append({
                            "index": ala_index,
                            "arguments": [arg]  # Single argument per entry
                        })
                        ala_index += 1
                
                mnt.append({
                    "index": len(mnt) + 1,
                    "macroName": current_macro,
                    "macroIndex": mdt_index  # Use current MDT index instead of line number
                })
                
                macro_def.append({"index": mdt_index, "definition": line})
                mdt_index += 1
            else:
                macro_def.append({"index": mdt_index, "definition": line})
                mdt_index += 1
                
            if parts[0] == 'MEND':
                mdt.extend(macro_def)
                in_macro = False
                macro_def = []
                current_macro = None
                
    return mnt, mdt, ala

def process_pass2(lines, mnt, mdt, ala):
    mdt_pass2 = []
    ala_pass2 = []
    ala_pass2_index = 1
    mdt_pass2_index = 1
    
    # Create mapping of macro names to their definitions and arguments
    macro_map = {}
    current_mdt_index = 0
    
    # Build macro definitions
    for entry in mnt:
        macro_name = entry["macroName"]
        macro_def = []
        is_first_line = True  # Flag to skip the first line of each macro
        
        while current_mdt_index < len(mdt):
            current_mdt_index += 1
            line_def = mdt[current_mdt_index - 1]["definition"]
            if line_def.split()[0] == "MEND":
                break
                
            # Skip the macro prototype line (first line of each macro)
            if is_first_line:
                is_first_line = False
                continue
                
            macro_def.append(mdt[current_mdt_index - 1])
            
        formal_args = []
        for line in lines:
            parts = line.split()
            if parts and parts[0] == macro_name and any(arg.startswith('&') for arg in parts[1:]):
                formal_args = [arg.strip(',') for arg in parts[1:] if arg.startswith('&')]
                break
                
        macro_map[macro_name] = {
            "definition": macro_def,
            "arguments": formal_args
        }
    
    # Process each line for macro calls
    for line in lines:
        parts = line.split()
        if not parts:
            continue
            
        macro_name = parts[0]
        if macro_name in macro_map:
            # Get actual arguments and exclude macro definition lines
            if not any(arg.startswith('&') for arg in parts[1:]):  # Only process lines with actual arguments
                actual_args = [arg.strip(',') for arg in parts[1:]]
                
                # Add to ALA Pass 2
                for actual_arg in actual_args:
                    ala_pass2.append({
                        "index": ala_pass2_index,
                        "arguments": [actual_arg]
                    })
                    ala_pass2_index += 1
                
                # Process macro expansion
                formal_args = macro_map[macro_name]["arguments"]
                arg_mapping = dict(zip(formal_args, actual_args))
                
                # Add expanded macro definition (excluding prototype line)
                for macro_line in macro_map[macro_name]["definition"]:
                    new_line = macro_line["definition"]
                    for formal, actual in arg_mapping.items():
                        new_line = new_line.replace(formal, actual)
                    mdt_pass2.append({
                        "index": mdt_pass2_index,
                        "definition": new_line
                    })
                    mdt_pass2_index += 1
                
                # Add MEND statement
                mdt_pass2.append({
                    "index": mdt_pass2_index,
                    "definition": "MEND"
                })
                mdt_pass2_index += 1
    
    return mdt_pass2, ala_pass2

def print_tables(mnt, mdt, ala, mdt_pass2, ala_pass2):
    # MNT Table (Pass 1)
    mnt_headers = ["Index", "MacroName", "MacroIndex"]
    mnt_data = [[entry["index"], entry["macroName"], entry["macroIndex"]] for entry in mnt]
    print("\nMNT Table (Pass 1):")
    print(tabulate(mnt_data, headers=mnt_headers, tablefmt="grid"))
    
    # MDT Table (Pass 1)
    mdt_headers = ["Index", "Definition"]
    mdt_data = [[entry["index"], entry["definition"]] for entry in mdt]
    print("\nMDT Table (Pass 1):")
    print(tabulate(mdt_data, headers=mdt_headers, tablefmt="grid"))
    
    # ALA Table (Pass 1)
    ala_headers = ["Index", "Arguments"]
    ala_data = [[entry["index"], ", ".join(entry["arguments"])] for entry in ala]
    print("\nALA Table (Pass 1):")
    print(tabulate(ala_data, headers=ala_headers, tablefmt="grid"))
    
    # MDT Table (Pass 2)
    mdt_pass2_headers = ["Index", "Definition"]
    mdt_pass2_data = [[entry["index"], entry["definition"]] for entry in mdt_pass2]
    print("\nMDT Table (Pass 2):")
    print(tabulate(mdt_pass2_data, headers=mdt_pass2_headers, tablefmt="grid"))
    
    # ALA Table (Pass 2)
    ala_pass2_headers = ["Index", "Arguments"]
    ala_pass2_data = [[entry["index"], ", ".join(entry["arguments"])] for entry in ala_pass2]
    print("\nALA Table (Pass 2):")
    print(tabulate(ala_pass2_data, headers=ala_pass2_headers, tablefmt="grid"))

def main():
    # Read and process the source file
    lines = read_source_file('source.txt')
    mnt, mdt, ala = process_pass1(lines)
    mdt_pass2, ala_pass2 = process_pass2(lines, mnt, mdt, ala)
    print_tables(mnt, mdt, ala, mdt_pass2, ala_pass2)

if __name__ == "__main__":
    main()