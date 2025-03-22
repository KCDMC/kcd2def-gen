import schema
from record import from_json
from itertools import zip_longest

def generate_def(name: str, defn: schema.Definition) -> str:
    pass

def generate_defs(root: schema.Root) -> dict[str,str]:
    defs = {}
    for name, defn in root.defs.items():
        lines = []
        match type(defn):
            case schema.FunctionDefinition:
                orig_g = None
                orig_s = None
                orig_f = None
                orig_b = None
                for o in defn.orig:
                    if isinstance(o,schema.GlobalOrigin):
                        orig_g = o
                    elif isinstance(o,schema.ScriptOrigin):
                        orig_s = o
                    elif isinstance(o,schema.FileOrigin):
                        orig_f = o
                    elif isinstance(o,schema.BuiltinOrigin):
                        orig_b = o
                show = orig_b is None or orig_b.show
                if show:
                    param_data = list(zip_longest(defn.argn,defn.argt,defn.argd))
                    return_data = list(zip_longest(defn.retn,defn.rett,defn.retd))
                    if orig_g is not None:
                        params = []
                        for i,(n,t,d) in enumerate(param_data):
                            p_show = t is not None or d is not None
                            if n is None:
                                n = 'unk_'+str(i)
                            if t is None:
                                t = 'unknown'
                            if d is None:
                                d = ''
                            params.append(n)
                            if p_show:
                                lines.append(f'---@param {n} {t} {d}')
                        for i,(n,t,d) in enumerate(return_data):
                            if t is None:
                                t = 'unknown'
                            lines.append(f'---@return {t} {n} {d}')
                        if orig_f is not None:
                            lines.append(f'---@source {orig_f.file}')
                        lines.append(f"function {orig_g.path}({', '.join(params)}) end")
                    params = []
                    for i,(n,t,d) in enumerate(param_data):
                        if n is None:
                            n = 'unk_'+str(i)
                        params.append(n if t is None else f"{n}: {t}")
                    lines.append(f"---@alias {name} fun({', '.join(params)})")
                        
                    
            case schema.ClassDefinition:
                pass
            case schema.TableDefinition:
                pass
            case _:
                raise ValueError('bare definition.')
        if lines:
            defs[name] = '\n'.join(lines)+'\n'
    
    return defs

def process_file(read_path,write_path):
    data = None
    with open(read_path) as file:
        data = file.read()
    root = from_json(data)
    
    defs = generate_defs(root)
    
    with open(write_path,'w') as file:
        file.write('\n'.join(defs.values()))

if __name__ == '__main__':
    process_file('../test.json','../test.lua')    
