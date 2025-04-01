from itertools import zip_longest

from dataclasses import dataclass, field, fields, replace

from dataclasses_json import DataClassJsonMixin
from json import loads, dumps

from typing import Literal, Optional, Any
import types


__all__ = [
    'RefuseMerge',
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

strict = False

class RefuseMerge(Exception):
    pass

def record(cls):
    cls = dataclass(frozen = cls.pure(), kw_only=True)(cls)
    records[cls.__name__] = cls
    return cls

class Record(DataClassJsonMixin):
    base: 'Record'
    kind: str
    
    def __init_subclass__(cls, **kwargs: Any) -> None:
        # https://github.com/pydantic/pydantic/discussions/4706#discussioncomment-4404440            
        cls.__annotations__['kind'] = Literal[cls.__name__]
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
        if not isinstance(other,Record):
            raise TypeError(f'incompatible merge of {type(self).__name__} and {type(other).__name}.')
        # by default, only combine the same kind
        if self.kind != other.kind:
            raise RefuseMerge(f'incompatible merge of records {self.kind} and {other.kind}.')
        flds = {}
        for fld in fields(other):
            value = getattr(other,fld.name)
            flds[fld.name] = merge(getattr(self,fld.name,None),value)
        return replace(self, **flds)

    @classmethod
    def pure(cls):
        "is pure (frozen dataclass)"
        return False

    @classmethod
    def poly(cls):
        "is polymorphic (save 'kind' field)"
        return True

    @classmethod
    def make(cls,kvs) -> 'Record':
        return cls.from_dict(kvs,infer_missing = True)


def merge_pair(p):
    return merge(*p)

def merge(a,b):
    if a is None:
        return b
    if b is None:
        return a

    if isinstance(a,Record) and isinstance(b,Record):
        return a.join(b)
    
    if isinstance(a,set) and isinstance(b,set):
        res = set()
        ret = set()
        for x in a:
            for y in b:
                if y not in res:
                    add = False
                    try:
                        z = merge(x,y)
                        add = True
                    except RefuseMerge:
                        pass
                    if add:
                        x = z
                        res.add(y)
            ret.add(x)
        return ret | (res ^ b)
    
    if isinstance(a,list) and isinstance(b,list):
        return list(map(merge_pair,zip_longest(a,b,fillvalue=None)))
    
    if isinstance(a,dict) and isinstance(b,dict):
        ret = dict()
        for k,v in b.items():
            ret[k] = merge(a.get(k,None),v)
        return ret

    if type(a) != type(b):
        raise RefuseMerge(f'incompatible merge of {type(a).__name__} and {type(b).__name__}.')

    if a is False:
        return b
    if b is False:
        return a

    if strict and a != b:
        raise ValueError(f'non-default value update from {a} to {b}.')
    
    return b


## Conversions

def reduce(data):
    if isinstance(data,dict):
        kind = data.get('kind',None)
        if kind is None:
            for v in data.values():
                reduce(v)
        else:
            cls = records[kind]
            poly = cls.poly()
            for fld in fields(cls):
                k = fld.name
                if not poly or k != 'kind':
                    v = data[k]
                    if fld.default_factory is not None and not v:
                        del data[k]
                    elif v == fld.default:
                        del data[k]
                    else:
                        reduce(v)
    elif isinstance(data,list):
        for v in data:
            reduce(v)

def convert(data):
    if isinstance(data,dict):
        kind = data.get('kind',None)
        for k,v in data.copy().items():
            data[k] = convert(v)
        if kind is not None:
            cls = records[kind]
            return cls.make(data)
    elif isinstance(data,list):
        for i,v in enumerate(data):
            data[i] = convert(v)
    return data

def into_dict(record: Record) -> dict:
    data = record.to_dict()
    reduce(data)
    return data

def into_json(record: Record) -> str:
    return dumps(into_dict(record),indent = 2)

def from_dict(data: dict) -> Record:
    return convert(data)

def from_json(json: str) -> Record:
    data = loads(json)
    return from_dict(data)
