import os
import requests
import argparse
import sys

sys.path.append('..')
from design_index_loader import DesignIndexLoader

parser = argparse.ArgumentParser()
parser.add_argument('--base', help='Base url point to Design data', required=True)
parser.add_argument('--dst', help='Destination directory', required=True)
parser.add_argument('--client', help='Client type', default='Windows')
args = parser.parse_args()

os.makedirs(args.dst, exist_ok=True)
index_base_url = args.base + f'/client/{args.client}/'

print('Downloading M_DesignV.bytes...')
with open(args.dst + '/M_DesignV.bytes', 'wb') as f:
    design_data_ii = requests.get(index_base_url + 'M_DesignV.bytes').content
    f.write(design_data_ii)
index_name = ''
for i in range(4):
    for j in range(4):
        index_name += f'{design_data_ii[31 + i * 4 - j]:02x}'
print(f'Downloading DesignV_{index_name}.bytes...')
with open(args.dst + f'/DesignV_{index_name}.bytes', 'wb') as f:
    design_data_i = requests.get(index_base_url + f'DesignV_{index_name}.bytes').content
    f.write(design_data_i)
index_loader = DesignIndexLoader(args.dst)
for f in index_loader.file_entries:
    print(f'Downloading {f.filename}...')
    with open(os.path.join(args.dst, f.filename), 'wb') as fo:
        fo.write(requests.get(index_base_url + f.filename).content)
