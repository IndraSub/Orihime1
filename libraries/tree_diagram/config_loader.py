#!/usr/bin/env python3

import os
import sys
import json
import yaml
import jsonpath_ng as jsonpath

class ParseError(Exception):
    pass

class Unresolved:
    def __init__(self, ctx):
        self.ctx = ctx
        self.cur_pos = ctx.cur_pos
        self.cur_file = ctx.cur_file
        ctx.unresolved.append(self)

class UnresolvedDict(Unresolved):
    def __init__(self, ctx, obj, mixins):
        super().__init__(ctx)
        self.mixins = mixins
        self.original = dict(obj)
        self.resolved = {}
    def update(self):
        updated = False
        new_obj = {}
        self.ctx.concrete(self.original, new_obj, None)
        for mixin in self.mixins:
            if not isinstance(mixin.resolved, dict):
                continue
            for k in mixin.resolved:
                if k not in new_obj:
                    new_obj[k] = mixin.resolved[k]
        if self.resolved != new_obj:
            updated = True
            self.resolved.clear()
            self.resolved.update(new_obj)
        return updated
    def check(self):
        for mixin in self.mixins:
            if mixin.resolved and not isinstance(mixin.resolved, dict):
                raise ParseError(f'Cannot mix {type(mixin.resolved)} into dict, at {self.cur_pos}, in {self.cur_file}')

class UnresolvedList(Unresolved):
    def __init__(self, ctx, abstract_list):
        super().__init__(ctx)
        self.abstract_list = abstract_list
        self.resolved = []
    def update(self):
        updated = False
        new_list = []
        for it in self.abstract_list:
            if isinstance(it, Unresolved):
                it = it.resolved
                if isinstance(it, list):
                    new_list.extend(it)
                else:
                    new_list.append(it)
            else:
                new_list.append(it)
        if new_list != self.resolved:
            updated = True
            self.resolved = new_list
        return updated
    def check(self):
        pass

class UnresolvedFile(Unresolved):
    def __init__(self, ctx, path, cur_path):
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
            ctx.files[self.path] = ctx.abstract(loaded, self.path)
            ctx.cur_pos = old_pos
        self.abstract = ctx.files[self.path]
        if isinstance(self.abstract, Unresolved):
            self.resolved = self.abstract.resolved
        else:
            self.resolved = None
    def update(self):
        updated = False
        if self.abstract is None:
            self.abstract = self.ctx.files[self.path]
            updated = True
        def reset(concrete):
            nonlocal updated
            self.resolved = concrete
            updated = True
        self.ctx.concrete(self.abstract, self.resolved, reset)
        return updated
    def check(self):
        pass

class UnresolvedJsonpath(Unresolved):
    def __init__(self, ctx, pattern):
        super().__init__(ctx)
        try:
            self.matcher = jsonpath.parse(pattern)
        except Exception:
            raise ParseError(f'Cannot parse JsonPath expression: {pattern}, in {self.cur_file}')
        self.resolved = None
    def update(self):
        updated = False
        result = [m.value for m in self.matcher.find(self.ctx.concrete_obj)]
        if len(result) == 1:
            result = result[0]
        if result != self.resolved:
            updated = True
            self.resolved = result
        return updated
    def check(self):
        pass

class ParseContext:
    def __init__(self, root_path, init_obj):
        self.files = {}
        self.unresolved = []
        self.root_path = root_path
        self.cur_file = None
        self.cur_pos = '$'
        self.abstract_obj = self.abstract(init_obj, self.root_path)
        self.concrete_obj = None
        self.last_updated = None

    def abstract(self, obj, cur_path):
        if os.path.isfile(cur_path):
            self.cur_file = cur_path
        else:
            self.cur_file = '<unknown>'
        if isinstance(obj, dict):
            mixins = set()
            new_obj = {}
            old_pos = self.cur_pos
            for k in obj:
                self.cur_pos = old_pos + '.' + k
                if k == '$ref':
                    mixins.add(UnresolvedJsonpath(self, obj[k]))
                elif k == '$include':
                    mixins.add(UnresolvedFile(self, obj[k], cur_path))
                else:
                    new_obj[k] = self.abstract(obj[k], cur_path)
            self.cur_pos = old_pos
            if not mixins:
                return new_obj
            elif len(mixins) == 1 and not new_obj:
                return mixins.pop()
            else:
                return UnresolvedDict(self, new_obj, mixins)
        elif isinstance(obj, list):
            new_list = []
            old_pos = self.cur_pos
            for i in range(0, len(obj)):
                self.cur_pos = old_pos + f'[{i}]'
                new_list.append(self.abstract(obj[i], cur_path))
            self.cur_pos = old_pos
            if not any(map(lambda o: isinstance(o, Unresolved), new_list)):
                return new_list
            else:
                return UnresolvedList(self, new_list)
        else:
            return obj

    def concrete(self, abs, con, reset):
        if isinstance(abs, Unresolved):
            if con is not abs.resolved:
                reset(abs.resolved)
        elif isinstance(abs, dict):
            if not isinstance(con, dict):
                con = {}
                reset(con)
            for k in abs:
                if k not in con:
                    con[k] = None
                def inner_reset(concrete):
                    con[k] = concrete
                self.concrete(abs[k], con[k], inner_reset)
        elif isinstance(abs, list):
            if not isinstance(con, list):
                con = []
                reset(con)
            while len(con) > len(abs):
                con.pop()
            while len(con) < len(abs):
                con.append(None)
            for i in range(0, len(abs)):
                def inner_reset(concrete):
                    con[i] = concrete
                self.concrete(abs[i], con[i], inner_reset)
        else:
            if con is not abs:
                reset(abs)

    def update_one(self):
        updated = False
        for unres in self.unresolved:
            if unres.update():
                self.last_updated = unres
                updated = True
        return updated

    def update(self):
        i = 0
        while i < len(self.unresolved) + 1:
            i += 1
            def inner_reset(con):
                self.concrete_obj = con
            self.concrete(self.abstract_obj, self.concrete_obj, inner_reset)
            if not self.update_one():
                break
        circular = self.update_one()
        if circular:
            raise ParseError('Circular references')

    def check(self):
        for unres in self.unresolved:
            unres.check()

    def parse(self):
        self.update()
        self.check()
        return self.expand_str(self.concrete_obj)

    def expand_str(self, doc):
        if isinstance(doc, dict):
            result = {}
            for k in doc:
                result[k] = self.expand_str(doc[k])
            return result
        if isinstance(doc, list):
            return list(map(self.expand_str, doc))
        if isinstance(doc, str):
            return self.translate_str(doc)
        else:
            return doc

    def translate_str(self, s, circular=set()):
        if id(s) in circular:
            raise ParseError('Circular string expansion: ' + s)
        circular.add(id(s))
        translated = []
        proc_mode = False
        expr = None
        stacked_right_brace = False
        for c in s:
            if c != '}':
                stacked_right_brace = False
            if proc_mode and c == '}':
                proc_mode = False
                stacked_right_brace = False
                targets = [m.value for m in jsonpath.parse(''.join(expr)).find(self.concrete_obj)]
                expr = None
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
                expr = None
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
                    expr.append(c)
                else:
                    translated.append(c)
        if proc_mode:
            raise ParseError('Incomplete string expansion expression: ' + s)
        circular.remove(id(s))
        return ''.join(translated)

if __name__ == '__main__':
    print(ParseContext(os.environ['PWD'], {'$include': sys.argv[1]}).parse())
