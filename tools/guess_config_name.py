import json
import os
import re
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util
import sys
import argparse

sys.path.append('..')
from class_loader import ClassLoader
from design_index_loader import DesignIndexLoader
from config_loader import ConfigLoader

parser = argparse.ArgumentParser()
parser.add_argument('--cs', help='Path to dump.cs provided by il2cpp dumper', required=True)
parser.add_argument('--string', help='Path to stringliteral.json provided by il2cpp dumper', required=True)
parser.add_argument('--design', help='Path to design data folder', required=True)
parser.add_argument('--output', help='Path to output file', required=True)
parser.add_argument('--map', help='Path to ID map file. If not provided the program will guess the id.', required=False)
args = parser.parse_args()


cls = ClassLoader(args.cs, args.map)
design = DesignIndexLoader(args.design)
conf = ConfigLoader(design, cls)


def pass1():
    mapping = {}
    valid = {}
    string_json = json.load(open(args.string, 'r', encoding='utf-8'))
    for s in string_json:
        if re.fullmatch(r'[a-zA-Z]+', s['value']):
            if design.get_entry(name='BakedConfig/ExcelOutput/' + s['value'] + '.bytes') is not None:
                valid[s['value']] = 'BakedConfig/ExcelOutput/' + s['value'] + '.bytes'
            elif design.get_entry(name='BakedConfig/ExcelOutputGameCore/' + s['value'] + '.bytes') is not None:
                valid[s['value']] = 'BakedConfig/ExcelOutputGameCore/' + s['value'] + '.bytes'

    for class_name in cls.get_excel_classes():
        if class_name == 'Textmap' or class_name == 'TextmapMT':
            continue
        # Guess from all excel classes
        if design.get_entry(name=f'BakedConfig/ExcelOutput/{class_name}.bytes') is not None:
            mapping[class_name] = f'BakedConfig/ExcelOutput/{class_name}.bytes'
        elif design.get_entry(name=f'BakedConfig/ExcelOutputGameCore/{class_name}.bytes') is not None:
            mapping[class_name] = f'BakedConfig/ExcelOutputGameCore/{class_name}.bytes'
        elif class_name.endswith('Config') and design.get_entry(
                name=f'BakedConfig/ExcelOutput/{class_name[:-6]}.bytes') is not None:
            mapping[class_name] = f'BakedConfig/ExcelOutput/{class_name[:-6]}.bytes'
        elif class_name.endswith('Config') and design.get_entry(
                name=f'BakedConfig/ExcelOutputGameCore/{class_name[:-6]}.bytes') is not None:
            mapping[class_name] = f'BakedConfig/ExcelOutputGameCore/{class_name[:-6]}.bytes'
        else:
            if design.get_entry(name=f'BakedConfig/ExcelOutputGameCore/{class_name}Config.bytes') is not None:
                mapping[class_name] = f'BakedConfig/ExcelOutputGameCore/{class_name}Config.bytes'
            elif design.get_entry(name=f'BakedConfig/ExcelOutput/{class_name}Config.bytes') is not None:
                mapping[class_name] = f'BakedConfig/ExcelOutput/{class_name}Config.bytes'

    return mapping, valid


def pass2(mapping: dict, valid: dict):
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    available = list(set(valid.keys()) - set([os.path.basename(it)[:-6] for it in mapping.values()]))
    need_to_find = list(set(cls.get_excel_classes()) - set(mapping.keys()) - {'Textmap', 'TextmapMT'})
    available_l2 = [' '.join(re.findall(r'[A-Z][^A-Z]*', it)) for it in available]
    need_to_find_l2 = [' '.join(re.findall(r'[A-Z][^A-Z]*', it)) for it in need_to_find]
    available_embedding = model.encode(available_l2)
    need_to_find_embedding = model.encode(need_to_find_l2)
    cos_scores = util.cos_sim(need_to_find_embedding, available_embedding)
    for idx, class_name in tqdm(enumerate(need_to_find)):
        score_list = [(cos_scores[idx][it], available[it]) for it in range(len(available))]
        score_list.sort(key=lambda x: x[0], reverse=True)
        for item in score_list:
            print(f'Trying {class_name}Row with {item[1]}')
            path = valid[item[1]]
            try:
                result = conf.load_binary_excel(class_name, path)
            except:
                continue
            if result is not None and len(result) > 0:
                mapping[class_name] = path
                break
        else:
            print(f'Failed to find {class_name}')
    return {
        'mapping': mapping,
        'valid': valid
    }


if __name__ == '__main__':
    data = pass2(*pass1())
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
