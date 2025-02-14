# Usage:
#   For a single file:  python cli.py --files=rom.nes
#   For a set of files:  python cli.py --files="rom1.nes rom2.nes"
#   For a glob of files:  python cli.py --files="*.nes"

import argparse
import glob
import io
import os
from data_extractor import DataExtractor
from constants import CAVE_NAME, ITEM_TYPES

def GenerateLevelCSVLine(file_path, level_num, data):
   ret = [file_path, str(level_num)]
   ret.append(data['room_num'])
   ret.append(data['room_type'])
   ret.append(data['enemy_info'] or 'No Enemies')
   ret.append(data['item_info'] or 'No Item')
   ret.append(data['stair_info'] or 'No Stairway')
   ret.append(data['north.wall_type'])
   ret.append(data['west.wall_type'])
   ret.append(data['east.wall_type'])
   ret.append(data['south.wall_type'])
   return ','.join(ret)

def GenerateOverworldCSVLine(file_path, data):
   if not data['screen_num']:
       return
   ret = [file_path, 'Overworld']
   ret.append(data['screen_num'])
   ret.append(data['cave_name'])
   ret.append(data['block_type'])
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
            try:
               data_extractor.Parse()
            except IndexError:
                print("Error parsing level data in %s." % file_path)
                exit()

            # Print out room data for each level
            for level in range(1, 10):
                if level in data_extractor.data:
                    for room in data_extractor.data[level]:
                        print(GenerateLevelCSVLine(file_path, level, data_extractor.data[level][room]))

            # Print out overworld screens
            if data_extractor.data:
                for screen_num in data_extractor.data[0]:
                    print(GenerateOverworldCSVLine(file_path, data_extractor.data[0][screen_num]))

            # Caves
            if data_extractor.shop_data:
                for cave_type in [0x10, 0x11, 0x12, 0x13, 0x18]:
                    for i in range (0,3):
                        if data_extractor.shop_data[cave_type][i] != 0x3F:
                            print(",".join([file_path, "cave", CAVE_NAME[cave_type],
                                ITEM_TYPES[data_extractor.shop_data[cave_type][i]]]))

            # Shops
            if data_extractor.shop_data:
                for cave_type in [0x1D, 0x1E, 0x1F, 0x20, 0x1A, 0x23, 0x21, 0x22]:
                    for i in range (0,3):
                        if data_extractor.shop_data[cave_type][i] != 0x3F:
                            print(",".join([file_path, "cave", CAVE_NAME[cave_type],
                                ITEM_TYPES[data_extractor.shop_data[cave_type][i]],
                                str(data_extractor.shop_data[cave_type][i+3])]))

            # Print out Overworld items as "Level 0"
            locations = ["Armos", "Coast"]
            items = data_extractor.GetOverworldItems()
            for i in range (0, 2):
                print(','.join([file_path, '0', locations[i], items[i]]))
            
            requirements = data_extractor.GetRequirements()
            if requirements["triforce"] == 0xFF:
                print ("%s,misc,level_nine_triforce_requirement,8 (Vanilla)" % file_path)
            else:
                print ("%s,misc,level_nine_triforce_requirement,%d" %
                       (file_path, requirements["triforce"]))
            print("%s,misc,white_sword_cave_requirement,%d" %
                  (file_path, requirements["white_sword"]))
            print("%s,misc,magical_sword_cave_requirement,%d" %
                  (file_path, requirements["magical_sword"]))
            print("%s,misc,door_repair_charge,%d" %
                  (file_path, requirements["door_repair"]))

            for num in range (0, 38):
                print("%s,quote,%d,%s" % (file_path, num, data_extractor.GetQuote(num)))
            maybe_recorder_text = data_extractor.GetRecorderText()

            if maybe_recorder_text:
                print("%s,quote,recorder,%s" % (file_path, maybe_recorder_text))

if __name__ == "__main__":
    main()
