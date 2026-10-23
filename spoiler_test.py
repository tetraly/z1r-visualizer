import glob
import io
import json
import os
import unittest

from constants import ITEM_TYPES, PEGASUS_BOOTS_ITEM_TYPES
from data_extractor import DataExtractor
from spoiler import FORMAT_VERSION, ItemSummary, Read

try:
    import jsonschema
except ImportError:  # the checks that need it skip
    jsonschema = None

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, 'docs', 'seed-format.schema.json')
# samples/ holds the seed documents of one ZORA seed with second-quest dungeons and Pegasus Boots
# (flags '8hq4BeR1JXo89BJ2!TFpTP02u8UJ2v', ZORA flags '7.iQCEKa', seed 7; its ROM is
# testdata/zora-2q-boots-seed7.nes): the visualizer's reading of the ROM (format 1.1, `cli.py
# --seed --producer-version=sample`) and ZORA's own document (format 1.0, naming the boots as
# boomerangs). docs/design/sample-seed.json is an older 1.0 document, without shown numbers.
SAMPLE = os.path.join(HERE, 'samples', 'zora-2q-pegasus-boots.json')
ZORA_SAMPLE = os.path.join(HERE, 'samples', 'zora-2q-pegasus-boots.zora-1.0.json')
OLD_SAMPLE = os.path.join(HERE, 'docs', 'design', 'sample-seed.json')
# A second-quest set's paired levels show each other's numbers: door code -> number shown.
SECOND_QUEST_NUMBERS = {1: 1, 2: 3, 3: 2, 4: 5, 5: 4, 6: 6, 7: 8, 8: 7, 9: 9}


def _Read(name):
    with open('testdata/%s' % name, 'rb') as f:
        return Read(f.read(), 'test')


def _HasTestRom(name):
    return os.path.exists('testdata/%s' % name)


def _Load(path):
    with open(path) as f:
        return json.load(f)


def _ItemNames(seed):
    """Every item name in a seed document."""
    names = [seed['overworld']['armos'], seed['overworld']['coast']]
    for level in seed['levels']:
        for room in level['rooms']:
            names.append(room['item'] and room['item']['name'])
            if room['staircase'] and room['staircase']['kind'] == 'item':
                names.append(room['staircase']['item'])
    names += [ware['item'] for cave in seed['caves'] for ware in cave['wares']]
    return {name for name in names if name}


class SchemaTest(unittest.TestCase):

    def setUp(self):
        with open(SCHEMA_PATH) as f:
            self.schema = json.load(f)

    @unittest.skipIf(jsonschema is None, 'jsonschema not installed')
    def test_schema_is_valid(self):
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_item_vocabulary_matches_the_parser(self):
        # The parser names $03 in caves "Magical Sword"; "No Item" and "Nothing" are absences.
        names = {name for name in ITEM_TYPES.values() if name not in ('No Item', 'Nothing')} | {'Magical Sword'}
        names |= set(PEGASUS_BOOTS_ITEM_TYPES.values())
        self.assertEqual(names, set(self.schema['$defs']['itemName']['anyOf'][0]['enum']))

    @unittest.skipIf(jsonschema is None, 'jsonschema not installed')
    def test_every_test_rom_seed_is_valid(self):
        validator = jsonschema.Draft202012Validator(self.schema)
        roms = sorted(glob.glob('testdata/*.nes'))
        if not roms:
            self.skipTest('no test ROMs')
        for path in roms:
            with open(path, 'rb') as f:
                result = Read(f.read(), 'test')
            if result['status'] == 'ok':
                errors = ['%s at %s' % (e.message, list(e.path)) for e in validator.iter_errors(result['seed'])]
                self.assertEqual([], errors, path)


    @unittest.skipIf(jsonschema is None, 'jsonschema not installed')
    def test_samples_and_older_documents_are_valid(self):
        validator = jsonschema.Draft202012Validator(self.schema)
        for path in (SAMPLE, ZORA_SAMPLE, OLD_SAMPLE):
            errors = ['%s at %s' % (e.message, list(e.path)) for e in validator.iter_errors(_Load(path))]
            self.assertEqual([], errors, path)


class SampleSeedTest(unittest.TestCase):

    def test_second_quest_levels_show_their_partners_numbers(self):
        for path in (SAMPLE, ZORA_SAMPLE):
            self.assertEqual(SECOND_QUEST_NUMBERS,
                             {level['number']: level['shownNumber'] for level in _Load(path)['levels']}, path)

    def test_level_doors_are_named_by_the_shown_number(self):
        for path in (SAMPLE, ZORA_SAMPLE):
            doors = {screen['cave']['name']: screen['cave'] for screen in _Load(path)['overworld']['screens']
                     if screen['cave']['name'].startswith('Level ')}
            for code, shown in SECOND_QUEST_NUMBERS.items():
                self.assertEqual(('Level %d' % shown, 'L%d' % shown),
                                 (doors['Level %d' % code]['shownName'], doors['Level %d' % code]['shownShortName']))

    def test_pegasus_boots_are_named_as_boots(self):
        names = _ItemNames(_Load(SAMPLE))
        self.assertLessEqual({'Pegasus Boots', 'Magical Boots'}, names)
        self.assertFalse(names & {'Boomerang', 'Magical Boomerang'})
        # ZORA's 1.0 document names the same items as boomerangs.
        self.assertLessEqual({'Boomerang', 'Magical Boomerang'}, _ItemNames(_Load(ZORA_SAMPLE)))

    @unittest.skipUnless(_HasTestRom('zora-2q-boots-seed7.nes'), 'ZORA ROM not present')
    def test_sample_is_the_roms_reading(self):
        self.assertEqual(_Load(SAMPLE), _Read('zora-2q-boots-seed7.nes')['seed'] | {'producer': {
            'name': 'z1r-visualizer', 'version': 'sample'}})


class ReadTest(unittest.TestCase):

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_parsed_rom(self):
        result = _Read('zora-sword-seed1.nes')
        self.assertEqual('ok', result['status'])
        seed = result['seed']
        self.assertEqual(('z1r-seed', FORMAT_VERSION), (seed['format'], seed['formatVersion']))
        self.assertEqual({'name': 'z1r-visualizer', 'version': 'test'}, seed['producer'])
        self.assertEqual(list(range(1, 10)), [level['number'] for level in seed['levels']])
        self.assertEqual(45, len(seed['hints']))
        room = next(room for room in seed['levels'][3]['rooms'] if room['number'] == 0x0A)
        self.assertEqual({'name': 'Magical Sword', 'drop': True}, room['item'])
        self.assertEqual((5, 1), (room['column'], room['row']))  # the top row counts as 1
        self.assertIn({'name': 'Magical Sword Cave', 'kind': 'item', 'wares': [{'item': 'Heart Container'}]},
                      seed['caves'])
        self.assertEqual(json.loads(json.dumps(seed)), seed)  # plain JSON, nothing lost

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_transport_staircases_point_at_each_other(self):
        for level in _Read('zora-sword-seed1.nes')['seed']['levels']:
            rooms = {room['number']: room for room in level['rooms']}
            for room in rooms.values():
                stairs = room['staircase']
                if stairs and stairs['kind'] == 'transport':
                    other = rooms[stairs['to']]['staircase']
                    self.assertEqual(('transport', stairs['number'], room['number']),
                                     (other['kind'], other['number'], other['to']))

    @unittest.skipUnless(_HasTestRom('zora-progressive-seed1.nes'), 'ZORA ROM not present')
    def test_progressive_items_keep_their_own_names(self):
        seed = _Read('zora-progressive-seed1.nes')['seed']
        self.assertTrue(seed['progressiveItems'])
        cellar = next(room for room in seed['levels'][6]['rooms'] if room['number'] == 0x25)
        self.assertEqual({'kind': 'item', 'item': 'White Sword'}, cellar['staircase'])

    @unittest.skipUnless(_HasTestRom('zora-2q-seed1.nes'), 'ZORA ROM not present')
    def test_item_summary_by_shown_number(self):
        with open('testdata/zora-2q-seed1.nes', 'rb') as f:
            de = DataExtractor(io.BytesIO(f.read()))
        de.Parse()
        seed = _Read('zora-2q-seed1.nes')['seed']
        summary = ItemSummary(de)['levels']
        self.assertEqual([str(n) for n in range(1, 10)], list(summary))
        # Level 3 as shown is door code 2's level: its rooms are the summary's rooms.
        level = next(level for level in seed['levels'] if level['shownNumber'] == 3)
        self.assertEqual(2, level['number'])
        rooms = {'%X' % room['number'] for room in level['rooms']}
        self.assertTrue(summary['3'])
        self.assertLessEqual({row['Screen'] for row in summary['3']}, rooms)

    @unittest.skipUnless(_HasTestRom('zora-encoded-seed1.nes'), 'ZORA ROM not present')
    def test_encoded_rom_gives_no_seed(self):
        result = _Read('zora-encoded-seed1.nes')
        self.assertEqual('encoded', result['status'])
        self.assertIn("ZORA's level decoder", result['message'])
        self.assertEqual({'status', 'message', 'recorder'}, set(result))

    def test_not_a_rom(self):
        result = Read(b'not a rom', 'test')
        self.assertEqual({'status': 'unsupported', 'recorder': None}, {k: result[k] for k in ('status', 'recorder')})
        self.assertNotIn('seed', result)


if __name__ == '__main__':
    unittest.main()
