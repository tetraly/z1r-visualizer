import glob
import json
import os
import unittest

from constants import ITEM_TYPES
from spoiler import FORMAT_VERSION, Read

try:
    import jsonschema
except ImportError:  # the checks that need it skip
    jsonschema = None

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs', 'seed-format.schema.json')


def _Read(name):
    with open('testdata/%s' % name, 'rb') as f:
        return Read(f.read(), 'test')


def _HasTestRom(name):
    return os.path.exists('testdata/%s' % name)


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
