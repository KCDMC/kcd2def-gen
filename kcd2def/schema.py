from dataclasses import replace, field
from record import record, Record, from_dict
from typing import Literal, Optional, Union

__all__ = [
    'Type',
    'NilType',
    'ValueType',
    'TableType',
    'ChunkType',
    'PresentType',
    'ReferenceType',
    
    'Tag',
    'Type',
    'Origin',
    'Definition',

    'TypeTag',
    'AliasTag',
    'UsesTag',
    'HasTag',
    'IsTag',

    'FileOrigin',
    'EngineOrigin',
    'RuntimeOrigin',
    'ScriptOrigin',
    'ScripBindOrigin',
    'LoaderOrigin',
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
Type = Union[NilType, PresentType, 'unknown']


## Records

class Tag(Record):
    data: object

class Origin(Record):
    pass

class Definition(Record):
    """a lua definition entry"""
    # formatted description
    desc: Optional[str] = None
    # formatted usage examples
    uses: Optional[str] = None
    # source of the definition
    orig: list[Origin] = field(default_factory=list)


## Tags

@record
class TypeTag(Tag):
    data: Type = 'unknown'
    @classmethod
    def pure(cls):
        return True
    def join(self, other):
        if self.data == 'unknown':
            return other
        if other.data == 'unknown':
            return self
        return None

@record
class AliasTag(Tag):
    data: str
    @classmethod
    def pure(cls):
        return True
    def join(self, other):
        return None


@record
class UsesTag(Tag):
    data: set[Union[TypeTag,AliasTag]] = field(default_factory=set)
    """association/dependency"""
    
    def join(self, other):
        a = self.data
        b = other.data
        res = set()
        ret = set()
        for x in a:
            for y in b:
                if y not in res:
                    z = merge(x,y)
                    if z is not None:
                        x = z
                        res.add(y)
            ret.add(x)
        return type(self)(ret | (res ^ b))

    @classmethod
    def make(cls,kvs,infer_missing = False) -> 'UsesTag':
        rec = cls.from_dict(kvs,infer_missing = infer_missing)
        return replace(rec,data=set(map(from_dict,rec.data)))

@record
class HasTag(Tag):
    """composition/aggregation"""
    data: dict[str,UsesTag] = field(default_factory=dict)

@record
class IsTag(Tag):
    """inheritance/generalisation"""
    data: Optional[Union[TypeTag,AliasTag]] = None


## Origins

@record
class GlobalOrigin(Origin):
    """accessible under a fixed global path"""
    path: Union[str,list]

@record
class FileOrigin(Origin):
    file: str

@record
class EngineOrigin(Origin):
    pass

@record
class RuntimeOrigin(Origin):
    pass

@record
class ScriptOrigin(FileOrigin):
    line: int
    char: int

@record
class ScriptBindOrigin(EngineOrigin):
    pass

@record
class LoaderOrigin(EngineOrigin):
    pass

@record
class BuiltinOrigin(EngineOrigin):
    show: bool = False


## Definitions

@record
class TableDefinition(Definition):
    flds: HasTag = field(default_factory=HasTag)
    meta: IsTag = field(default_factory=IsTag)

@record
class ClassDefinition(TableDefinition):
    call: UsesTag = field(default_factory=UsesTag)

@record
class FunctionDefinition(Definition):
    args: HasTag = field(default_factory=HasTag)
    rets: HasTag = field(default_factory=HasTag)
    call: UsesTag = field(default_factory=UsesTag)


## Structure

@record
class Root(Record):
    defs: dict[str,Definition] = field(default_factory=dict)
