# Usage:
#   For a single file:  python cli.py --files=rom.nes
#   For a set of files:  python cli.py --files="rom1.nes rom2.nes"
#   For a glob of files:  python cli.py --files="*.nes"

import argparse
import glob
import io
import os
from data_extractor import DataExtractor 

def GenerateCSVLine(file_path, level_num, data):
   ret = [file_path, str(level_num)]
   ret.append(data['room_num'])
   ret.append(data['room_type'])
   ret.append(data['enemy_info'] or 'No Enemies')
   ret.append(data['item_info'] or 'No Item')
   ret.append(data['stair_info'] or 'No Stairway')
   return ','.join(ret)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', type=str, required=True, help='Roms to process and print')
    args = parser.parse_args()
    files_to_process = []
    for pattern in args.files.split(' '):
        if '*' in pattern:
            files_to_process.extend(glob.glob(pattern))
        else:
            files_to_process.append(pattern)

    for file_path in files_to_process:
        with open(file_path, 'rb') as f:
            rom = io.BytesIO(f.read())
            data_extractor = DataExtractor(rom=rom)
            for level in range(1, 10):
                for room in data_extractor.data[level]:
                    print(GenerateCSVLine(file_path, level, data_extractor.data[level][room]))


if __name__ == "__main__":
    main()
