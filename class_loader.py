import json
import re
from typing import List, Optional, Dict
from logger import get_logger

log = get_logger('ClassLoader')

BLACK_LIST = {
    'TaskConfig': [
        'LevelShowDialog',
        'OCDJOKABOEP'
    ]
}


class FieldDecl:
    def __init__(self, name: str, ty: str, is_array: bool, is_generic: bool, generic_type: Optional[str]):
        self.name = name
        self.type = ty
        self.is_array = is_array
        self.is_generic = is_generic
        if self.is_generic and generic_type is None:
            raise ValueError('Generic type cannot be None')
        if self.is_generic:
            self.generic_type = [x.strip() for x in generic_type.split(',')]

    def __repr__(self):
        if self.is_generic:
            return f'Field: {self.type}<{self.generic_type}> {self.name}'
        return f'Field: {self.type} {self.name}' + ('[]' if self.is_array else '')


class EnumDecl:
    def __init__(self, name: str):
        self.name = name
        self.dict = {}
        self.rev_dict = {}
        self.val_type = 'int'

    def add(self, name: str, value: int):
        self.dict[name] = value
        self.rev_dict[value] = name

    def get_name_by_value(self, value: int):
        return self.rev_dict[value]

    def get_value_by_name(self, name: str):
        return self.dict[name]

    def set_val_type(self, ty: str):
        self.val_type = ty

    def is_int(self):
        return self.val_type == 'int'

    def is_ushort(self):
        return self.val_type == 'ushort'

    def is_uint(self):
        return self.val_type == 'uint'


class ClassLoader:
    def __init__(self, header_file: str, index_file: str = None):
        self._classes: Dict[str, List[FieldDecl]] = {}
        self._enums: Dict[str, EnumDecl] = {}
        self._base_classes: Dict[str, str] = {}
        self._rev_base_class: Dict[str, List[str]] = {}
        self._excel_row_class: List[str] = []
        self._cur_namespace = ''
        with open(header_file, 'r', encoding='utf-8') as f:
            self.header_raw = f.readlines()
        if index_file is not None:
            with open(index_file, 'r', encoding='utf-8') as f:
                self._cls_index = json.load(f)
        else:
            self._cls_index = {}
        self._idx = 0
        self._len = len(self.header_raw)
        self.parse()
        self._guess_derivation_idx()

    def parse(self):
        while self._idx < self._len:
            line = self.header_raw[self._idx]
            # TODO: Use dump from frida-il2cpp-bridge instead of this shit
            pat = re.search('^// Namespace: (.*)', line)
            if pat:
                self._cur_namespace = pat[1]
            if re.search('public(.*)? class', line) is not None:
                self._load_class()
            elif line.startswith('public enum'):
                self._load_enum()
            else:
                self._idx += 1
        self._excel_row_class = list(set(self._excel_row_class))
        log.info(f'Loaded {len(self._classes)} classes and {len(self._enums)} enums')
        log.info(f'Found {len(self._excel_row_class)} excel row classes')

    def _merge_derivation_class_list(self, cls_name):
        ret = []
        if cls_name not in self._rev_base_class:
            return []
        for sub_cls_name in self._rev_base_class[cls_name]:
            ret.append(sub_cls_name)
            ret.extend(self._merge_derivation_class_list(sub_cls_name))
        return ret

    def _guess_derivation_idx(self, blacklist: List[str] = None):
        log.info('Guessing derivation class index...')
        if not blacklist:
            blacklist = []
        map_needed = set()
        for k, v in self._classes.items():
            if self.is_json_config(k) and self.get_base_class(k) != 'JsonConfig':
                map_needed.add(self.get_base_class(k))
        for item in map_needed:
            # Merge all fields into base class
            if item:
                if item in self._cls_index:
                    log.info(f'Skipping {item} due to class index provided by json')
                    continue
                if item in blacklist:
                    log.info(f'Skipping {item} due to blacklist')
                    continue
                field = list(set(self._merge_derivation_class_list(item)) - set(BLACK_LIST.get(item, [])))
                # FIXME: Try skip all obfuscated classes. At least it works for now
                field = [x for x in field if re.fullmatch(r'[A-Z]{11,}', x) is None]
                field.sort()
                self._cls_index[item] = {str(idx + 1): it for idx, it in enumerate(field)}
                self._cls_index[item]['0'] = item

    def get_class(self, name: str, with_base_class: bool = False) -> List[FieldDecl]:
        ret = self._classes.get(name, None)
        if with_base_class:
            base_class = self.get_base_class(name)
            while base_class is not None:
                base_fields = self.get_class(base_class)
                if base_fields is not None:
                    ret = base_fields + ret
                base_class = self.get_base_class(base_class)
        return ret

    def get_excel_classes(self):
        return self._excel_row_class

    def get_enum(self, name: str) -> EnumDecl:
        return self._enums.get(name, None)

    def contain_enum(self, name: str) -> bool:
        return name in self._enums

    def contain_class(self, name: str) -> bool:
        return name in self._classes

    def get_base_class(self, name: str) -> str:
        return self._base_classes.get(name, None)

    def is_json_config(self, name: str) -> bool:
        while True:
            if name is None:
                return False
            if name == 'JsonConfig':
                return True
            if not self.contain_class(name):
                return False
            name = self.get_base_class(name)

    def is_derivation_class(self, class_name: str):
        if class_name in self._cls_index:
            return True
        class_name = self.get_base_class(class_name)
        if class_name is None:
            return False
        return self.is_derivation_class(class_name)

    def get_derivation_class_name(self, base_name: str, class_index: int) -> str:
        return self._cls_index[base_name][str(class_index)]

    def has_derivation_class(self, base_name: str) -> bool:
        return base_name in self._cls_index

    def _load_class(self):
        pat = re.search(r'public(?: .*)? class ([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?)(?: : ([a-zA-Z0-9_]+))?',
                        self.header_raw[self._idx])
        if pat is None:
            log.warning('Fail to extract metadata from class decl: ' + self.header_raw[self._idx].strip())
            self._idx += 1
            return
        class_name = pat[1]
        base_class = pat[2]
        # TODO: Skip other namespaces to avoid duplicate class name. May remove when using frida-il2cpp-bridge dump
        if class_name in self._classes and self._cur_namespace != 'RPG.GameCore':
            self._idx += 1
            return
        if base_class is not None:
            self._base_classes[class_name] = base_class
            if base_class in self._rev_base_class:
                self._rev_base_class[base_class].append(class_name)
            else:
                self._rev_base_class[base_class] = [class_name]
        class_decl = []
        self._idx += 1
        while not self.header_raw[self._idx].startswith('}'):
            pat = re.search(r'public ([a-zA-Z0-9_]+)(\[])? ([a-zA-Z0-9_]+);', self.header_raw[self._idx])
            if pat:
                class_decl.append(FieldDecl(pat[3], pat[1], pat[2] is not None, False, None))
            else:
                pat = re.search(r'public(?: readonly)? (\w+)<([\w.,\s]+)> (\w+);', self.header_raw[self._idx])
                if pat:
                    class_decl.append(FieldDecl(pat[3], pat[1], False, True, pat[2]))
            if 'Row' in self.header_raw[self._idx]:
                pat = re.search(
                    r'public static void [A-Z]+\(Dictionary<string, int> [A-Z]+, string\[] [A-Z]+, out ([a-zA-Z0-9]+)Row [A-Z]+\) \{ }',
                    self.header_raw[self._idx])
                if pat:
                    self._excel_row_class.append(pat[1])
            self._idx += 1
        self._classes[class_name] = class_decl

    def _load_enum(self):
        pat = re.search(r'public enum ([a-zA-Z0-9_]+)', self.header_raw[self._idx])
        if pat is None:
            return
        enum_decl = EnumDecl(pat[1])
        self._idx += 1
        while not self.header_raw[self._idx].startswith('}'):
            pat = re.search(rf'public const {enum_decl.name} ([a-zA-Z0-9_]+) = (-?[0-9]+);', self.header_raw[self._idx])
            if pat:
                enum_decl.add(pat[1], int(pat[2]))
            else:
                pat = re.search(rf'public (\w+) value__;', self.header_raw[self._idx])
                if pat:
                    enum_decl.set_val_type(pat[1])
            self._idx += 1
        self._enums[enum_decl.name] = enum_decl
