# The seed format, version 1.0

A JSON description of one Legend of Zelda seed **as a player sees it**: its dungeons, overworld
caves, shops, items and hint texts. It says nothing about how any program stores a seed, and
nothing about the ROM's bytes.

Two producers write it:
- the visualizer's ROM reader (`spoiler.py`; `cli.py --seed`);
- ZORA, directly from its own model, for the "View in Visualizer" hand-off (section 5).

The visualizer draws every view from it, whichever produced it.

The machine-readable definition is [`seed-format.schema.json`](seed-format.schema.json)
(JSON Schema, draft 2020-12). This page explains it. Where the two disagree, the schema wins
and this page is wrong.

## 1. Rules for producers

- **Never for an encoded seed.** A seed made with "Encode level data" (or Zelda Randomizer's
  "Race ROM") must stay unreadable to map viewers. A producer must not write a seed document for
  it. The visualizer's own reader refuses such ROMs and produces none.
- **Text only.** Every string is shown as plain text; nothing is ever run, parsed as HTML or
  fetched. Strings have length limits (see the schema).
- **Unknown fields are ignored** by readers of the same major version, which is what makes
  additive changes possible (section 4).

## 2. Top level

```json
{
  "format": "z1r-seed",
  "formatVersion": "1.0",
  "producer": { "name": "ZORA", "version": "0.3.0" },
  "seed": { "number": "12345", "flags": "...", "zoraFlags": "1.D", "code": ["Bow", "Raft", "Clock", "Fairy"] },
  "progressiveItems": false,
  "levels": [ ... ],
  "overworld": { "screens": [ ... ], "armos": "Power Bracelet", "coast": "Heart Container" },
  "caves": [ ... ],
  "hints": [ { "text": "THE GLEEOK HOLDS THE RED RING", "speaker": "Level 3, room 2A" } ],
  "recorder": { "text": "...", "notes": [ ... ] },
  "requirements": { "whiteSwordHearts": 5, "magicalSwordHearts": 12, "level9Triforces": 8, "doorRepairCost": 20 },
  "settings": [ { "id": "B08", "name": "Shuffle shop items", "chosen": "?", "resolved": "on" } ]
}
```

| Field | Required | What |
|---|---|---|
| `format` | yes | always `"z1r-seed"` |
| `formatVersion` | yes | `"<major>.<minor>"`; this page describes `1.0` |
| `producer` | yes | `name` and `version` of the program that wrote it. The visualizer shows them |
| `seed` | no | how the player made it: `number` (a string, since seed numbers can exceed JSON's safe integers), `flags`, `zoraFlags`, `code` (the seed's code, as item names) |
| `progressiveItems` | no | `true` when swords, candles, arrows, rings and boomerangs upgrade one level at a time (section 3.6). Default `false` |
| `levels` | yes | the dungeons, 1 to 9 of them (section 3.1) |
| `overworld` | yes | the screens with a cave, and the Armos and coast items (section 3.2) |
| `caves` | yes | the caves that give or sell items (section 3.3) |
| `hints` | yes | the game's texts, in the game's order (section 3.4) |
| `recorder` | no | a custom recorder tune, if the seed has one (section 3.5) |
| `requirements` | no | hearts needed for the white and magical swords, triforces needed for level 9, the door repair charge |
| `settings` | no | **ZORA extra.** Every setting, as the player chose it and as it resolved (section 3.7) |

## 3. The parts

### 3.1 Levels and rooms

```json
{ "number": 4, "color": "#5C94FC", "rooms": [
  { "number": 10, "column": 5, "row": 1, "type": "Chevy",
    "enemies": { "name": "Digdogger (3)" },
    "item": { "name": "Magical Sword", "drop": true },
    "staircase": null,
    "doors": { "north": "solid", "east": "open", "south": "locked", "west": "bombable" } } ] }
```

- **Level:**
  - `number`: 1-9.
  - `color`: the level's map colour, `#RRGGBB`.
  - `rooms`: the rooms a player can reach.
- **Room:**
  - `number`: 0-127, the game's room number; the visualizer shows it in hex.
  - `column` (1-8, from the left) and `row` (1-8, **from the top**): the room's place on the level's map.
  - `type`: the room's layout, e.g. "Entrance Room", "Spiral Stair".
  - `enemies`: `null` for none, or `name`, plus `count` when the game's group size applies. Bosses and other single foes have no count; their name may say how many, e.g. "Digdogger (3)".
    The dungeon's people are named by what they do. A reader shows these names as they are, so producers should use them:
    - "Bomb Upgrade": the person who sells more bomb capacity. The game sells it only in two levels (5 and 7 in vanilla).
    - "Talking Person": a person of the same kind in any other level, who only talks (vanilla has one in level 8).
    - "Mugger": the room that takes life or money.
    - "Hint #1" to "Hint #6": people who give a hint.
  - `item`: `null` for none, or the item's `name` (section 3.6) and `drop`. `drop` is `true` when the item appears once the room's enemies are beaten, `false` when it lies on the floor.
  - `staircase`: `null`, or one of:
    - `{"kind": "item", "item": <name or null>}`: a stairway down to an item cellar, with `null` for an empty cellar;
    - `{"kind": "transport", "number": n, "to": <room number>}`: one end of the level's transport staircase n, whose other end is room `to`. Both ends name each other and share `n`.
  - `doors`: for `north`, `east`, `south` and `west`, one of `open`, `solid`, `bombable`, `locked`, `walk-through` and `shutter`.

The visualizer draws a solid wall only between two rooms of the level. It works this out from
positions, so producers list every side.

### 3.2 Overworld

- `screens`: the screens with a cave entrance:
  - `number`: 0-127.
  - `column` (1-16) and `row` (1-8, from the top).
  - `cave`: its `name`, e.g. "White Sword Cave" or "Level 5", and `shortName`, the map label, e.g. "White" or "L5".
- `armos` and `coast`: the item under the Armos statue and the one on the coast; `null` for none.

### 3.3 Caves

```json
{ "name": "Shop 3", "kind": "shop", "wares": [ { "item": "Bow", "price": 98, "sellsOnce": true } ] }
```

- `kind`:
  - `item`: a cave that gives an item: the wood, white and magical sword caves, the letter cave;
  - `take-any`: the take-any cave;
  - `shop`;
  - `potion-shop`.
- `wares`: up to three, in the order the cave shows them:
  - `item`;
  - `price` (rupees, shops only);
  - `sellsOnce`: **ZORA extra**, `true` when a shop sells that ware only once.

The visualizer shows the caves in the order given. The item summary takes the `item` caves as
"Major Caves", and the shops and potion shop as "Shops".

### 3.4 Hints

The game's texts in its own order (old men, shopkeepers, hint shops), each `{"text": ...}`. The
visualizer numbers them from 0.
- `speaker`: **ZORA extra.** Who says it, in words, e.g. "Level 3, room 2A" or "Hint Shop 1".

### 3.5 Recorder

A custom recorder tune (a Zelda Randomizer option):
- `text`: its name.
- `notes`: the tune's bytes, up to 64.

The visualizer builds the IPS patch it offers from these.

### 3.6 Items and progressive items

Item names come from a fixed list (`$defs/itemName` in the schema): "Wood Sword", "White Sword",
"Magical Sword", "Blue Candle", "Red Candle", "Wooden Arrow", "Silver Arrow", "Bow", "Blue Ring",
"Red Ring", "Boomerang", "Magical Boomerang", "Heart Container", "Triforce", and the rest. One
more form is allowed: "Unknown Item XX", for a code a reader could not name.

Items always carry **their own** name. With `progressiveItems`, the visualizer shows the five
lines as "Sword Upgrade", "Candle Upgrade", "Arrow Upgrade", "Ring Upgrade" and "Boomerang
Upgrade". **ZORA extra:** this is the progressive-items meaning.

### 3.7 Settings (ZORA extra)

Each entry has:
- `name`, e.g. "Shuffle shop items".
- `id`: optional, e.g. "B08".
- `chosen`: what the player set: "on", "off", "?" or a value.
- `resolved`: what the seed used. For a "?", this is how it came out.

The visualizer lists them on its "Seed Info" view.

## 4. Versions

`formatVersion` is `"<major>.<minor>"`.

- **Additive changes** (a new optional field, a new item name, a new value of `kind`) raise the
  minor version. Readers of the same major version keep working: they ignore fields they do not
  know.
- **Breaking changes** (a field removed, renamed or retyped, a meaning changed, a new required
  field) raise the major version.
- The visualizer reads major version 1. It refuses any other major version, with a message naming
  the version it got and the one it reads. It validates every document against the schema before
  drawing it, and refuses one that does not validate, naming the first problems.

The schema allows unknown properties everywhere, so a 1.1 document validates against the 1.0
schema.

## 5. The hand-off: "View in Visualizer"

ZORA's page opens the visualizer in a new tab and hands it a seed by window messaging. Only seeds
made with "Encode level data" **off** may be offered.

1. **ZORA** registers a `message` listener, then opens the visualizer with an opener, so not with
   `noopener`:
   ```js
   const viz = window.open("https://tetraly.github.io/z1r-visualizer/", "_blank");
   ```
2. **The visualizer**, once loaded, posts this to its opener. It repeats it once a second for up
   to 30 seconds, until a seed arrives:
   ```js
   { type: "z1r-seed-ready", protocol: 1 }
   ```
3. **ZORA**, on a ready message whose `event.source === viz`, posts the seed as JSON text:
   ```js
   viz.postMessage({ type: "z1r-seed", protocol: 1, json: JSON.stringify(seedDocument) }, "*");
   ```
   `"*"` works from ZORA's single-file page (a `file://` page). A hosted ZORA can name the
   visualizer's origin instead. Answering every ready message is harmless: the same seed is
   drawn again.
4. **The visualizer** accepts only messages from its opener (`event.source === window.opener`),
   from any origin. A message must be an object with `type: "z1r-seed"`, `protocol: 1` and a
   string `json` of at most 4 MB. The JSON must parse to a seed document of a major version it
   reads, and validate against the schema. It then draws the seed, showing the producer and its
   version, and answers its opener:
   ```js
   { type: "z1r-seed-received", protocol: 1, ok: true }
   { type: "z1r-seed-received", protocol: 1, ok: false, error: "..." }
   ```
   Other messages are ignored. Nothing in a message is run or used as HTML.

The visualizer needs no Pyodide for this path, and does not load it unless the player also
chooses a ROM. A seed document saved as a `.json` file can also be opened with the page's file
chooser, which is handy for testing.

ZORA's side, in full:

```js
function viewInVisualizer(seedDocument) {
  const json = JSON.stringify(seedDocument);
  let viz = null;
  const onMessage = (event) => {
    if (event.source !== viz || !event.data) return;
    if (event.data.type === "z1r-seed-ready") viz.postMessage({ type: "z1r-seed", protocol: 1, json }, "*");
    if (event.data.type === "z1r-seed-received") {
      window.removeEventListener("message", onMessage);
      if (!event.data.ok) console.warn("The visualizer refused the seed:", event.data.error);
    }
  };
  window.addEventListener("message", onMessage);
  viz = window.open("https://tetraly.github.io/z1r-visualizer/", "_blank");
}
```
