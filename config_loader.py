import os
import json
from design_index_loader import DesignIndexLoader
from class_loader import ClassLoader, FieldDecl
from binary_reader import BinaryReader
from logger import get_logger

logger = get_logger('ConfigLoader')

CONFIG_MAP = {
    'AdventureAbilityConfigList': 'AdventureAbilityConfigList',
    'TurnBasedAbilityConfigList': 'TurnBasedAbilityConfigList',
    'ChessAbilityConfigList': 'ChessAbilityConfigList',
    'BattleLineupConfigList': 'BattleLineupConfig',
    'BattleLineupAvatarConfigList': 'BattleLineupAvatarConfig',
    'BattleLineupMazeBuffConfigList': 'LineupMazeBuffConfig',
    'BattleLineupSkillTreePresetConfigList': 'SkillTreePointPresetConfig',
    'BattleLineupCEPresetConfigList': 'CEBattlePresetConfig',
    'LevelConfigList': 'LevelGraphConfig',
    'GlobalModifierConfigList': 'GlobalModifierConfig',
    'AdventureModifierConfigList': 'AdventureModifierConfig',
    'ComplexSkillAIGlobalGroupConfigList': 'ComplexSkillAIGlobalGroupLookup',
    'GlobalTaskTemplateList': 'GlobalTaskListTemplateConfig',
}

ZIPPED_CLASS = {
    'ChangePropState',
    'SyncAllSubPropState',
    'SyncSubPropState',
    'LoopWaitBeHit',
    'WaitPredicateSucc',
    'ComparePropState',
}


class ConfigLoader:
    def __init__(self, design: DesignIndexLoader, cls: ClassLoader, is_beta: bool = True):
        self._design = design
        self._class = cls
        self._beta = is_beta
        try:
            with open(
                    os.path.join(design.dir_path, design.get_entry(name='BakedConfig/ConfigManifest.json').parent.filename),
                    'r', encoding='utf-8') as f:
                self._manifest = json.load(f)
        except:
            self._manifest = {}

    def load_binary_config(self, s_config: str, base_class: str, dump: str = None):
        idx = s_config.rfind('.')
        s_config = 'BakedConfig/' + s_config[:idx] + '.bytes'
        reader = self._design.get_reader(name=s_config)
        if dump:
            try:
                with open(dump, 'wb') as f:
                    f.write(reader.read_all())
            except:
                pass
            reader.reset()
        return self.load_class(reader, base_class)

    def _try_get_binary_excel_reader(self, base_class: str):
        reader = self._design.get_reader(name=f'BakedConfig/ExcelOutput/{base_class}.bytes')
        if reader is not None:
            return reader
        reader = self._design.get_reader(name=f'BakedConfig/ExcelOutputGameCore/{base_class}.bytes')
        if reader is not None:
            return reader
        if base_class.endswith('Config'):
            base_class = base_class[:-6]
            reader = self._design.get_reader(name=f'BakedConfig/ExcelOutput/{base_class}.bytes')
            if reader is not None:
                return reader
            reader = self._design.get_reader(name=f'BakedConfig/ExcelOutputGameCore/{base_class}.bytes')
            if reader is not None:
                return reader
        else:
            reader = self._design.get_reader(name=f'BakedConfig/ExcelOutput/{base_class}Config.bytes')
            if reader is not None:
                return reader
            reader = self._design.get_reader(name=f'BakedConfig/ExcelOutputGameCore/{base_class}Config.bytes')
            if reader is not None:
                return reader
        return None

    def load_binary_excel(self, base_class: str, s_path: str = None):
        if not s_path:
            reader = self._try_get_binary_excel_reader(base_class)
        else:
            reader = self._design.get_reader(name=s_path)
        if reader is None:
            return None
        arr_len = reader.read_array_len()
        logger.info(f'{base_class} excel item count: {arr_len}')
        index_field = self._class.get_class(base_class + 'Row')[0].name
        result = {}
        for _ in range(arr_len):
            data = {index_field: _}
            data.update(self.load_class(reader, base_class + 'Row', False, False))
            result[str(data[index_field])] = data
        return result

    def load_all_excels(self, output_dir: str, path_mapping: dict = None):
        err_list = []
        os.makedirs(output_dir, exist_ok=True)
        if path_mapping is not None:
            for class_name, s_path in path_mapping.items():
                try:
                    data = self.load_binary_excel(class_name, s_path)
                    with open(os.path.join(output_dir, os.path.basename(s_path)[:-6] + '.json'), 'w',
                              encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                except:
                    err_list.append(class_name)
        else:
            for excel_name in self._class.get_excel_classes():
                try:
                    data = self.load_binary_excel(excel_name)
                    if data is None:
                        err_list.append(excel_name)
                    else:
                        with open(os.path.join(output_dir, excel_name + '.json'), 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                except:
                    err_list.append(excel_name)
        return err_list

    def load_all_story(self, output_dir: str):
        story_config = self.load_binary_excel('PerformanceC', 'BakedConfig/ExcelOutput/PerformanceC.bytes')
        err = []
        for config in story_config.values():
            path = config['PerformancePath']
            try:
                data = self.load_binary_config(path[:-5] + '.bytes', 'LevelGraphConfig')
                os.makedirs(os.path.join(output_dir, os.path.dirname(path)), exist_ok=True)
                with open(os.path.join(output_dir, path), 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except:
                err.append(path)
        return err

    def load_all_configs(self, output_dir: str):
        err_list = {}
        for config_name in self._manifest.keys():
            err = self.load_config(config_name, output_dir)
            if err:
                err_list[config_name] = err
        return err_list

    def load_config(self, config_name: str, output_dir: str):
        err_list = []
        for item in self._manifest[config_name]:
            logger.info(f'Parsing {item}')
            try:
                # This shit doesn't save in the config
                if os.path.basename(item).startswith('MissionInfo'):
                    class_name = 'MainMissionInfoConfig'
                elif os.path.basename(item).startswith('MunicipalChatConfig'):
                    class_name = 'ConfigMunicipalNPCChatGroup'
                elif '/NPCOverrideConfig/' in item:
                    class_name = 'LevelNPCInfoOverride'
                else:
                    class_name = CONFIG_MAP.get(config_name, None)
                    if not class_name:
                        logger.warning(f'Can\'t find class name for config {config_name}. Roll back to item name.')
                        class_name = config_name
                data = self.load_binary_config(item, class_name)
                os.makedirs(os.path.dirname(os.path.join(output_dir, item)), exist_ok=True)
                with open(os.path.join(output_dir, item), 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logger.warning(f'Failed to parse {item}. Error: {e}')
                err_list.append(item)
        logger.info(
            f'Parsing complete. Extracted {len(self._manifest[config_name]) - len(err_list)} of {len(self._manifest[config_name])} files.')
        return err_list

    def load_class(self, reader: BinaryReader, class_name: str, parse_derivation=True, add_typing=True) -> dict:
        result = {}
        logger.debug(f'Loading class {class_name}. Position: {hex(reader._buffer.tell())}')
        if not parse_derivation and add_typing:
            result['$type'] = 'RPG.GameCore.' + class_name
        if class_name in ZIPPED_CLASS:
            # Fuck the zipper
            result['TaskEnabled'] = True
            return result
        if self._class.is_derivation_class(class_name) and parse_derivation:
            # Find Real Signature of Class. Avoid death loop.
            if self._class.has_derivation_class(class_name):
                cls_idx = reader.read_uleb128()
                cls_name = self._class.get_derivation_class_name(class_name, cls_idx)
                if not cls_name:
                    raise ValueError(f'Unknown class index {cls_idx} for class {class_name}')
                return self.load_class(reader, cls_name, False)
        # TaskConfig use merge field instead of lookup base class.
        class_decl = self._class.get_class(class_name, True)
        if class_decl is None:
            raise ValueError(f'Unknown class {class_name}')
        mask = reader.read_uleb128()
        mask_bit = 1
        for field in class_decl:
            if mask & mask_bit != 0:
                if field.is_array:
                    count = reader.read_array_len()
                    result[field.name] = []
                    for _ in range(count):
                        result[field.name].append(self.load_field(reader, field))
                else:
                    result[field.name] = self.load_field(reader, field)
            mask_bit <<= 1
        return result

    @staticmethod
    def parse_dynamic_float_rel(reader: BinaryReader):
        # REL version differ from BETA version
        is_dynamic = reader.read_bool()
        if is_dynamic:
            num_ops = reader.read_byte()
            expression = []
            for _ in range(num_ops):
                op_code = reader.read_byte()
                if op_code == 0:
                    expression.append({'Type': 'FixedNumber', 'FixedValue': {
                                'Value': reader.read_sleb128() / 4294967296}})
                elif op_code == 1:
                    expression.append({'Type': 'DynamicNumber', 'DynamicHash': reader.read_hash()})
                elif op_code == 2:
                    expression.append({'Type': 'Add'})
                elif op_code == 3:
                    expression.append({'Type': 'Sub'})
                elif op_code == 4:
                    expression.append({'Type': 'Mul'})
                elif op_code == 5:
                    expression.append({'Type': 'Div'})
                elif op_code == 6:
                    expression.append({'Type': 'Neg'})
                elif op_code == 7:
                    expression.append({'Type': 'Floor'})
                elif op_code == 8:
                    expression.append({'Type': 'Round'})
                elif op_code == 9:
                    expression.append({'Type': 'Int'})
                else:
                    raise ValueError(f'Unknown opcode {op_code}')
            return {"IsDynamic": True, "Expressions": expression}
        else:
            value = reader.read_sleb128() / 4294967296
            return {"IsDynamic": False, "FixedValue": {"Value": value}}


    @staticmethod
    def parse_dynamic_float(reader: BinaryReader, parse_expression=True) -> dict:
        # Dynamic float parser
        is_dynamic = reader.read_bool()
        if is_dynamic:
            expression = []
            expression_raw = {
                'Op': [],
                'Fixed': [],
                'Dynamic': []
            }
            op_count = reader.read_byte()
            for _ in range(op_count):
                expression_raw['Op'].append(reader.read_byte())
            fixed_count = reader.read_byte()
            for _ in range(fixed_count):
                expression_raw['Fixed'].append(reader.read_sleb128())
            dynamic_count = reader.read_byte()
            for _ in range(dynamic_count):
                expression_raw['Dynamic'].append(reader.read_hash())
            if parse_expression:
                """
                [1, 0, 0, 0, 1, 1, 2, 1, 2, 3, 8, 1, 9]
                # Strange in some white box item, roll to raw
                """
                try:
                    op_list = expression_raw['Op']
                    idx = 0
                    while idx < len(op_list):
                        op = op_list[idx]
                        if op == 0:
                            idx += 1
                            expression.append({'Type': 'FixedNumber', 'FixedValue': {
                                'Value': expression_raw['Fixed'][op_list[idx]] / 4294967296}})
                        elif op == 1:
                            idx += 1
                            expression.append(
                                {'Type': 'DynamicNumber', 'DynamicHash': expression_raw['Dynamic'][op_list[idx]]})
                        elif op == 2:
                            expression.append({'Type': 'Add'})
                        elif op == 3:
                            expression.append({'Type': 'Sub'})
                        elif op == 4:
                            expression.append({'Type': 'Mul'})
                        elif op == 5:
                            expression.append({'Type': 'Div'})
                        elif op == 6:
                            expression.append({'Type': 'Neg'})
                        elif op == 7:
                            expression.append({'Type': 'Floor'})
                        elif op == 8:
                            expression.append({'Type': 'Round'})
                        elif op == 9:
                            # Type 9 is Int, skip
                            pass
                        else:
                            raise ValueError(f'Unknown op type {op}')
                        idx += 1
                    expression_raw = expression
                except IndexError or ValueError:
                    expression_raw['$warning'] = 'Analyzer failed to parse expression'
                    logger.warning('Failed to parse expression. Use raw expression instead')
            return {"IsDynamic": True, "Expressions": expression_raw}
        else:
            value = reader.read_sleb128() / 4294967296
            return {"IsDynamic": False, "FixedValue": {"Value": value}}

    @staticmethod
    def parse_dynamic_value_read_type(reader: BinaryReader):
        # Aka. FJIPGPKEDBE___FromBinary
        dynamic_value_read_type = reader.read_byte()
        if dynamic_value_read_type != 0:
            dyn_str = reader.read_string()
            dyn_int = reader.read_hash()
            return {"DynamicValueReadType": dynamic_value_read_type, "String": dyn_str, "Integer": dyn_int}
        else:
            return {"DynamicValueReadType": 0}

    @staticmethod
    def parse_dynamic_values(reader: BinaryReader):
        """
        Tricks. I really don't know how to parse things like Action<xxx>, so just use this instead of generic method
        :param reader:
        :return:
        """
        ret = {}
        count = reader.read_uleb128()
        for _ in range(count):
            sub_item = {}
            hash_ = reader.read_hash()
            has_content = reader.read_bool()
            if has_content:
                for name in ['LGKGOMNMBAH', 'JKFHANPDGCA', 'LCADBHMMDED']:
                    sub_item[name] = ConfigLoader.parse_dynamic_float(reader)
            else:
                reader.read_hash()
                has_append_hash = reader.read_bool()
                if has_append_hash:
                    reader.read_hash()
                    reader.read_hash()
            dyn = ConfigLoader.parse_dynamic_value_read_type(reader)
            if dyn['DynamicValueReadType'] != 0:
                sub_item['IMMOBDAEDCL'] = dyn
            ret[hash_] = sub_item
        return ret

    @staticmethod
    def parse_dynamic_value(reader: BinaryReader):
        ret = {}
        _type = reader.read_sleb128()
        if _type == 0:
            ret['Type'] = 'INT'
            ret['IntValue'] = reader.read_sleb128()
        elif _type == 1:
            ret['Type'] = 'FLOAT'
            ret['FloatValue'] = reader.read_float()
        elif _type == 2:
            ret['Type'] = 'BOOL'
            ret['BoolValue'] = reader.read_bool()
        elif _type == 3:
            ret['Type'] = 'ARRAY'
            data = []
            arr_len = reader.read_array_len()
            for _ in range(arr_len):
                data.append(ConfigLoader.parse_dynamic_value(reader))
            ret['ArrayValue'] = data
        elif _type == 4:
            ret['Type'] = 'MAP'
            data = []
            arr_len = reader.read_array_len()
            for _ in range(arr_len):
                key = ConfigLoader.parse_dynamic_value(reader)
                value = ConfigLoader.parse_dynamic_value(reader)
                data.append({
                    'Key': key,
                    'Value': value
                })
            ret['MapValue'] = data
        elif _type == 5:
            ret['Type'] = 'STRING'
            ret['StringValue'] = reader.read_string()
        elif _type == 6:
            ret['Type'] = 'NULL'
        else:
            raise ValueError(f'Unknown dynamic value type {_type}')
        return ret

    def parse_dictionary(self, reader: BinaryReader, key_type: str, value_type: str):
        ret = {}
        count = reader.read_sleb128()
        for _ in range(count):
            key = self.load_field(reader, key_type)
            value = self.load_field(reader, value_type)
            ret[key] = value
        return ret

    @staticmethod
    def parse_vector(reader: BinaryReader, vector_size: int) -> dict:
        if vector_size == 2:
            return {
                'X': reader.read_float(),
                'Y': reader.read_float()
            }
        elif vector_size == 3:
            return {
                'X': reader.read_float(),
                'Y': reader.read_float(),
                'Z': reader.read_float()
            }
        elif vector_size == 4:
            return {
                'X': reader.read_float(),
                'Y': reader.read_float(),
                'Z': reader.read_float(),
                'W': reader.read_float()
            }

    def load_field(self, reader, field_type) -> dict:
        if isinstance(field_type, FieldDecl):
            if field_type.is_generic:
                if field_type.type == 'Dictionary':
                    gen_t = field_type.generic_type
                    key_ty = gen_t[0]
                    value_ty = gen_t[-1]
                    return self.parse_dictionary(reader, key_ty, value_ty)
                else:
                    raise NotImplementedError("Unsupported generic type: " + str(field_type))
            field_type = field_type.type
        if field_type == 'string':
            return reader.read_string()
        elif field_type == 'bool':
            return reader.read_bool()
        elif field_type == 'uint':
            return reader.read_uleb128()
        elif field_type == 'FixPoint':
            return reader.read_sleb128() / 4294967296
        elif field_type == 'int':
            return reader.read_sleb128()
        elif field_type == 'float':
            return reader.read_float()
        elif field_type == 'double':
            return reader.read_double()
        elif field_type == 'byte':
            return reader.read_byte()
        elif field_type == 'DynamicFloat':
            if self._beta:
                return self.parse_dynamic_float(reader)
            else:
                return self.parse_dynamic_float_rel(reader)
        elif field_type == 'DynamicValue':
            return self.parse_dynamic_value(reader)
        elif field_type == 'FMIOFJDICOO':  # TODO: DynamicValues in AbilityConfig
            return self.parse_dynamic_values(reader)
        elif field_type == 'TextID' or field_type == 'StringHash':
            return {"Hash": reader.read_hash()}
        elif field_type.startswith('MVector'):
            return self.parse_vector(reader, int(field_type[7]))
        elif self._class.contain_enum(field_type):
            enum_decl = self._class.get_enum(field_type)
            if enum_decl.is_int():
                val = reader.read_sleb128()
            elif enum_decl.is_ushort() or enum_decl.is_uint():
                val = reader.read_uleb128()
            else:
                raise NotImplementedError(f'Unknown enum value type {enum_decl.val_type}')
            return enum_decl.get_name_by_value(val)
        elif self._class.contain_class(field_type):
            return self.load_class(reader, field_type)
        else:
            raise NotImplementedError(f'Unknown type {field_type}')
