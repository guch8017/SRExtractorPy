import json
import os
from enum import Enum
from design_index_loader import DesignIndexLoader
from logger import get_logger

logger = get_logger('TextmapLoader')


class Language(Enum):
    ChineseSimplified = 'cn'
    ChineseTraditional = 'cht'
    German = 'de'
    English = 'en'
    Spanish = 'es'
    French = 'fr'
    Indonesian = 'id'
    Japanese = 'jp'
    Korean = 'kr'
    Portuguese = 'pt'
    Russian = 'ru'
    Thai = 'th'
    Vietnamese = 'vi'


class TextmapLoader:
    def __init__(self):
        self._textmap = {}

    def load_by_language(self, design: DesignIndexLoader, language: Language):
        self._textmap.clear()
        reader = design.get_reader(name=f'BakedConfig/ExcelOutput/Textmap_{language.value}.bytes')
        if not reader:
            logger.warning(f'Textmap_{language.value}.bytes not found.')
            return
        num_entry = reader.read_array_len()
        logger.info(f'Loading textmap for {language.name}. Entry count: {num_entry}')
        for _ in range(num_entry):
            mask = reader.read_uleb128()
            hash_ = reader.read_hash()
            text = reader.read_string()
            has_param = False
            if (mask & 0b100) != 0:
                has_param = reader.read_bool()
            self._textmap[hash_] = (text, has_param)
        logger.info(f'Successfully loaded textmap for {language.name}.')

    def get_text_by_hash(self, hash_: int) -> str:
        return self._textmap[hash_][0]

    def dump(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text_map = {}
        for k, v in self._textmap.items():
            text_map[k] = v[0]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(text_map, f, ensure_ascii=False, indent=2)
