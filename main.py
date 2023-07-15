import json
import argparse
import os

from class_loader import ClassLoader
from design_index_loader import DesignIndexLoader
from textmap_loader import TextmapLoader, Language
from config_loader import ConfigLoader


parser = argparse.ArgumentParser()
parser.add_argument('--design', help='Path to design data folder', required=True)
parser.add_argument('--cs', help='Path to dump.cs', required=True)
parser.add_argument('--output', help='Path to output folder', required=True)
parser.add_argument('--excel-map', help='ExcelClass - sPath map file path')
args = parser.parse_args()

cls = ClassLoader(args.cs)
design = DesignIndexLoader(args.design)
conf = ConfigLoader(design, cls)
# Load text map
tm_loader = TextmapLoader()
os.makedirs(os.path.join(args.output, 'TextMap'), exist_ok=True)
for lang in Language:
    data = tm_loader.load_by_language(design, lang)
    with open(os.path.join(args.output, 'TextMap', 'TextMap' + lang.value.upper() + '.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
# Load configs
err_conf = conf.load_all_configs(args.output)
# Load excels
if args.excel_map:
    with open(args.excel_map, 'r', encoding='utf-8') as f:
        excel_map = json.load(f)
err_excel = conf.load_all_excels(args.output, excel_map['mapping'] if args.excel_map else None)
# Load stories
err_story = conf.load_all_story(args.output)
# Dump errors
with open(os.path.join(args.output, 'err.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'config': err_conf,
        'excel': err_excel,
        'story': err_story
    }, f, indent=2)

