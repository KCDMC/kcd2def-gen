import schema
from record import from_json
from itertools import zip_longest
from pathlib import Path
from os import scandir, chdir

INPUT_FOLDER_PATH = Path("entries")
OUTPUT_FOLDER_PATH = Path("results")

NAMESPACE = 'kcd2def'

BUILTINS_REDIRECT = {
    'global-_G': '_G',
    'global-os': 'oslib',
    'global-io': 'iolib',
    'global-debug': 'debuglib',
    'global-table': 'tablelib',
    'global-package': 'packagelib',
    'global-math': 'mathlib',
    'global-coroutine': 'coroutinelib',
}

BUILTINS_DEFINE = {
    'global-tostring': "fun(v: any): string",
    'global-assert': "fun(v?: T, message?: any, ...: any): T, ...: any",
    'global-load': "fun(func: function, chunkname?: string): function?, error_message: string?",
    'global-loadstring': "fun(text: string, chunkname?: string): function?, error_message: string?",
    'global-print': "fun(...: any)",
    'global-ipairs': f"fun(t: T): {NAMESPACE}*internal-global-ipairs, T, i: integer",
    'global-collectgarbage': "fun(opt?: 'collect'|'count'|'isrunning'|'restart'|'setpause'|'stop'|'step'|'setstepmul', arg?: integer): any",
    'global-pcall': "fun(f: function, arg1?: any, ...: any): success: boolean, result: any, ...: any",
    'global-type': "fun(v: any): type: 'nil' | 'number' | 'string' | 'boolean' | 'table' | 'function' | 'thread' | 'userdata'",
    'global-loadfile': "fun(filename?: string): function?, error_message: string?",
    'global-gcinfo': "fun(): integer",
    'global-getfenv': "fun(f?: integer|fun(...: any): ...: unknown): table",
    'global-module': "fun(name: string, ...: any)",
    'global-xpcall': "fun(f: function, err: function): success: boolean, result: any, ...: any",
    'global-unpack': "fun(list: { [1]: T1, [2]: T2, [3]: T3, [4]: T4, [5]: T5, [6]: T6, [7]: T7, [8]: T8, [9]: T9, [10]: T10, [integer]: T }, i?: integer, j?: integer): T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, ...: T",
    'global-require': "fun(modname: string): unknown",
    'global-setmetatable': "fun(table: table, metatable?: table|metatable): table",
    'global-next': "fun(table: table<K, V>, index?: K): K?, V?",
    'global-setfenv': "fun(f: integer|fun(...: any): ...: unknown, table: table): function",
    'global-rawequal': "fun(v1: any, v2: any): boolean",
    'global-getmetatable': "fun(object: any): metatable: table",
    'global-pairs': f"fun(t: T): {NAMESPACE}*internal-global-pairs, T",
    'global-rawset': "fun(table: table, index: any, value: any): table",
    'global-tonumber': "fun(e: any): number?",
    'global-rawget': "fun(table: table, index: any): any",
    'global-select': "fun(index: integer|'#', ...: any): any",
    'global-newproxy': "fun(proxy: boolean|table|userdata): userdata",
    'global-dofile': "fun(filename?: string): ...: any",
    'global-error': "fun(message: any, level?: integer)",
}

BUILTINS_DEFINE_GENERICS = {
    'global-assert': { 'T': None },
    'global-ipairs': { 'T': 'table', 'V': None},
    'global-unpack': { 'T1': None, 'T2': None, 'T3': None, 'T4': None, 'T5': None, 'T6': None, 'T7': None, 'T8': None, 'T9': None, 'T10': None, 'T': None },
    'global-next': { 'K': None, 'V': None },
    'global-pairs': { 'T': 'table', 'K': None, 'V': None },
    
}

BUILTINS_DEFINE_INTERNAL = {
    'global-ipairs': [ f"---@alias {NAMESPACE}*internal-global-ipairs fun(table: V[], i?: integer): integer, V" ],
    'global-pairs': [ f"---@alias {NAMESPACE}*internal-global-pairs fun(table: table<K, V>, index?: K): K, V" ],
}

class BuiltinTypeException(Exception):
    pass

def type_union(t,builtins,shown,exclude_builtins=False):
    if t is None:
        return 'unknown'
    ts = t.many
    t = None
    for v in ts:
        tn = v.name
        if isinstance(v,schema.AliasType):
            if tn in builtins:
                if exclude_builtins:
                    raise BuiltinTypeException()
                if tn in BUILTINS_REDIRECT:
                    tn = BUILTINS_REDIRECT[tn]
                elif tn in BUILTINS_DEFINE:
                    tn = f"{NAMESPACE}*{tn}"
                else:
                    tn = 'function'
            else:
                tn = f"{NAMESPACE}*{tn}"
            shown.add(tn)
        if t is None:
            t = tn
        else:
            t = f"{t}|{tn}"
    if t is None:
        t = 'unknown'
    return t

def expand_path(path):
    #TODO: check for field name conflicts and turn to list if so
    if isinstance(path,list):
        #TODO: implement list path
        pass
    return path

def format_description(desc):
    return '\n'.join(map(desc.split('\n'),lambda s: '--\t' + s))

def generate_defs(root: schema.Root) -> dict[str,str]:
    builtins = {}
    for name, defn in root.defs.items():
        orig_builtin = None
        orig_global = None
        for o in defn.orig:
            if isinstance(o,schema.BuiltinOrigin):
                orig_builtin = o
            elif isinstance(o,schema.GlobalOrigin):
                orig_global = o
        show = orig_builtin is None or orig_builtin.show
        if show:
            continue
        builtins[name] = defn

    shown = set()
    
    defs = {}
    for name, defn in root.defs.items():
        if name in builtins:
            continue
        shown.add(name)
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

        # description section
        lines.append('--')
        
        if defn.desc is not None:
            lines.append(format_description(defn.desc))

        if orig_coverage is not None:
            lines.append('-- Dependencies:')
            for k in orig_coverage.uses:
                lines.append(f'---@see {k}')
            lines.append('-- Dependants:')
            for k in orig_coverage.used:
                lines.append(f'---@see {k}')

        lines.append('--')

        # body section
        
        if isinstance(defn,schema.FunctionDefinition):
            params = None
            if defn.args is not None:
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
                        lines.append(f'---@param {n} {type_union(t,builtins,shown)} {d}')
            if defn.rets is not None:
                for i,r in enumerate(defn.rets):
                    n,t,d = (r.name, r.type, r.desc)
                    if t is None:
                        t = 'unknown'
                    #TODO: check, do multiple return lines work?
                    lines.append(f'---@return {type_union(t,builtins,shown)} {n} {d}')
            if orig_file is not None:
                lines.append(f'---@source {orig_file.file}')
            if not defn.good:
                lines.append('---@deprecated')
                
            params = None
            if defn.args is not None:
                params = []
                for i,a in enumerate(defn.args):
                    n,t,d = (a.name, a.type, a.desc)
                    if n is None:
                        n = 'unk_'+str(i)
                    params.append(n if t is None else f"{n}: {type_union(t,builtins,shown)}")
            #TODO: add return types
                    
            if orig_global is not None:
                path = expand_path(orig_global.path)
                line = f"{path} = "
                if params is None:
                    lines.append(f"---@type {NAMESPACE}*{name}")
                    line += "..."
                else:
                    line += f"function({', '.join(params)}) end"
                lines.append(line)
            

            line = f"---@alias {NAMESPACE}*{name} "
            if params is None:
                line += "fun(...): ..."
            else:
                line += f"fun({', '.join(params)})"
            lines.append(line)
            
        elif isinstance(defn, schema.TableDefinition):
            header = f"---@class {NAMESPACE}*{name}"
            meta = defn.meta
            if meta is None:
                meta = BUILTINS_REDIRECT.get(name,None)
            if meta is not None:
                header = header + ': ' + meta
            lines.append(header)
            #TODO: handle operators (infer from meta, include overrides, special cases for call and index)
            for fldn,fld in defn.flds.items():
                if fld.show:
                    try:
                        types = type_union(fld.type,builtins,shown,name in BUILTINS_REDIRECT)
                    except BuiltinTypeException:
                        continue
                    desc = fld.desc
                    if desc is None:
                        desc = ''
                    visibility = 'public' if fld.good else 'private'
                    lines.append(f"---@field {visibility} {fldn} {types} {desc}")
            if orig_global is not None:
                if not defn.good:
                    lines.append('---@deprecated')
                lines.append(f"---@type {NAMESPACE}*{name}")
                path = expand_path(orig_global.path)
                lines.append(f"{path} = ...")
        
        if lines:
            defs[name] = '\n'.join(lines)+'\n'

    for name, defn in builtins.items():
        lines = []
        
        if name not in defs and name not in BUILTINS_REDIRECT and name in shown:
            if isinstance(defn,schema.FunctionDefinition):
                if name not in BUILTINS_DEFINE:
                    print(f'undefined builtin {name}')
                else:
                    orig_global = None
                    for o in defn.orig:
                        if isinstance(o,schema.GlobalOrigin):
                            orig_global = o
                    if orig_global is not None:
                        lines.append(f"---@type {NAMESPACE}*{name}")
                        path = expand_path(orig_global.path)
                        lines.append(f"{path} = ...")
                    generics = BUILTINS_DEFINE_GENERICS.get(name,None)
                    if generics is not None:
                        gs = []
                        for k,v in generics.items():
                            if v is None:
                                gs.append(k)
                            else:
                                gs.append(f"{k}: {v}")
                        lines.append(f"---@generic {', '.join(gs)}")
                    internal = BUILTINS_DEFINE_INTERNAL.get(name,None)
                    if internal is not None:
                        for line in internal:
                            lines.append(line)
                    lines.append(f"---@alias {NAMESPACE}*{name} {BUILTINS_DEFINE[name]}")
            elif isinstance(defn,schema.TableDefinition):
                raise ValueError(f'builtin table {name} should have a lib alias.')
                
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
        file.write('---@meta kcd2def\n')
        file.write('---@diagnostic disable: deprecated, invisible\n\n')
        file.write('\n'.join(defs.values()))

def main(argv):
    this = Path(argv[0])
    chdir(this.parent)
    
    inputs = []
    for entry in scandir(INPUT_FOLDER_PATH):
        path = Path(entry)
        if path.is_file() and path.suffix == '.json':
            inputs.append(path)
    
    OUTPUT_FOLDER_PATH.mkdir(parents=True,exist_ok=True)
    for path in inputs:
        process_file(path,OUTPUT_FOLDER_PATH / (path.stem + '.lua'))

if __name__ == '__main__':
    import sys
    main(sys.argv)
