from dataclasses import replace, field
from record import record, Record, from_dict
from collections.abc import Collection
from typing import Literal, Optional, Union

__all__ = [
    'NilType',
    'ValueType',
    'TableType',
    'ChunkType',
    'BuiltinType',
    'PresentType',
    'ReferenceType',

    'MetaOperator',
    'PlainOperator',
    'ProxyOperator',
    'BuiltinOperator',
    
    'Origin',
    'Definition',

    'Type',
    'Field',
    'Param',

    'FileOrigin',
    'GlobalOrigin',
    'BuiltinOrigin',
    'CoverageOrigin',

    'TableDefinition',
    'FunctionDefinition',
]


## Special Strings

NilType = Literal['nil']
ValueType = Literal['boolean','number','string','integer','lightuserdata']
TableType = Literal['table','userdata']
ChunkType = Literal['function','thread']
ReferenceType = Union[TableType,ChunkType]
PresentType = Union[ValueType, ReferenceType]
BuiltinType = Union[NilType, PresentType]

# metamethods assuming lua 5.1
MetaOperator = Literal['mode','tostring','gc','name','metatable']
PlainOperator = Literal['unm','add','sub','mul','div','mod','pow','concat','eq','lt','le']
ProxyOperator = Literal['call','index','newindex']
BuiltinOperator = Union[MetaOperator,PlainOperator,ProxyOperator]


## Records

@record
class Origin(Record):
    """source information of a lua definition"""

@record
class Definition(Record):
    """a lua definition entry"""
    # has this been manually verified by a human?
    good: bool = False
    # formatted description
    desc: Optional[str] = None
    # formatted usage examples
    exam: Optional[str] = None
    # sources of the definition
    orig: list[Origin] = field(default_factory=list)
    
    def join(self, other):
        result = super().join(other)

        # silly way of making a set without hashability:
        orig_by_type = {}
        for o in self.orig:
            t = type(o)
            ot = orig_by_type.get(t,None)
            if ot is None:
                ot = o
            else:
                ot = ot.join(o)
            orig_by_type[t] = ot
        orig=list(orig_by_type.values())
        
        return replace(result,orig=orig)
    
    @classmethod
    def make(cls,kvs):
        result = cls.from_dict(kvs,infer_missing = True)
        return result.join(result)

@record
class Type(Record):
    bset: set[BuiltinType] = field(default_factory=set)
    dset: set[str] = field(default_factory=set)
    
    @classmethod
    def make(cls,kvs) -> 'Type':
        rec = cls.from_dict(kvs,infer_missing = True)
        bset = set(map(from_dict,rec.bset))
        dset = set(map(from_dict,rec.dset))
        return replace(rec,bset=bset,dset=dset)

    @classmethod
    def poly(cls):
        return False

@record
class Field(Record):
    type: Optional[Type] = None
    desc: Optional[str] = None
    good: bool = False
    show: bool = True

    @classmethod
    def poly(cls):
        return False

@record
class Param(Field):
    name: Optional[str] = None
    
    @classmethod
    def poly(cls):
        return False

## Origins

@record
class FileOrigin(Origin):
    # URI to file that defines this
    file: str
    # line defined
    line: Optional[int] = None
    # last line defined
    last: Optional[int] = None
    # initiating character (offset within line defined)
    init: Optional[int] = None
    # terminating character (offset within last line defined)
    term: Optional[int] = None


@record
class GlobalOrigin(Origin):
    #fixed global path in lua environment of game
    path: Union[str,list]

@record
class BuiltinOrigin(Origin):
    # is this builtin worth showing (e.g. it got modified by the game)
    show: bool = False

@record
class CoverageOrigin(Origin):
    # is this actually used in-game? (i.e. non-legacy)
    real: bool = False
    # other definitions that use this
    used: set[str] = field(default_factory=set)
    # other definitions this uses
    uses: set[str] = field(default_factory=set)

    @classmethod
    def make(cls,kvs):
        result = cls.from_dict(kvs,infer_missing = True)
        used = set(result.used)
        deps = set(result.deps)
        return replace(result,used = used,deps = deps)


## Definitions

@record
class TableDefinition(Definition):
    # metatable / metamethods
    meta: Optional[Type] = None
    # override operator overloads
    over: dict[BuiltinOperator,str] = field(default_factory=dict)
    # is immutable ('exact' class)
    imut: bool = False
    
    # list/array part
    # explicit positional types
    args: list[Field] = field(default_factory=list)
    # type of all other positions
    varg: Optional[Field] = None

    # map/hash part
    # fields have keys that can be joined via `.`
    flds: dict[str,Field] = field(default_factory=dict)
    # mappings for individual literal values
    lmap: dict[str,Field] = field(default_factory=dict)
    # mappings for builtin types
    bmap: dict[BuiltinType,Field] = field(default_factory=dict)
    # mappings for defined types
    dmap: dict[str,Field] = field(default_factory=dict)

@record
class FunctionDefinition(Definition):
    args: Optional[list[Param]] = None
    varg: Optional[Field] = None
    rets: Optional[list[Param]] = None
    vret: Optional[Field] = None


## Structure

@record
class Root(Record):
    # collected definitions
    defs: dict[str,Definition] = field(default_factory=dict)
    # remapped definition names
    maps: dict[str,str] = field(default_factory=dict)
