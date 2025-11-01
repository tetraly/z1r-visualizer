from bokeh.plotting import figure
from bokeh.transform import dodge
from bokeh.core.properties import field
from bokeh.models import Legend, Line, ColumnDataSource, Rect
import pandas as pd
import streamlit as st
from streamlit_bokeh import streamlit_bokeh
from data_extractor import DataExtractor
import requests


def display_overworld():
    x_range = [str(x) for x in range(1, 17)]
    y_range = [str(y) for y in range(1, 9)]
    data = de.data[0]
    df = pd.DataFrame.from_dict(data, orient='index')
    TOOLTIPS = [
        ("Screen Number", "@{screen_num}"),
        ("Col", "@{col}"),
        ("Row", "@{row}"),
        ("Cave", "@{cave}"),
        ("Cave2", "@{cave_name}"),
        ("Cave3", "@{cave_name_short}"),
    ]
    p = figure(title="Overworld",
               width=800,
               height=400,
               x_range=x_range,
               y_range=list(reversed(y_range)),
               tools="hover",
               toolbar_location=None,
               tooltips=TOOLTIPS,
               background_fill_color="white",
               border_fill_color="white")

    # Force white background on the plot area
    p.background_fill_color = "white"
    p.border_fill_color = "white"
    p.outline_line_color = "black"

    r = p.rect("x_coord", "y_coord", 0.95, 0.95, source=df, fill_alpha=0.6, color='#4CAF50')

    text_props = dict(source=df, text_align="left", text_baseline="middle")
    x = dodge("col", .1, range=p.x_range)
    p.text(x=x,
           y=dodge("y_coord", 0, range=p.y_range),
           text="cave_name_short",
           text_font_size="14px",
           **text_props)
    p.outline_line_color = None
    p.grid.grid_line_color = None
    p.axis.visible = False
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.axis.major_label_standoff = 0

    # Don't use theme parameter - let the explicit colors work
    streamlit_bokeh(p, use_container_width=False, key="overworld")


def display_level(level_num):
    palette = de.GetLevelColorPalette(level_num)
    data = de.data[level_num]
    df = pd.DataFrame.from_dict(data, orient='index')

    # Debug: Check if we have data
    if df.empty:
        st.error(f"No data found for Level {level_num}")
        return

    # Rename columns to remove dots (Bokeh 3.8 doesn't like dots in column names)
    df.columns = df.columns.str.replace('.', '_', regex=False)

    # Ensure all color columns contain valid hex colors
    for color_col in ['north_color', 'south_color', 'east_color', 'west_color']:
        if color_col in df.columns:
            # Map color names to appropriate values:
            # - 'black' -> dark gray (for open doors)
            # - 'red' -> keep red (for solid walls that should be visible)
            # - '#000000' -> white (for solid walls that should blend in)
            # - everything else -> keep as-is
            def map_color(x):
                s = str(x)
                if s == 'black':
                    return '#333333'  # Dark gray for open doors
                elif s == '#000000':
                    return 'white'  # White for invisible solid walls
                elif pd.notna(x):
                    return s
                else:
                    return 'white'

            df[color_col] = df[color_col].apply(map_color)

    TOOLTIPS = [
        ("Room Number", "@{room_num}"),
        ("Col", "@{col}"),
        ("Row", "@{row}"),
        ("Stair", "@{stair_tooltip}"),
        ("Room Type", "@{room_type}"),
        ("Enemy Type", "@{enemy_type_tooltip}"),
        ("Num Enemies", "@{enemy_num_tooltip}"),
    ]
    x_range = [str(x) for x in range(1, 9)]
    y_range = [str(y) for y in range(1, 9)]

    p = figure(title="Level %d" % level_num,
               width=800,
               height=800,
               x_range=x_range,
               y_range=list(reversed(y_range)),
               tools="hover",
               toolbar_location=None,
               tooltips=TOOLTIPS,
               background_fill_color="white",
               border_fill_color="white")

    # Force white background on the plot area
    p.background_fill_color = "white"
    p.border_fill_color = "white"
    p.outline_line_color = "black"

    r = p.rect("x_coord", "y_coord", 0.8, 0.8, source=df, fill_alpha=0.6, color=palette[2])
    r2 = p.rect("north_x", "north_y", 0.1, 0.1, source=df, fill_alpha=0.6, color="north_color")
    r3 = p.rect("south_x", "south_y", 0.1, 0.1, source=df, fill_alpha=0.6, color="south_color")
    r4 = p.rect("east_x", "east_y", 0.1, 0.1, source=df, fill_alpha=0.6, color="east_color")
    r5 = p.rect("west_x", "west_y", 0.1, 0.1, source=df, fill_alpha=0.6, color="west_color")

    r6 = p.rect("north_wall_x",
                "north_wall_y",
                1,
                0.05,
                source=df,
                fill_alpha=0.6,
                color="north_color")  #, legend_field="metal")
    r7 = p.rect("south_wall_x",
                "south_wall_y",
                1,
                0.05,
                source=df,
                fill_alpha=0.6,
                color="south_color")  #, legend_field="metal")
    r8 = p.rect("east_wall_x",
                "east_wall_y",
                0.05,
                1,
                source=df,
                fill_alpha=0.6,
                color="east_color")  #, legend_field="metal")
    r9 = p.rect("west_wall_x",
                "west_wall_y",
                0.05,
                1,
                source=df,
                fill_alpha=0.6,
                color="west_color")  #, legend_field="metal")

    source = ColumnDataSource(data={'x': [-1], 'y': [-1], 'w': [.1], 'h': [.1]})
    bomb_wall = p.add_glyph(
        source, Rect(x="x", y="y", width="w", height="h", fill_color='blue', fill_alpha=0.6))
    locked_door = p.add_glyph(
        source, Rect(x="x", y="y", width="w", height="h", fill_color='orange', fill_alpha=0.6))
    walk_through_wall = p.add_glyph(
        source, Rect(x="x", y="y", width="w", height="h", fill_color='purple', fill_alpha=0.6))
    shutter_door = p.add_glyph(
        source, Rect(x="x", y="y", width="w", height="h", fill_color='brown', fill_alpha=0.6))
    open_door = p.add_glyph(
        source, Rect(x="x", y="y", width="w", height="h", fill_color='black', fill_alpha=0.6))
    solid_wall = p.add_glyph(source,
                             Line(x="x", y="y", line_color="red", line_width=3, line_dash="solid"))

    legend = Legend(title='The Legend of Door & Wall Types',
                    items=[("Open Door    ", [open_door]), ("Shutter Door    ", [shutter_door]),
                           ("Key-Locked Door    ", [locked_door]),
                           ("Bombable Wall    ", [bomb_wall]),
                           ("Walk-Through Wall    ", [walk_through_wall]),
                           ("Solid Wall", [solid_wall])],
                    location='top_left',
                    orientation='horizontal',
                    label_text_color='black')
    p.add_layout(legend, 'below')

    text_props = dict(source=df, text_align="left", text_baseline="middle")

    p.text(x=dodge("col", -0.86, range=p.x_range),
           y=dodge("row", -0.2, range=p.y_range),
           text="room_type",
           text_font_style="normal",
           text_font_size='8pt',
           **text_props)

    p.text(x=dodge("col", -0.86, range=p.x_range),
           y=dodge("row", -0.4, range=p.y_range),
           text="enemy_info",
           text_font_style="normal",
           text_font_size='8pt',
           **text_props)

    p.text(x=dodge("col", -0.86, range=p.x_range),
           y=dodge("row", -0.6, range=p.y_range),
           text="item_info",
           text_font_style="normal",
           text_font_size='8pt',
           **text_props)

    p.text(x=dodge("col", -0.86, range=p.x_range),
           y=dodge("row", -0.8, range=p.y_range),
           text="stair_info",
           text_font_style="normal",
           text_font_size='8pt',
           **text_props)

    p.outline_line_color = None
    p.grid.grid_line_color = None
    p.axis.visible = False
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.axis.major_label_standoff = 0
    p.hover.renderers = [r]  # only hover element boxes

    # Don't use theme parameter - let the explicit colors work
    streamlit_bokeh(p, use_container_width=False, key=f"level_{level_num}")


def display_recorder_info():
    recorder_data = de.GetRecorderData()
    if not recorder_data or recorder_data[0] == 0xFF:
        st.info("This ROM doesn't appear to have a custom recorder tune")
        return
    recorder_text = de.GetRecorderText().rstrip()
    st.write("Recorder Text: %s" % recorder_text)
    text_data = ""
    for val in recorder_data:
        text_data += "%02x " % val
    st.write("Recorder Data: %s" % text_data)

    recorder_patch_text = ""
    for val in de.GetRecorderPatchData():
        recorder_patch_text += "%02x " % val
    st.write("Recorder Patch Data: %s" % recorder_patch_text)
    output_filename = "%s.ips" % recorder_text.replace(" ", "_")
    st.download_button(
        label="Download recorder tune IPS patch (%s)" % output_filename,
        data=bytes(de.GetRecorderPatchData()),
        file_name=output_filename,
        mime="application/octet-stream",
    )


def display_item_summary():
    from constants import CAVE_NAME, ITEM_TYPES

    # Define items to exclude
    excluded_items = ["Rupee", "5 Rupees", "Bombs", "Key", "Map", "Compass", "Triforce", "No Item", "Nothing"]

    # Section 1: Level Items in 3x3 layout
    st.subheader("Dungeon Items")

    # Collect all level data first
    all_level_data = {}
    for level_num in range(1, 10):
        level_items = []
        if level_num in de.data:
            for room_num, room_data in de.data[level_num].items():
                # Check floor items
                if 'item_info' in room_data and room_data['item_info']:
                    item_text = room_data['item_info']
                    # Remove "D " prefix if it's a drop
                    is_drop = item_text.startswith("D ")
                    item_name = item_text[2:] if is_drop else item_text

                    if item_name and item_name not in excluded_items:
                        # Format screen number with leading zero
                        screen_str = room_data.get('room_num', hex(room_num))
                        if screen_str.startswith('0x'):
                            screen_str = '0x' + screen_str[2:].zfill(2)

                        level_items.append({
                            'Item': item_name,
                            'Screen': screen_str,
                            'Location': 'Drop' if is_drop else 'Floor'
                        })

                # Check stairway items
                if 'stair_info' in room_data and room_data['stair_info']:
                    stair_text = room_data['stair_info']
                    # Only include if it's not a transport staircase (starts with "Stair")
                    if not stair_text.startswith("Stair") and stair_text not in excluded_items:
                        # Format screen number with leading zero
                        screen_str = room_data.get('room_num', hex(room_num))
                        if screen_str.startswith('0x'):
                            screen_str = '0x' + screen_str[2:].zfill(2)

                        level_items.append({
                            'Item': stair_text,
                            'Screen': screen_str,
                            'Location': 'Item Stairway'
                        })

        all_level_data[level_num] = level_items

    # Display in 3x3 grid
    for row in range(3):
        cols = st.columns(3)
        for col_idx in range(3):
            level_num = row * 3 + col_idx + 1
            with cols[col_idx]:
                if level_num in all_level_data:
                    level_items = all_level_data[level_num]
                    if level_items:
                        st.write(f"**Level {level_num}:**")
                        df = pd.DataFrame(level_items)
                        st.markdown(df.to_html(index=False), unsafe_allow_html=True)
                    else:
                        st.write(f"**Level {level_num}:** No major items")

    # Section 2-4: Major Caves, Shops, and Overworld Items in 3 columns
    st.subheader("Caves, Shops, and Overworld Items")
    cols = st.columns(3)

    # Column 1: Major Caves
    with cols[0]:
        st.write("**Major Caves:**")
        cave_items = []
        major_caves = [0x10, 0x12, 0x13, 0x18]  # Wood Sword, White Sword, Magical Sword, Letter Cave

        for cave_type in major_caves:
            if cave_type in de.shop_data:
                cave_name = CAVE_NAME.get(cave_type, f"Cave {hex(cave_type)}")
                for i in range(3):
                    item_code = de.shop_data[cave_type][i]
                    # Special case: 0x03 in caves/shops is Magical Sword, not "No Item"
                    if item_code == 0x03:
                        cave_items.append({
                            'Cave': cave_name,
                            'Item': 'Magical Sword'
                        })
                    elif item_code != 0x3F and item_code in ITEM_TYPES:  # 0x3F is "Nothing"
                        cave_items.append({
                            'Cave': cave_name,
                            'Item': ITEM_TYPES[item_code]
                        })

        if cave_items:
            df = pd.DataFrame(cave_items)
            st.markdown(df.to_html(index=False), unsafe_allow_html=True)

    # Column 2: Shops
    with cols[1]:
        st.write("**Shops:**")
        shop_items = []
        shops = [0x1D, 0x1E, 0x1F, 0x20, 0x1A]  # Shop 1-4, Potion Shop

        for shop_type in shops:
            if shop_type in de.shop_data:
                shop_name = CAVE_NAME.get(shop_type, f"Shop {hex(shop_type)}")
                for i in range(3):
                    item_code = de.shop_data[shop_type][i]
                    # Special case: 0x03 in caves/shops is Magical Sword, not "No Item"
                    if item_code == 0x03:
                        price = de.shop_data[shop_type][i + 3]
                        shop_items.append({
                            'Shop': shop_name,
                            'Item': 'Magical Sword',
                            'Price': price
                        })
                    elif item_code != 0x3F and item_code in ITEM_TYPES:  # 0x3F is "Nothing"
                        price = de.shop_data[shop_type][i + 3]
                        shop_items.append({
                            'Shop': shop_name,
                            'Item': ITEM_TYPES[item_code],
                            'Price': price
                        })

        if shop_items:
            df = pd.DataFrame(shop_items)
            st.markdown(df.to_html(index=False), unsafe_allow_html=True)

    # Column 3: Armos and Coast Items
    with cols[2]:
        st.write("**Overworld Items:**")
        overworld_items = de.GetOverworldItems()
        if len(overworld_items) >= 2:
            ow_data = [
                {'Location': 'Armos', 'Item': overworld_items[0]},
                {'Location': 'Coast', 'Item': overworld_items[1]}
            ]
            df = pd.DataFrame(ow_data)
            st.markdown(df.to_html(index=False), unsafe_allow_html=True)


successfully_parsed_level_data = False
st.set_page_config(page_title="Z1R Visualizer", layout="wide")
st.write("""
    # Z1R Visualizer
    """)

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload a ROM by dragging and dropping a file or clicking the \"Browse Files\" button below.",
    key="1",
    help="Please upload a Legend of Zelda ROM",
)
if uploaded_file is None:
    st.info(
        "Please upload a Legend of Zelda ROM using the file widget above. "
        "Supported ROM types are vanilla Legend of Zelda ROMs and randomized "
        "ROMs created by Zelda Randomizer without the ‘Race ROM’ flag checked.",)
    st.stop()

de = DataExtractor(rom=uploaded_file)
try:
    de.Parse()
    successfully_parsed_level_data = True
except Exception as e:
    st.info("Sorry, this ROM doesn't seem to be supported. Features may not work correctly.")

options = [f"Level %d" % i for i in range(1, 10)] + ["Overworld", "Recorder Info", "Item Summary"]
selected_option = st.selectbox('What information would you like to display?', options)
if selected_option.startswith("Level"):
    if not successfully_parsed_level_data:
        st.info("Sorry, level maps aren't available for this ROM")
    else:
        display_level(int(selected_option.split(" ")[1]))
elif selected_option == "Overworld":
    if not successfully_parsed_level_data:
        st.info("Sorry, level maps aren't available for this ROM")
    else:
        display_overworld()
elif selected_option == "Recorder Info":
    display_recorder_info()
elif selected_option == "Item Summary":
    if not successfully_parsed_level_data:
        st.info("Sorry, item summary isn't available for this ROM")
    else:
        display_item_summary()
