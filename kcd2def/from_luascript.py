import schema
from record import into_json

from pathlib import Path
from os import scandir, chdir
from functools import partial
from contextlib import redirect_stdout
from dataclasses import dataclass
import re

from luaparser import ast, astnodes
import lupa.lua51 as lupa

SCRIPTS_FOLDER_PATH = Path("..")

@dataclass
class NodeInfo:
    scope: bool = False # True -> inside a function

@dataclass
class State:
    root: schema.Root
    files: dict[str,str]
    nodes: dict[int,NodeInfo]
    
    lua: lupa.LuaRuntime
    lg: 'lupa._LuaTable'
    ltype: 'lupa._LuaFunction'
    lstr: 'lupa._LuaFunction'
    lgetinfo: 'lupa._LuaFunction'
    lbuiltins: 'lupa._LuaTable'
    
    root_path: Path

    current_file_path: str | None = None

    @classmethod
    def init(cls,*args,**kwargs):
        defs = schema.Root()
        files = {}
        nodes = {}
        
        lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        _lg = lua.globals()
        _ltype = _lg.type
        _lstr = _lg.tostring
        _lgetinfo = _lg.debug.getinfo
        _lbuiltins = lua.execute("""
            local builtins = {}
            local function scan(tbl)
                local todo = {}
                if builtins[tbl] then return end
                local b = {}
                builtins[tbl] = b
                for k,v in pairs(tbl) do
                    if type(v) == 'table' then
                        todo[v] = true
                    end
                    b[k] = true
                end
                for stbl in pairs(todo) do
                    todo[stbl] = nil
                    scan(stbl)
                end
            end
            scan(_G)
            return builtins
        """)
        
        
        return cls(defs, files, nodes, lua, _lg, _ltype, _lstr, _lgetinfo, _lbuiltins, *args, **kwargs)

def pass1_mark_nodes(state,node):
    for subnode in ast.walk(node):
        if subnode != node:
            visit(state, subnode, scope = node)

class Pass1_Visitor(ast.ASTVisitor):
    state: State
    
    def __init__(self,state: State, *args, **kwargs):
        self.state = state
        super().__init__(*args,**kwargs)
    
    def visit_Function(self, node):
        info = visit(self.state, node)
        if not info.scope:
            pass1_mark_nodes(self.state, node)

    def visit_Method(self, node):
        info = visit(self.state, node)
        if not info.scope:
            pass1_mark_nodes(self.state, node)

    def visit_AnonymousFunction(self, node):
        info = visit(self.state, node)
        if not info.scope:
            pass1_mark_nodes(self.state, node)

    def visit_Assign(self, node):
        info = visit(self.state, node)
        if not info.scope:
            pass1_mark_nodes(self.state, node)

class Pass2_Visitor(ast.ASTVisitor):
    state: State
    
    def __init__(self,state: State, *args, **kwargs):
        self.state = state
        super().__init__(*args,**kwargs)

    #def visit_Function(self, node):
        #info = visit(self.state, node)
        #if not info.scope:
            #source = ast.to_lua_source(node)
            #print(source)
            #print(ast.to_pretty_str(node))

    #def visit_Method(self, node):
        #info = visit(self.state, node)
        #if not info.scope:
            #source = ast.to_lua_source(node)
            #print(source)
            #print(ast.to_pretty_str(node))

    #def visit_AnonymousFunction(self, node):
        #info = visit(self.state, node)
        #if not info.scope:
            #source = ast.to_lua_source(node)
            #print(source)
            #print(ast.to_pretty_str(node))

    def visit_Assign(self, node):
        info = visit(self.state, node)
        if not info.scope:
            source = ast.to_lua_source(node)
            print(source)
            #print(ast.to_pretty_str(node))

def parse(tree):
    with redirect_stdout(None):
        return ast.parse(tree)

def visit(state, node, **kwargs):
    key = id(node)
    info = state.nodes.get(key,None)
    if info is None:
        info = NodeInfo(**kwargs)
        state.nodes[key] = info
    else:
        for k,v in kwargs.items():
            setattr(info,k,v)

    #print(key,info)
    return info

def load_script(state, path):
    if isinstance(path, Path):
        path = str(path.relative_to(state.root_path).as_posix())

    path = 'Scripts/' + path
    if reject_path(path):
        return
    print('-- LOAD: ',path)

    data = None
    try:
        with open(path) as file:
            data = file.read()
    except FileNotFoundError:
        print('-- MISSING: ', path)
        return
    
    state.current_file_path = path
    state.files[path] = data
    

    tree = parse(data)
    #Pass1_Visitor(state).visit(tree)
    #Pass2_Visitor(state).visit(tree)
    state.lua.execute(data)

def scan_directory(state, path, mode):
    
    found = state.lua.eval('{}')
    if reject_path(path):
        return found
    
    try:
        #print('scan',path)
        for entry in scandir(path):
            pe = Path(entry)
            if pe.is_file():
                if mode == 2:
                    continue
            elif mode == 1:
                continue
            
            #print('found',pe.name)
            found[len(found)+1] = pe.name
    except FileNotFoundError:
        try:
            path = 'Scripts/' + path
            #print('scan',path)
            for entry in scandir(path):
                pe = Path(entry)
                if pe.is_file():
                    if mode == 2:
                        continue
                elif mode == 1:
                    continue
                
                #print('found',pe.name)
                found[len(found)+1] = pe.name
        except FileNotFoundError:
            #print('missing', path.as_posix())
            return found

    return found

reject_paths = {'Scripts/Quests/'}

def reject_path(path):
    for subpath in reject_paths:
        if path.startswith(subpath):
            return True
    return False

def load_scripts(loader):
    loader('Scripts/common.lua')
    loader('Scripts/main.lua')

def run_scripts(lua):
    lua.execute('OnInit()')

def prepare_info(state,rdefn,path=None,tbl=None,seen=None):
    if seen is None:
        seen = {}
    if tbl is None:
        tbl = state.lg
        seen[state.lstr(tbl)] = 'global-_G'
    todo = []

    for k,v in tbl.items():
        if state.ltype(k) == 'string':
            t = state.ltype(v)
            subpath = k
            defn = None
            if path is not None:
                subpath = path + '.' + k
            fld = rdefn.flds.get(k,None)
            if fld is None:
                fld = schema.PolyType()
                rdefn.flds[k] = fld
            name = 'global-' + subpath
            fld.many.add(schema.AliasType(name=name))
            if state.lstr(v) not in seen:
                if t == 'table':
                    defn = schema.TableDefinition()
                    todo.append((defn,subpath,v))
                    seen[state.lstr(v)] = name
                elif t == 'function':
                    defn = schema.FunctionDefinition()
                else:
                    fld.many.add(schema.LuaType(name=t))
                if defn is not None:
                    if state.lbuiltins[v]:
                        defn.orig.append(schema.BuiltinOrigin())
                    else:
                        # TODO: associate file origin (currently muddled by lupa)
                        if t == 'function':
                            # TODO: also associate script origin for other types
                            # TODO: associate more script origin info
                            info = state.lgetinfo(v)
                            defn.orig.append(schema.ScriptOrigin(
                                line = info.linedefined
                                ))
                    defn.orig.append(schema.GlobalOrigin(
                        path = subpath
                        ))
                    state.root.defs[name] = defn
    for d,k,v in todo:
        prepare_info(state,d,k,v,seen)

def dump_info(state, file):
    with open(file,'w') as file:
        file.write(into_json(state.root))

if __name__ == '__main__':
    chdir(SCRIPTS_FOLDER_PATH)
    
    global state
    state = State.init(root_path=Path('.'))
    
    loader = partial(load_script, state)
    scanner = partial(scan_directory, state)
    
    state.lua.execute('Script = {}')
    state.lua.execute('System = {}')
    state.lg.Script.ReloadScript = loader
    state.lg.System.ScanDirectory = scanner
    state.lg.SCANDIR_FILES = 1
    state.lg.SCANDIR_SUBDIRS = 2
    
    load_scripts(loader)
    run_scripts(state.lua)

    rdefn = schema.TableDefinition()
    rdefn.orig.append(schema.BuiltinOrigin(show=True))
    rdefn.orig.append(schema.GlobalOrigin(path='_G'))
    state.root.defs['global-_G'] = rdefn
    prepare_info(state,rdefn)
    dump_info(state, "test.json")
