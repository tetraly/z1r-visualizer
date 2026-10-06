"""Everything the visualizer shows for one ROM, as plain JSON-ready data.

The static page (site/) runs this in Pyodide and draws the result; `cli.py --json` prints the
same thing. Level maps, the overworld, the item summary and the texts are only produced when
the level data parses, so nothing about an encoded ROM's seed is computed. The recorder info is
always available, as in the Streamlit app.
"""
import io
from typing import Any, Dict, List

from constants import CAVE_NAME, ITEM_TYPES
from data_extractor import DataExtractor, GarbledLevelDataError

# The item summary's rules are the Streamlit app's (app.py, display_item_summary).
EXCLUDED_ITEMS = ["Rupee", "5 Rupees", "Bombs", "Key", "Map", "Compass", "Triforce", "No Item", "Nothing"]
MAJOR_CAVES = [0x10, 0x12, 0x13, 0x18]  # Wood Sword, White Sword, Magical Sword, Letter Cave
SHOPS = [0x1D, 0x1E, 0x1F, 0x20, 0x1A]  # Shop 1-4, Potion Shop

ENCODED_MESSAGE = ("This ROM's level data is encoded, so it was probably generated with Zelda "
                   "Randomizer's ‘Race ROM’ flag or ZORA's ‘Encode level data’ setting. Please "
                   "generate the ROM again with that turned off. (%s)")
UNSUPPORTED_MESSAGE = "Sorry, this ROM doesn't seem to be supported. Features may not work correctly."


def ItemSummary(de: DataExtractor) -> Dict[str, Any]:
    levels = {}  # type: Dict[str, List[Dict[str, str]]]
    for level_num in range(1, 10):
        level_items = []
        for room_data in de.data[level_num].values():
            item_text = room_data['item_info']
            if item_text:
                is_drop = item_text.startswith("D ")
                item_name = item_text[2:] if is_drop else item_text
                if item_name and item_name not in EXCLUDED_ITEMS:
                    level_items.append({
                        'Item': item_name,
                        'Screen': room_data['room_num'],
                        'Location': 'Drop' if is_drop else 'Floor'
                    })
            stair_text = room_data['stair_info']
            if stair_text and not stair_text.startswith("Stair") and stair_text not in EXCLUDED_ITEMS:
                level_items.append({
                    'Item': stair_text,
                    'Screen': room_data['room_num'],
                    'Location': 'Item Stairway'
                })
        levels[str(level_num)] = level_items

    caves = []
    for cave_type in MAJOR_CAVES:
        for i in range(3):
            item_code = de.shop_data[cave_type][i]
            if item_code != 0x3F and item_code in ITEM_TYPES:
                caves.append({'Cave': CAVE_NAME[cave_type], 'Item': de.GetItemName(item_code)})

    shops = []
    for shop_type in SHOPS:
        for i in range(3):
            item_code = de.shop_data[shop_type][i]
            if item_code != 0x3F and item_code in ITEM_TYPES:
                shops.append({
                    'Shop': CAVE_NAME[shop_type],
                    'Item': de.GetItemName(item_code),
                    'Price': de.shop_data[shop_type][i + 3]
                })

    armos, coast = de.GetOverworldItems()
    overworld = [{'Location': 'Armos', 'Item': armos}, {'Location': 'Coast', 'Item': coast}]
    return {'levels': levels, 'caves': caves, 'shops': shops, 'overworld': overworld}


def _RecorderInfo(de: DataExtractor) -> Dict[str, Any]:
    data = de.GetRecorderData()
    if not data or data[0] == 0xFF:
        return {}
    text = de.GetRecorderText().rstrip()
    return {
        'text': text,
        'data': data,
        'patch': de.GetRecorderPatchData(),
        'filename': "%s.ips" % text.replace(" ", "_"),
    }


def Export(rom: bytes) -> Dict[str, Any]:
    """The page's data for one ROM. `status` is "ok", "encoded" or "unsupported"."""
    try:
        de = DataExtractor(rom=io.BytesIO(rom))
        recorder = _RecorderInfo(de)
    except Exception:
        return {'status': 'unsupported', 'message': UNSUPPORTED_MESSAGE, 'recorder': {}}
    try:
        de.Parse()
    except GarbledLevelDataError as e:
        return {'status': 'encoded', 'message': ENCODED_MESSAGE % e, 'recorder': recorder}
    except Exception:
        return {'status': 'unsupported', 'message': UNSUPPORTED_MESSAGE, 'recorder': recorder}

    levels = {}
    for level_num in range(1, 10):
        rooms = []
        for room_num, room in de.data[level_num].items():
            rooms.append(dict(room, num=room_num))
        levels[str(level_num)] = {'palette': de.GetLevelColorPalette(level_num), 'rooms': rooms}

    return {
        'status': 'ok',
        'message': '',
        'recorder': recorder,
        'progressiveItems': de.has_progressive_items,
        'levels': levels,
        'overworld': list(de.data[0].values()),
        'itemSummary': ItemSummary(de),
        'texts': [de.GetQuote(num) for num in range(de.GetQuoteCount())],
        'recorderText': de.GetRecorderText(),
    }
