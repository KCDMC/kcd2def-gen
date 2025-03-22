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
    
    lua: lupa.LuaRuntime
    
    lglobals: 'lupa._LuaTable'
    ltype: 'lupa._LuaFunction'
    lstr: 'lupa._LuaFunction'
    lloadfile: 'lupa._LuaFunction'
    lloadstring: 'lupa._LuaFunction'
    lsetfenv:'lupa._LuaFunction'
    lgetinfo: 'lupa._LuaFunction'
    lbuiltins: 'lupa._LuaTable'
    lenv: 'lupa._LuaTable'
    
    root_path: Path

    current_file_path: str | None = None

    @classmethod
    def init(cls,*args,**kwargs):
        defs = schema.Root()
        files = {}
        
        lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        _lglobals = lua.globals()
        _ltype = _lglobals.type
        _lstr = _lglobals.tostring
        _lloadfile = _lglobals.loadfile
        _lloadstring = _lglobals.loadstring
        _lsetfenv = _lglobals.setfenv
        _lgetinfo = _lglobals.debug.getinfo

        _lenv = lua.execute("""
            __luascript_env = {}
            return __luascript_env
            
        """)

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

            local env = __luascript_env
            __luascript_env = nil

            for k,v in pairs(_G) do
                env[k] = v
            end
            env._G = env
            
            scan(env)

            __luascript_env = env
            return builtins
        """)
        
        return cls(defs, files, lua,
                   _lglobals, _ltype, _lstr, _lloadfile, _lloadstring,
                   _lsetfenv, _lgetinfo, _lbuiltins, _lenv,
                   *args, **kwargs)

def parse(tree):
    with redirect_stdout(None):
        return ast.parse(tree)

def purge_function_bodies(tree):
    for node in ast.walk(tree):
        if type(node) in {astnodes.Function, astnodes.Method, astnodes.AnonymousFunction}:
            node.body.body.clear()

def interrogate_function_node(state,name,node):
    args = []
    for arg in node.args:
        _arg = ast.to_lua_source(arg)
        args.append(_arg)
    _name = name
    if hasattr(node,'name'):
        _name = ast.to_lua_source(node.name)
        if _name == name:
            print('-- FUNC: ',name,'ON',', '.join(args))
        else:
            print('-- FUNC: ',_name,'AS',name,'ON',', '.join(args))
    return name, tuple(args)

class InterrogateFunction_Visitor(ast.ASTVisitor):
    state: State
    name: str
    args: dict
    
    def __init__(self,state: State, name: str, *args, **kwargs):
        self.state = state
        self.name = name
        self.args = {}
        super().__init__(*args,**kwargs)
    
    def visit_Function(self, node):
        name, args = interrogate_function_node(self.state, self.name, node)
        assert self.args.get(name,args) == args
        self.args[name] = args

    def visit_Method(self, node):
        name, args = interrogate_function_node(self.state, self.name, node)
        assert self.args.get(name,args) == args
        self.args[name] = args

    def visit_AnonymousFunction(self, node):
        name, args = interrogate_function_node(self.state, self.name, node)
        assert self.args.get(name,args) == args
        self.args[name] = args

def interrogate_function(state,path,name,line,last):
    data = state.files[path]
    lines = data.split('\n')
    code = '\n'.join(lines[line-1:last])
    
    tree = parse(code)
    purge_function_bodies(tree)

    visitor = InterrogateFunction_Visitor(state,name)    
    visitor.visit(tree)

    return visitor.args

def load_string(state, data):
    return state.lua.execute(f"""
        setfenv(1,__luascript_env)
        {data}
    """)

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
        print('-- NOPE: ', path)
        return
    
    state.current_file_path = path
    state.files[path] = data

    return state.lua.execute(f"""
        local chunk = loadfile("{path}")
        setfenv(chunk,__luascript_env)
        return chunk()
    """)

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

def prepare_state(state):
    load_string(state,'Script = {}')
    load_string(state,'System = {}')
    state.lenv.Script.ReloadScript = loader
    state.lenv.System.ScanDirectory = scanner
    state.lenv.SCANDIR_FILES = 1
    state.lenv.SCANDIR_SUBDIRS = 2

def load_scripts(state):
    load_script(state, 'Scripts/common.lua')
    load_script(state, 'Scripts/main.lua')

def run_scripts(state):
    load_string(state,'OnInit()')

def prepare_info(state,rdefn,path=None,tbl=None,seen=None):
    if seen is None:
        seen = {}
    if tbl is None:
        tbl = state.lenv
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
                            line = info.linedefined
                            last = info.lastlinedefined 
                            defn.orig.append(schema.ScriptOrigin(
                                line = line,
                                last = last
                                ))
                            file = info.source
                            if file and file[0] == '@':
                                file = file[1:]
                                defn.orig.append(schema.FileOrigin(
                                    file = file
                                    ))
                                args = interrogate_function(state,file,subpath,line,last)
                                assert len(args) == 1 or len(set(args.values())) == 1
                                defn.para = list(tuple(args.values())[0])
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
    
    prepare_state(state)
    load_scripts(state)
    run_scripts(state)

    rdefn = schema.TableDefinition()
    rdefn.orig.append(schema.BuiltinOrigin(show=True))
    rdefn.orig.append(schema.GlobalOrigin(path='_G'))
    state.root.defs['global-_G'] = rdefn
    prepare_info(state,rdefn)
    dump_info(state, "test.json")
