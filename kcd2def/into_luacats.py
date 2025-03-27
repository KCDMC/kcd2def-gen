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

def generate_defs(root: schema.Root) -> dict[str,str]:
    defs = {}
    for name, defn in root.defs.items():
        lines = []

        # extracting origins

        orig_file = None
        orig_global = None
        orig_builtin = None
        orig_coverage = None
        
        for o in defn.orig:
            if isinstance(o,schema.FileOrigin):
                orig_file = o
            elif isinstance(o,schema.GlobalOrigin):
                orig_global = o
            elif isinstance(o,schema.BuiltinOrigin):
                orig_builtin = o
            elif isinstance(o,schema.CoverageOrigin):
                orig_coverage = o

        show = orig_builtin is None or orig_builtin.show
        if not show:
            continue

        # description section
        lines.append('---')
        
        if defn.desc is not None:
            lines.append(format_description(defn.desc))

        if orig_coverage is not None:
            lines.append('-- Dependencies:')
            for k in orig_coverage.uses:
                lines.append(f'---@see {k}')
            lines.append('-- Dependants:')
            for k in orig_coverage.used:
                lines.append(f'---@see {k}')

        lines.append('---')

        # body section
        
        if isinstance(defn,schema.FunctionDefinition):
            
            if orig_global is not None:
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
                if orig_file is not None:
                    lines.append(f'---@source {orig_file.file}')
                lines.append(f"function {orig_global.path}({', '.join(params)}) end")
            params = []
            for i,a in enumerate(defn.args):
                n,t,d = (a.name, a.type, a.desc)
                if n is None:
                    n = 'unk_'+str(i)
                params.append(n if t is None else f"{n}: {type_union(t)}")
            #TODO: add return types
            lines.append(f"---@alias {NAMESPACE}*{name} fun({', '.join(params)})")
            
        elif isinstance(defn, schema.TableDefinition):
            header = f"---@class {NAMESPACE}*{name}"
            if defn.meta is not None:
                header = header + ': ' + defn.meta
            lines.append(header)
            #TODO: handle operators (infer from meta, include overrides, special cases for call and index)
            for fldn,fld in defn.flds.items():
                desc = fld.desc
                if desc is None:
                    desc = ''
                visibility = 'public' if fld.good else 'private'
                lines.append(f"---@field {visibility} {fldn} {type_union(fld.type)} {desc}")
        
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
