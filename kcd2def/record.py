from itertools import zip_longest

from dataclasses import dataclass, field, fields, replace

from dataclasses_json import DataClassJsonMixin
from json import loads, dumps

from typing import Literal, Optional, Any
import types


__all__ = [
    'merge',
    'Record',
    'record',
    'records',

    'into_dict',
    'into_json',
    'from_dict',
    'from_json',
]


records: dict[str,type['Record']] = {}

def record(cls):
    cls = dataclass(frozen = cls.pure(), kw_only=True)(cls)
    records[cls.__name__] = cls
    return cls

class Record(DataClassJsonMixin):
    base: 'Record'
    kind: str
    
    def __init_subclass__(cls, **kwargs: Any) -> None:
        # https://github.com/pydantic/pydantic/discussions/4706#discussioncomment-4404440            
        cls.__annotations__['kind'] = str #Literal[cls.__name__]
        cls.kind = field(default=cls.__name__,repr=False)

    @classmethod
    def _get_subclasses(cls):
        yield cls
        for subclass in cls.__subclasses__():
            yield from subclass._get_subclasses()
            
    @classmethod
    def _get_subclass_union(cls):
        return Union[tuple(cls._get_subclasses())]

    def join(self, other: 'Record') -> Optional['Record']:
        """combine the information of two similar records or fail"""
        # by default, only combine the same kind
        if self.kind != other.kind:
            return None
        flds = {}
        for fld in fields(other):
            value = getattr(other,fld.name)
            if hasattr(self,fld.name):
                value = merge(getattr(self,fld.name),value)
            flds[fld.name] = value
        return replace(self, **flds)

    @classmethod
    def pure(cls):
        return False

    @classmethod
    def make(cls,kvs,infer_missing = False) -> 'Record':
        return cls.from_dict(kvs,infer_missing = infer_missing)


def merge_pair(p):
    return merge(*p)

def merge(a,b):
    if a == b:
        return b

    if a is None:
        return b
    if b is None:
        return a
    
    if isinstance(a,Record):
        return a.join(b)
    if isinstance(b,Record):
        return b.join(a)
    
    if type(a) != type(b):
        return None

    if isinstance(a,set):
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
        return ret | (res ^ b)
    if isinstance(a,list):
        return list(map(merge_pair,zip_longest(a,b,fillvalue=None)))
    if isinstance(a,dict):
        ret = dict(a)
        for k,v in b.items():
            if k in a:
                ret[k] = merge(ret[k],v)
            ret[k] = v
        return ret
    
    return b

## Conversions

def into_dict(record: Record) -> dict:
    return record.to_dict()

def into_json(record: Record) -> str:
    return dumps(into_dict(record),indent = 2)

def from_dict(data: dict) -> Record:
    cls = records[data['kind']]
    return cls.make(data)

def from_json(json: str) -> Record:
    data = loads(json)
    return from_dict(data)
