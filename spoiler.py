"""A ROM's seed in the public seed format (docs/seed-format.md), and the visualizer's read result.

The static page (site/) runs Read in Pyodide and draws the seed it returns; `cli.py --json`
prints the same result and `cli.py --seed` the seed alone. ZORA sends the page the same format
directly. Nothing about an encoded or unsupported ROM's seed is computed: its result holds only
a status, the Streamlit app's message and the recorder tune, which the app shows for any ROM.
"""
import io
import os
import subprocess
from typing import Any, Dict, List, Optional

from constants import CAVE_NAME, ITEM_TYPES
from data_extractor import DataExtractor, GarbledLevelDataError

FORMAT = "z1r-seed"
FORMAT_VERSION = "1.0"
PRODUCER = "z1r-visualizer"

DOOR_KINDS = {
    "Door": "open",
    "Wall": "solid",
    "Walk-Through Wall": "walk-through",
    "Bomb Hole": "bombable",
    "Locked Door": "locked",
    "Shutter Door": "shutter",
}
DIRECTIONS = ["north", "east", "south", "west"]
# The caves the seed format lists, in the order the page shows them.
CAVES = [(0x10, "item"), (0x11, "take-any"), (0x12, "item"), (0x13, "item"), (0x18, "item"),
         (0x1D, "shop"), (0x1E, "shop"), (0x1F, "shop"), (0x20, "shop"), (0x1A, "potion-shop")]
PRICED_KINDS = ("shop", "potion-shop")
NO_ITEM = ITEM_TYPES[0x03]  # "No Item"
NOTHING = ITEM_TYPES[0x3F]  # "Nothing"

# The item summary's rules are the Streamlit app's (app.py, display_item_summary). The page
# derives the same tables from the seed format (site/app.js); `cli.py --item-summary` prints
# these so the two can be compared.
EXCLUDED_ITEMS = ["Rupee", "5 Rupees", "Bombs", "Key", "Map", "Compass", "Triforce", "No Item", "Nothing"]
MAJOR_CAVES = [0x10, 0x12, 0x13, 0x18]  # Wood Sword, White Sword, Magical Sword, Letter Cave
SHOPS = [0x1D, 0x1E, 0x1F, 0x20, 0x1A]  # Shop 1-4, Potion Shop

ENCODED_MESSAGE = ("This ROM's level data is encoded, so it was probably generated with Zelda "
                   "Randomizer's ‘Race ROM’ flag or ZORA's ‘Encode level data’ setting. Please "
                   "generate the ROM again with that turned off. (%s)")
UNSUPPORTED_MESSAGE = "Sorry, this ROM doesn't seem to be supported. Features may not work correctly."


def DefaultProducerVersion() -> str:
    """The visualizer's commit, e.g. "2026-10-06 9b99e59", or "unknown" outside a git checkout."""
    try:
        return subprocess.run(["git", "log", "-1", "--format=%cs %h"], cwd=os.path.dirname(os.path.abspath(__file__)),
                              capture_output=True, text=True, check=True).stdout.strip() or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _ItemOrNone(name: str) -> Optional[str]:
    return None if name in (NO_ITEM, NOTHING) else name


def _Room(de: DataExtractor, level_num: int, room_num: int, room: Dict[str, Any]) -> Dict[str, Any]:
    enemies = de.GetRoomEnemies(level_num, room_num)
    item = de.GetRoomItem(level_num, room_num)
    if 'stair_partner' in room:
        staircase = {'kind': 'transport', 'number': int(room['stair_info'].split('#')[1]),
                     'to': room['stair_partner']}  # type: Optional[Dict[str, Any]]
    elif 'stair_item_code' in room:
        staircase = {'kind': 'item', 'item': _ItemOrNone(de.GetRoomItemName(room['stair_item_code'], by_line=False))}
    else:
        staircase = None
    return {
        'number': room_num,
        'column': room['col'],
        'row': 9 - room['row'],  # the parser counts rows from the bottom, the format from the top
        'type': room['room_type'],
        'enemies': None if enemies is None else dict(
            {'name': enemies[0]}, **({} if enemies[1] is None else {'count': enemies[1]})),
        'item': None if item is None else {'name': item[0], 'drop': item[1]},
        'staircase': staircase,
        'doors': {direction: DOOR_KINDS[room['%s.wall_type' % direction]] for direction in DIRECTIONS},
    }


def _Screen(screen: Dict[str, Any]) -> Dict[str, Any]:
    name = screen.get('cave_name') or 'Unknown cave %s' % screen['cave'].upper()
    return {
        'number': int(screen['screen_num'], 16),
        'column': screen['col'] + 1,
        'row': 9 - screen['row'],
        'cave': {'name': name, 'shortName': screen.get('cave_name_short') or name},
    }


def _Cave(de: DataExtractor, cave_type: int, kind: str) -> Dict[str, Any]:
    wares = []
    for i in range(3):
        code = de.shop_data[cave_type][i]
        if code == 0x3F:
            continue
        ware = {'item': de.GetItemName(code, by_line=False)}  # type: Dict[str, Any]
        if kind in PRICED_KINDS:
            ware['price'] = de.shop_data[cave_type][i + 3]
        wares.append(ware)
    return {'name': CAVE_NAME[cave_type], 'kind': kind, 'wares': wares}


def _Recorder(de: DataExtractor) -> Optional[Dict[str, Any]]:
    notes = de.GetRecorderData()
    if not notes or notes[0] == 0xFF:
        return None
    return {'text': de.GetRecorderText().rstrip(), 'notes': notes}


def SeedDocument(de: DataExtractor, producer_version: str) -> Dict[str, Any]:
    """The parsed ROM's seed in the seed format. de must have parsed."""
    armos, coast = de.rom_reader.GetOverworldItemData()
    requirements = de.GetRequirements()
    seed = {
        'format': FORMAT,
        'formatVersion': FORMAT_VERSION,
        'producer': {'name': PRODUCER, 'version': producer_version},
        'progressiveItems': de.has_progressive_items,
        'levels': [{
            'number': level_num,
            'color': de.GetLevelColorPalette(level_num)[2],
            'rooms': [_Room(de, level_num, room_num, room) for room_num, room in de.data[level_num].items()],
        } for level_num in range(1, 10)],
        'overworld': {
            'screens': [_Screen(screen) for screen in de.data[0].values()],
            'armos': _ItemOrNone(de.GetItemName(armos, by_line=False)),
            'coast': _ItemOrNone(de.GetItemName(coast, by_line=False)),
        },
        'caves': [_Cave(de, cave_type, kind) for cave_type, kind in CAVES],
        'hints': [{'text': de.GetQuote(num)} for num in range(de.GetQuoteCount())],
        'requirements': {
            'whiteSwordHearts': requirements['white_sword'],
            'magicalSwordHearts': requirements['magical_sword'],
            'level9Triforces': 8 if requirements['triforce'] == 0xFF else requirements['triforce'],
            'doorRepairCost': requirements['door_repair'],
        },
    }  # type: Dict[str, Any]
    recorder = _Recorder(de)
    if recorder:
        seed['recorder'] = recorder
    return seed


def Read(rom: bytes, producer_version: str) -> Dict[str, Any]:
    """What the visualizer reads from a ROM: {"status": "ok", "seed": <seed format>}, or
    {"status": "encoded" | "unsupported", "message": ..., "recorder": <recorder tune or None>}."""
    try:
        de = DataExtractor(rom=io.BytesIO(rom))
        recorder = _Recorder(de)
    except Exception:
        return {'status': 'unsupported', 'message': UNSUPPORTED_MESSAGE, 'recorder': None}
    try:
        de.Parse()
    except GarbledLevelDataError as e:
        return {'status': 'encoded', 'message': ENCODED_MESSAGE % e, 'recorder': recorder}
    except Exception:
        return {'status': 'unsupported', 'message': UNSUPPORTED_MESSAGE, 'recorder': recorder}
    return {'status': 'ok', 'seed': SeedDocument(de, producer_version)}


def ItemSummary(de: DataExtractor) -> Dict[str, Any]:
    """The Streamlit app's item summary tables for a parsed ROM."""
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
