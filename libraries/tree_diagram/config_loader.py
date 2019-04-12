#!/usr/bin/env python3

'''
INDRA Config Loader

Directives:
  - $include: <filepath>
    Include YAML document from filepath, and mix into current object.
    Filepath could be absolute (starts with /) and relative.
    The absolute path is relative to the root_path, A.K.A. working_directory.
    Only *nix path style (/) is supported. Auto conversion happens on Windows.
  - $ref: <jsonpath>
    Reference another object in this document. The root object for jsonpath is
    always the top-level document (not the top-level object of current file).
    If there is exactly one match, the result is that matched document.
    Otherwise the result is a list of matched documents (empty list is possible).

Mix-in rules:
  - If an object has one directive and no other fields, then the object itself
    is replaced by the result of the directive.
  - If a list has an item that resolves to be a list, the inner list is concatenated
    into the outer list.
  - In normal cases, the fields of referenced target is mixed into the current object.
    So you can override fields by writing them in the current object.

String expansion:
  - String expansion is the last step. Directives are not expanded.
  - Use curly braces to insert JsonPath expression into strings.
  - Double curly brace is collapsed into one. E.g. {{ -> {
  - Objects and lists are not insertable.
'''


import os
import sys
import json
import yaml
from jsonpath2.path import Path as jsonpath

import typing as t

JsonArray = t.List['JsonValue']
JsonObject = t.Dict[str, 'JsonValue']
JsonValue = t.Union[None, bool, int, float, str, JsonArray, JsonObject]
AbstractValue = t.Union[JsonValue, 'AbstractNode']

def shallow_eq(a: JsonValue, b: JsonValue) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return [id(v) for v in a] == [id(v) for v in b]
    if isinstance(a, dict):
        return {k: id(v) for k, v in a.items()} == {k: id(v) for k, v in b.items()}
    return a == b

class ParseError(Exception):
    pass

class AbstractNode:
    def __init__(self, ctx: 'ParseContext'):
        self.ctx = ctx
        self.cur_pos = ctx.cur_pos
        self.cur_file = ctx.cur_file
        self.resolved: JsonValue = None
        ctx.unresolved.append(self)
    def update(self) -> bool:
        return False
    def check(self) -> None:
        raise NotImplementedError

class AbstractDict(AbstractNode):
    def __init__(self, ctx: 'ParseContext', obj: t.Dict[str, AbstractValue], mixins: t.Set[AbstractValue]):
        super().__init__(ctx)
        self.mixins = mixins
        self.original = dict(obj)
        self.orig_concrete: JsonObject = {}
        self.resolved: JsonObject = {}
    def update(self) -> bool:
        self.orig_concrete, updated = self.ctx.make_concrete(self.original, self.orig_concrete)
        new_obj = dict(self.orig_concrete)
        for mixin in self.mixins:
            if not isinstance(mixin.resolved, dict):
                continue
            for k in mixin.resolved:
                if k not in new_obj:
                    new_obj[k] = mixin.resolved[k]
        if not shallow_eq(self.resolved, new_obj):
            updated = True
            self.resolved.clear()
            self.resolved.update(new_obj)
        return updated
    def check(self) -> None:
        for mixin in self.mixins:
            if mixin.resolved and not isinstance(mixin.resolved, dict):
                raise ParseError(f'Cannot mix {type(mixin.resolved)} into dict, at {self.cur_pos}, in {self.cur_file}')

class AbstractList(AbstractNode):
    def __init__(self, ctx: 'ParseContext', abstract_list: t.List[AbstractValue]):
        super().__init__(ctx)
        self.abstract_list = abstract_list
        self.concrete_list = [None] * len(abstract_list)
        self.resolved: JsonArray = []
    def update(self) -> bool:
        updated = False
        new_list: JsonArray = []
        for i in range(0, len(self.abstract_list)):
            it = self.abstract_list[i]
            if isinstance(it, AbstractNode):
                resolved = it.resolved
                if isinstance(resolved, list):
                    new_list.extend(resolved)
                else:
                    new_list.append(resolved)
            else:
                self.concrete_list[i], u = self.ctx.make_concrete(it, self.concrete_list[i])
                new_list.append(self.concrete_list[i])
                updated = updated or u
        if not shallow_eq(new_list, self.resolved):
            updated = True
            self.resolved = new_list
        return updated
    def check(self) -> None:
        pass

class AbstractInclude(AbstractNode):
    def __init__(self, ctx: 'ParseContext', path: str, cur_path: str):
        super().__init__(ctx)
        if path.startswith('/'):
            self.path = os.path.join(ctx.root_path, *path.split('/'))
        else:
            if not os.path.isdir(cur_path):
                cur_path = os.path.abspath(os.path.join(cur_path, '..'))
            self.path = os.path.join(cur_path, *path.split('/'))
        if self.path not in ctx.files:
            ctx.files[self.path] = None
            loaded = None
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f)
            except Exception as e:
                raise ParseError(f'Failed to load {self.path}, in {self.cur_file}: {e}')
            old_pos = ctx.cur_pos
            ctx.cur_pos = '$'
            ctx.files[self.path] = ctx.make_abstract(loaded, self.path)
            ctx.cur_pos = old_pos
        self.abstract = ctx.files[self.path]
        if isinstance(self.abstract, AbstractNode):
            self.resolved = self.abstract.resolved
        else:
            self.resolved = None
    def update(self) -> bool:
        updated = False
        if self.abstract is None:
            self.abstract = self.ctx.files[self.path]
        old_resolved = self.resolved
        self.resolved, u = self.ctx.make_concrete(self.abstract, self.resolved)
        updated = updated or u
        if self.resolved is not old_resolved:
            updated = True
        return updated
    def check(self) -> None:
        pass

class AbstractRef(AbstractNode):
    def __init__(self, ctx: 'ParseContext', pattern: str):
        super().__init__(ctx)
        self.pattern = pattern
        self.resolved = None
    def update(self) -> bool:
        updated = False
        try:
            result: JsonValue = self.ctx.execute_path(self.pattern)
        except Exception:
            result = None
        if isinstance(result, list) and len(result) == 1:
            result = result[0]
        if not shallow_eq(result, self.resolved):
            updated = True
            self.resolved = result
        return updated
    def check(self) -> None:
        try:
            self.ctx.execute_path(self.pattern)
        except Exception:
            raise ParseError(f'Unable to execute path expression: {self.pattern}, in {self.cur_file}')

class ParseContext:
    def __init__(self, root_path: str, init_obj: JsonValue):
        self.files: t.Dict[str, AbstractValue] = {}
        self.unresolved: t.List[AbstractNode] = []
        self.root_path = root_path
        self.cur_file: t.Optional[str] = None
        self.cur_pos = '$'
        self.abstract_obj: AbstractValue = self.make_abstract(init_obj, self.root_path)
        self.concrete_obj: JsonValue = None
        self.last_updated: t.Optional[AbstractNode] = None

    def make_abstract(self, obj: JsonValue, cur_path: str) -> AbstractValue:
        if os.path.isfile(cur_path):
            self.cur_file = cur_path
        else:
            self.cur_file = '<unknown>'
        if isinstance(obj, dict):
            mixins: t.Set[AbstractNode] = set()
            new_obj = {}
            old_pos = self.cur_pos
            for k in obj:
                self.cur_pos = old_pos + '.' + k
                if k == '$ref':
                    mixins.add(AbstractRef(self, obj[k]))
                elif k == '$include':
                    mixins.add(AbstractInclude(self, obj[k], cur_path))
                else:
                    new_obj[k] = self.make_abstract(obj[k], cur_path)
            self.cur_pos = old_pos
            if not mixins:
                return new_obj
            elif len(mixins) == 1 and not new_obj:
                return mixins.pop()
            else:
                return AbstractDict(self, new_obj, mixins)
        elif isinstance(obj, list):
            new_list = []
            old_pos = self.cur_pos
            for i in range(0, len(obj)):
                self.cur_pos = old_pos + f'[{i}]'
                new_list.append(self.make_abstract(obj[i], cur_path))
            self.cur_pos = old_pos
            if not any(map(lambda o: isinstance(o, AbstractNode), new_list)):
                return new_list
            else:
                return AbstractList(self, new_list)
        else:
            return obj

    def make_concrete(self, abs: AbstractValue, con: JsonValue) -> t.Tuple[JsonValue, bool]:
        updated = False
        if isinstance(abs, AbstractNode):
            updated = con is not abs.resolved
            con = abs.resolved
        elif isinstance(abs, dict):
            if not isinstance(con, dict):
                con = {}
                updated = True
            for k in abs:
                if k not in con:
                    con[k] = None
                con[k], u = self.make_concrete(abs[k], con[k])
                updated = updated or u
        elif isinstance(abs, list):
            if not isinstance(con, list):
                con = []
                updated = True
            while len(con) > len(abs):
                con.pop()
                updated = True
            while len(con) < len(abs):
                con.append(None)
                updated = True
            for i in range(0, len(abs)):
                con[i], u = self.make_concrete(abs[i], con[i])
                updated = updated or u
        else:
            updated = con != abs
            con = abs
        return con, updated

    def execute_path(self, expr: str) -> t.List[JsonValue]:
        return [m.current_value for m in jsonpath.parse_str(expr).match(self.concrete_obj)]

    def update_one(self) -> bool:
        updated = False
        for unres in self.unresolved:
            if unres.update():
                self.last_updated = unres
                updated = True
        return updated

    def update(self) -> None:
        i = 0
        while i < len(self.unresolved) * 2 + 1:
            i += 1
            self.concrete_obj, updated = self.make_concrete(self.abstract_obj, self.concrete_obj)
            updated = self.update_one() or updated
            if not updated:
                break
        circular = self.update_one()
        if circular:
            # assert self.last_updated is not None
            raise ParseError(f'Circular references: at {self.last_updated.cur_pos}, in {self.last_updated.cur_file}')

    def check(self) -> None:
        for unres in self.unresolved:
            unres.check()

    def parse(self) -> JsonValue:
        self.update()
        self.check()
        result = self.expand_str(self.concrete_obj, {})
        return result

    def expand_str(self, doc: JsonValue, expanded: t.Dict[int, JsonValue]) -> JsonValue:
        if id(doc) in expanded:
            return expanded[id(doc)]
        if isinstance(doc, dict):
            result: JsonValue = {}
            expanded[id(doc)] = result
            # assert isinstance(result, dict)
            for k in doc:
                result[k] = self.expand_str(doc[k], expanded)
        elif isinstance(doc, list):
            result = []
            expanded[id(doc)] = result
            for d in doc:
                result.append(self.expand_str(d, expanded))
        elif isinstance(doc, str):
            result = self.translate_str(doc, set())
        else:
            result = doc
        return result

    def translate_str(self, s: str, circular: t.Set[int]) -> str:
        if id(s) in circular:
            raise ParseError('Circular string expansion: ' + s)
        circular.add(id(s))
        translated = []
        proc_mode = False
        expr: t.Optional[t.List[str]] = None
        expr_str = ''
        stacked_right_brace = False
        for c in s:
            if c != '}':
                stacked_right_brace = False
            if proc_mode and c == '}':
                proc_mode = False
                stacked_right_brace = False
                # assert expr is not None
                expr_str = ''.join(expr)
                try:
                    targets = self.execute_path(expr_str)
                except Exception:
                    raise ParseError(f'Unable to execute Path expression: {expr_str}, in {s}')
                expr = []
                if len(targets) > 1:
                    raise ParseError('Ambiguous string expansion: ' + s)
                elif len(targets) == 1:
                    target = targets[0]
                    if isinstance(target, str):
                        target = self.translate_str(target, circular)
                        translated.append(target)
                    elif isinstance(target, dict) or isinstance(target, list):
                        raise ParseError('Not scalar type in string expansion: ' + s)
                    else:
                        translated.append(json.dumps(target))
            elif proc_mode and c == '{' and not expr:
                proc_mode = False
                expr = []
                translated.append(c)
            elif not proc_mode and c == '{':
                proc_mode = True
                expr = []
            elif not proc_mode and c == '}':
                if stacked_right_brace:
                    stacked_right_brace = False
                else:
                    translated.append(c)
                    stacked_right_brace = True
            else:
                if proc_mode:
                    # assert expr is not None
                    expr.append(c)
                else:
                    translated.append(c)
        if proc_mode:
            raise ParseError('Incomplete string expansion expression: ' + s)
        circular.remove(id(s))
        return ''.join(translated)

def test_include():
    with open('conf1.yaml', 'w') as f:
        f.write('''
        top_level_obj: conf1
        test_include_conf3:
            $include: conf3.yaml
        test_include_conf4:
            $include: conf4.yaml
        ''')
    with open('conf2.yaml', 'w') as f:
        f.write('''
        - top_level_arr
        - top_level_arr
        ''')
    with open('conf3.yaml', 'w') as f:
        f.write('''
        conf3_arr:
          $include: conf2.yaml
        ''')
    with open('conf4.yaml', 'w') as f:
        f.write('''
        $include: conf3.yaml
        arr:
          - $include: conf2.yaml
        ''')
    assert ParseContext(os.environ['PWD'], {'$include': 'conf4.yaml'}).parse() == \
        {'arr': ['top_level_arr', 'top_level_arr'], 'conf3_arr': ['top_level_arr', 'top_level_arr']}
    assert ParseContext(os.environ['PWD'], {'$include': 'conf2.yaml'}).parse() == \
        ['top_level_arr', 'top_level_arr']
    assert ParseContext(os.environ['PWD'], {'$include': 'conf1.yaml'}).parse() == \
        {
            'top_level_obj': 'conf1',
            'test_include_conf3': {
                'conf3_arr': ['top_level_arr', 'top_level_arr']
            },
            'test_include_conf4': {
                'arr': ['top_level_arr', 'top_level_arr'],
                'conf3_arr': ['top_level_arr', 'top_level_arr']
            }
        }

def test_ref():
    assert ParseContext(os.environ['PWD'], {
        'obj1': {'$ref': '$.refer[*].id'},
        'obj2': {'$ref': '$.refer[1].id'},
        'obj3': {'$ref': '$.refer[3].id'},
        'obj4': [{'$ref': '$.refer[*].id'}],
        'refer': [{'id': 'a'}, {'id': 'b'}]
    }).parse() == {'obj1': ['a', 'b'], 'obj2': 'b', 'obj3': [], 'obj4': ['a', 'b'], 'refer': [{'id': 'a'}, {'id': 'b'}]}

def test_object_circular():
    with open('conf1.yaml', 'w') as f:
        f.write('''
        top_level_conf1: 1
        conf2:
          $include: conf2.yaml
        ''')
    with open('conf2.yaml', 'w') as f:
        f.write('''
        top_level_conf2: 1
        conf1:
          $include: conf1.yaml
        ''')
    result = ParseContext(os.environ['PWD'], {'$include': 'conf1.yaml'}).parse()
    assert result['conf2']['conf1']['conf2'] is result['conf2'] # top level is different

def test_object_mixin():
    with open('conf1.yaml', 'w') as f:
        f.write('''
        top_level_conf1: 1
        $include: conf2.yaml
        ''')
    with open('conf2.yaml', 'w') as f:
        f.write('''
        top_level_conf2: 1
        $include: conf1.yaml
        ''')
    assert ParseContext(os.environ['PWD'], {'$include': 'conf1.yaml'}).parse() == \
        {'top_level_conf1': 1, 'top_level_conf2': 1}

def test_list_circular():
    with open('conf1.yaml', 'w') as f:
        f.write('''
        - arr_conf1
        - $include: conf2.yaml
        ''')
    with open('conf2.yaml', 'w') as f:
        f.write('''
        - arr_conf2
        - $include: conf1.yaml
        ''')
    try:
        ParseContext(os.environ['PWD'], {'$include': 'conf1.yaml'}).parse()
    except ParseError:
        return
    assert False

def test_wrong_mixin_type():
    with open('conf1.yaml', 'w') as f:
        f.write('''
        $include: conf2.yaml
        obj: a
        ''')
    with open('conf2.yaml', 'w') as f:
        f.write('''
        - arr_conf2
        ''')
    try:
        ParseContext(os.environ['PWD'], {'$include': 'conf1.yaml'}).parse()
    except ParseError:
        return
    assert False

def test_arr_ref_obj():
    assert ParseContext(os.environ['PWD'], {
        'arr': [{'$ref': '$.obj'}],
        'obj': {'test': 'yes'}
    }).parse() == {'arr': [{'test': 'yes'}], 'obj': {'test': 'yes'}}

def test_fail_load_file():
    try:
        ParseContext(os.environ['PWD'], {'$include': 'confbad.yaml'}).parse()
    except ParseError:
        return
    assert False

def test_abs_path():
    os.makedirs('./conftest/a', exist_ok=True)
    with open('conftest/a/conf1.yaml', 'w') as f:
        f.write('''
        - $include: conf2.yaml
        - $include: /a/conf3.yaml
        ''')
    with open('conftest/a/conf2.yaml', 'w') as f:
        f.write('''
        - conf2
        ''')
    with open('conftest/a/conf3.yaml', 'w') as f:
        f.write('''
        - conf3
        ''')
    assert ParseContext(os.environ['PWD'] + '/conftest', {'$include': '/a/conf1.yaml'}).parse() == ['conf2', 'conf3']

def test_bad_json_path():
    try:
        ParseContext(os.environ['PWD'], {'$ref': '$$${{{}}}'}).parse()
    except ParseError:
        return
    assert False

def test_string():
    assert ParseContext(os.environ['PWD'], [0, '{$[0]} {$[2]}{$.nonexist}', '{$[3]}', 'a']).parse() == [0, '0 a', 'a', 'a']
    assert ParseContext(os.environ['PWD'], '{{').parse() == '{'
    assert ParseContext(os.environ['PWD'], '}}').parse() == '}'

def test_string_circular():
    try:
        ParseContext(os.environ['PWD'], [0, '{$[0]} {$[2]}', '{$[2]}', 'a']).parse()
    except ParseError:
        return
    assert False

def test_string_amb():
    try:
        ParseContext(os.environ['PWD'], [0, '{$[0]} {$[2]} {$[*]}', '{$[3]}', 'a']).parse()
    except ParseError:
        return
    assert False

def test_string_non_scalar():
    try:
        ParseContext(os.environ['PWD'], [0, '{$[0]} {$[2]}', '{$[4]}', 'a', {'x': 1}]).parse()
    except ParseError:
        return
    assert False

def test_string_incomplete():
    try:
        ParseContext(os.environ['PWD'], [0, '{$[0]} {$[2]', '{$[3]}', 'a']).parse()
    except ParseError:
        return
    assert False

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        print(ParseContext(os.environ['PWD'], {'$include': sys.argv[1]}).parse())
    else:
        test_include()
        test_ref()
        test_object_circular()
        test_object_mixin()
        test_list_circular()
        test_wrong_mixin_type()
        test_arr_ref_obj()
        test_fail_load_file()
        test_abs_path()
        test_bad_json_path()
        test_string()
        test_string_circular()
        test_string_amb()
        test_string_non_scalar()
        test_string_incomplete()
