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
    
    'Origin',
    'Definition',

    'LuaType'
    'AliasType',
    'PolyType',
    'Type',

    'FileOrigin',
    'GlobalOrigin',
    'ScriptOrigin',
    'BuiltinOrigin',

    'ClassDefinition',
    'TableDefinition',
    'FunctionDefinition',
]


## Types

NilType = Literal['nil']
ValueType = Literal['boolean','number','string','integer','lightuserdata']
TableType = Literal['table','userdata']
ChunkType = Literal['function','thread']
ReferenceType = Union[TableType,ChunkType]
PresentType = Union[ValueType, ReferenceType]
BuiltinType = Union[NilType, PresentType]


## Records

@record
class Relation(Record):
    pass

@record
class Origin(Record):
    pass

@record
class Definition(Record):
    """a lua definition entry"""
    # formatted description
    desc: Optional[str] = None
    # formatted usage examples
    uses: Optional[str] = None
    # sources of the definition
    orig: list[Origin] = field(default_factory=list)
    # has this been manually verified by a human?
    good: bool = False
    
    # silly way of making a set without hashability:
    def join(self, other):
        result = super().join(other)
        orig_by_type = {}
        for o in self.orig:
            t = type(o)
            ot = orig_by_type.get(t,None)
            if ot is None:
                ot = o
            else:
                ot = ot.join(o)
            orig_by_type[t] = ot
        return replace(result,orig=list(orig_by_type.values()))
    @classmethod
    def make(cls):
        result = cls.from_dict(kvs,infer_missing = infer_missing)
        return result.join(result)

@record
class LuaType(Record):
    name: BuiltinType
    @classmethod
    def pure(cls):
        return True
    def join(self, other):
        return None

@record
class AliasType(Record):
    name: str
    @classmethod
    def pure(cls):
        return True
    def join(self, other):
        return None

Type = Union[AliasType,LuaType]

@record
class PolyType(Record):
    many: set[Type] = field(default_factory=set)
    """association/dependency"""
    @classmethod
    def make(cls,kvs,infer_missing = False) -> 'PolyType':
        rec = cls.from_dict(kvs,infer_missing = infer_missing)
        form = set(map(from_dict,rec.form))
        return replace(rec,form=form)


## Origins

@record
class GlobalOrigin(Origin):
    """accessible under a fixed global path"""
    path: Union[str,list]

@record
class FileOrigin(Origin):
    """the location of the file (in game-specific notation)"""
    file: str

@record
class BuiltinOrigin(Origin):
    show: bool = False

@record
class ScriptOrigin(Origin):
    # line defined
    line: int
    # last line defined
    last: Optional[int] = None
    # initiating character
    init: Optional[int] = None
    # terminating character
    term: Optional[int] = None


## Definitions

@record
class TableDefinition(Definition):
    flds: dict[str,PolyType] = field(default_factory=dict)
    meta: Optional[Type] = None

@record
class ClassDefinition(TableDefinition):
    call: PolyType = field(default_factory=PolyType)

@record
class FunctionDefinition(Definition):
    # sequence of the arg/param names
    para: list[str] = field(default_factory=list)
    # types of the args/params by name
    args: list[PolyType] = field(default_factory=list)
    # sequence of types of the return values
    rets: list[PolyType] = field(default_factory=list)
    # types this function creates or interacts with
    call: PolyType = field(default_factory=PolyType)


## Structure

@record
class Root(Record):
    defs: dict[str,Definition] = field(default_factory=dict)
