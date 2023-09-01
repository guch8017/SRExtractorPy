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
parser.add_argument('--beta', help='Parse in beta mode', action='store_true', default=False)
parser.add_argument('--version', help='Version of the game', default='1.2.53')
parser.add_argument('--skip-textmap', help='Skip textmap loading', action='store_true', default=False)
parser.add_argument('--skip-config', help='Skip config loading', action='store_true', default=False)
parser.add_argument('--skip-excel', help='Skip excel loading', action='store_true', default=False)
parser.add_argument('--skip-story', help='Skip story loading', action='store_true', default=False)
args = parser.parse_args()

cls = ClassLoader(args.cs)
design = DesignIndexLoader(args.design, args.version)
conf = ConfigLoader(design, cls, args.beta)
# Load text map
if not args.skip_textmap:
    tm_loader = TextmapLoader()
    os.makedirs(os.path.join(args.output, 'TextMap'), exist_ok=True)
    for lang in Language:
        tm_loader.load_by_language(design, lang)
        tm_loader.dump(os.path.join(args.output, 'TextMap', 'TextMap' + '_' + lang.value.upper() + '.json'))
# Load configs
if not args.skip_config:
    err_conf = conf.load_all_configs(args.output)
else:
    err_conf = 'skipped'
# Load excels
if not args.skip_excel:
    if args.excel_map:
        with open(args.excel_map, 'r', encoding='utf-8') as f:
            excel_map = json.load(f)
    err_excel = conf.load_all_excels(os.path.join(args.output, 'ExcelOutput'), excel_map['mapping'] if args.excel_map else None)
else:
    err_excel = 'skipped'
# Load stories
if not args.skip_story:
    err_story = conf.load_all_story(args.output)
else:
    err_story = 'skipped'
# Dump errors
with open(os.path.join(args.output, 'err.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'config': err_conf,
        'excel': err_excel,
        'story': err_story
    }, f, indent=2)

