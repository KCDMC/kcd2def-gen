import schema
from record import from_json
from itertools import zip_longest

NAMESPACE = 'kcd2def'

def type_union(t):
    if t is None:
        return 'unknown'
    ts = t.many
    t = None
    for v in ts:
        tn = v.name
        if isinstance(v,schema.AliasType):
            tn = f"{NAMESPACE}*{tn}"
        if t is None:
            t = tn
        else:
            t = f"{t}|{tn}"
    if t is None:
        t = 'unknown'
    return t

def format_description(desc):
    return '\n'.join(map(desc.split('\n'),lambda s: '--\t' + s))

def generate_def(name: str, defn: schema.Definition) -> str:
    pass

def generate_defs(root: schema.Root) -> dict[str,str]:
    defs = {}
    for name, defn in root.defs.items():
        lines = []

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
        
        match type(defn):
            case schema.FunctionDefinition:
                show = orig_b is None or orig_b.show
                if show:
                    if orig_g is not None:
                        params = []
                        for i,a in enumerate(defn.args):
                            n,t,d = (a.name, a.type, a.desc)
                            p_show = t is not None or d is not None
                            if n is None:
                                n = 'unk_'+str(i)
                            if d is None:
                                d = ''
                            params.append(n)
                            if p_show:
                                lines.append(f'---@param {n} {type_union(t)} {d}')
                        for i,r in enumerate(defn.rets):
                            n,t,d = (r.name, r.type, r.desc)
                            if t is None:
                                t = 'unknown'
                            #TODO: check, do multiple return lines work?
                            lines.append(f'---@return {type_union(t)} {n} {d}')
                        if orig_f is not None:
                            lines.append(f'---@source {orig_f.file}')
                        lines.append(f"function {orig_g.path}({', '.join(params)}) end")
                    params = []
                    for i,a in enumerate(defn.args):
                        n,t,d = (a.name, a.type, a.desc)
                        if n is None:
                            n = 'unk_'+str(i)
                        params.append(n if t is None else f"{n}: {type_union(t)}")
                    #TODO: add return types
                    lines.append(f"---@alias {NAMESPACE}*{name} fun({', '.join(params)})") 
            case schema.ClassDefinition:
                pass
            case schema.TableDefinition:
                lines.append(f"---@class {NAMESPACE}*{name}")
                desc = defn.desc
                if desc is not None:
                    lines.append(format_description(desc))
                for fldn,fld in defn.flds.items():
                    desc = fld.desc
                    if desc is None:
                        desc = ''
                    lines.append(f"---@field public {fldn} {type_union(fld.type)} {desc}")
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
