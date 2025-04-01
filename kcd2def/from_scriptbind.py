import schema
from record import into_json

from pathlib import Path
from os import scandir, chdir

from dataclasses import dataclass
import time
import re

from types import SimpleNamespace
from bs4 import BeautifulSoup as Soup

INPUT_FOLDER_PATH = Path("sources")
OUTPUT_FOLDER_PATH = Path("entries")

SCRIPTBIND_PATH = INPUT_FOLDER_PATH / "script_bind" / "script_bind_2025_01_14"

FILENAME_SCRIPTBIND_CLASS = re.compile(r'^(?:(?:(?:!!MEMBERTYPE_(?P<methods>Methods)_)|(?:!!OVERLOADED_(?P<overloads>[A-Za-z][A-Za-z0-9]*?)_))?)(?P<prefix>C_?ScriptBind_?)(?P<class_name>[A-Za-z][A-Za-z0-9]*?)(?:__(?P<method>.*?)(@(?P<parameters>.*?)?))?\.html$')

SCRIPTBIND_HTML_CLASSES = SimpleNamespace(
    MethodName = 'Element203',
    MethodDescription = 'Element207',
    ClassCodeBlock = 'Element100',
    ClassSectionBody = 'Element10'
)

@dataclass
class ScriptBindMethodInfo():
    method_name: str
    description: str | None = None
    params: None = None # TODO: parse C++ arguments to lua types

@dataclass
class ScriptBindInfo():
    class_name: str
    header_file: str | None = None
    methods: dict[str,ScriptBindMethodInfo]|None = None

@dataclass
class State:
    root: schema.Root
    files: dict[str,str]
    info: dict[str,ScriptBindInfo]
    folder: Path

    @classmethod
    def init(cls,*args,**kwargs):
        root = schema.Root()
        files = {}
        info = {}
        
        return cls(root, files, info,
                   *args, **kwargs)

def parse_scriptbind_html_method(state, path, info, method, params):
    data = None
    with open(path) as file:
        data = file.read()
    
    soup = Soup(data,features="xml")

def parse_scriptbind_html_overloads(state, path, info, overload):
    data = None
    with open(path) as file:
        data = file.read()
    
    soup = Soup(data,features="xml")

def parse_scriptbind_html_methods(state, path, info):
    data = None
    with open(path) as file:
        data = file.read()
    
    soup = Soup(data,features="xml")

    method_names = soup.select(f"div.{SCRIPTBIND_HTML_CLASSES.MethodName}")
    method_names = filter(lambda x: x, map(lambda x: x.text.strip(), method_names))
    method_descs = soup.select(f"div.{SCRIPTBIND_HTML_CLASSES.MethodDescription}")
    method_descs = map(lambda x: x.text.strip(), method_descs)
    methods = zip(method_names, method_descs)

    for name, desc in methods:
        methods = info.methods
        if methods is None:
            methods = dict()
            info.methods = methods
        method = methods.get(name,None)
        if method is None:
            method = ScriptBindMethodInfo(name,desc)
            methods[name] = method

def parse_scriptbind_html(state: State, path):
    name = None
    m = FILENAME_SCRIPTBIND_CLASS.fullmatch(path.name)
    if m:
        name = m.group('class_name')
    if name is None:
        return

    info = state.info.get(name,None)
    if info is None:
        info = ScriptBindInfo(name)
        state.info[name] = info
        
        # assume the source is in its named .h, it seems to be inconsistent
        ## info.header_file = (state.folder / f"ScriptBind_{name}.h").relative_to(INPUT_FOLDER_PATH).as_posix()

    if m.group('methods') is not None:
        return parse_scriptbind_html_methods(state, path, info)

    method = m.group('method')
    if method is not None:
        return parse_scriptbind_html_method(state, path, info, method, m.group('parameters'))

    overload = m.group('overloads')
    if overload is not None:
        return parse_scriptbind_html_overloads(state, path, info, overload)
    

def parse_scriptbind(state: State):
    for entry in scandir(state.folder):
        path = Path(entry)
        if path.is_file() and path.suffix == '.html':
            parse_scriptbind_html(state,path)

def prepare_info(state: State):
    for info in state.info.values():
        defn = schema.TableDefinition()
        
        defname = 'scriptbind-' + info.class_name
        
        if info.header_file is not None:
            defn.orig.append(schema.FileOrigin(file=info.header_file))

        if info.methods is not None:
            for method in info.methods.values():
                fld = schema.FunctionDefinition()
                fld.desc = method.description
                defn.flds[method.method_name] = fld
        
        state.root.defs[defname] = defn

def dump_info(state, file):
    with open(file,'w') as file:
        file.write(into_json(state.root))

def main(argv):
    this = Path(argv[0])
    chdir(this.parent)
    
    output_folder = OUTPUT_FOLDER_PATH
    state = State.init(SCRIPTBIND_PATH)
    parse_scriptbind(state)
    prepare_info(state)

    timestamp = time.strftime("%Y-%m-%d--%H-%M-%S")
    output_file_name = f"{this.stem}-{timestamp}.json"
    output_folder.mkdir(parents=True, exist_ok=True)
    dump_info(state, output_folder / output_file_name)

if __name__ == '__main__':
    import sys
    main(sys.argv)
