import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from data_extractor import DataExtractor
import requests


def display_overworld():
    data = de.data[0]
    df = pd.DataFrame.from_dict(data, orient='index')

    fig = go.Figure()

    # Add room rectangles as scatter markers
    fig.add_trace(go.Scatter(
        x=df['x_coord'],
        y=df['y_coord'],
        mode='markers+text',
        marker=dict(
            size=80,
            color='#4CAF50',
            opacity=0.6,
            symbol='square',
            line=dict(color='black', width=1)
        ),
        text=df['cave_name_short'],
        textposition='middle right',
        textfont=dict(size=14),
        customdata=df[['screen_num', 'col', 'row', 'cave', 'cave_name', 'cave_name_short']],
        hovertemplate='<br>'.join([
            '<b>Screen Number:</b> %{customdata[0]}',
            '<b>Col:</b> %{customdata[1]}',
            '<b>Row:</b> %{customdata[2]}',
            '<b>Cave:</b> %{customdata[3]}',
            '<b>Cave2:</b> %{customdata[4]}',
            '<b>Cave3:</b> %{customdata[5]}',
            '<extra></extra>'
        ]),
        showlegend=False
    ))

    # Configure layout
    fig.update_layout(
        title="Overworld",
        width=800,
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            range=[0.5, 16.5],
            showgrid=False,
            showticklabels=False,
            zeroline=False
        ),
        yaxis=dict(
            range=[0.5, 8.5],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            autorange='reversed'  # Reverse y-axis to match Bokeh
        ),
        hovermode='closest'
    )

    st.plotly_chart(fig, use_container_width=False, key="overworld")


def display_level(level_num):
    palette = de.GetLevelColorPalette(level_num)
    data = de.data[level_num]
    df = pd.DataFrame.from_dict(data, orient='index')

    # Debug: Check if we have data
    if df.empty:
        st.error(f"No data found for Level {level_num}")
        return

    # Map color names for walls/doors
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

    # Map color columns if they exist
    for color_col in ['north_color', 'south_color', 'east_color', 'west_color']:
        if color_col in df.columns:
            df[color_col] = df[color_col].apply(map_color)

    fig = go.Figure()

    # Add main room rectangles
    fig.add_trace(go.Scatter(
        x=df['x_coord'],
        y=df['y_coord'],
        mode='markers',
        marker=dict(
            size=90,
            color=palette[2],
            opacity=0.6,
            symbol='square',
            line=dict(color='black', width=1)
        ),
        customdata=df[['room_num', 'col', 'row', 'stair_tooltip', 'room_type',
                       'enemy_type_tooltip', 'enemy_num_tooltip']],
        hovertemplate='<br>'.join([
            '<b>Room Number:</b> %{customdata[0]}',
            '<b>Col:</b> %{customdata[1]}',
            '<b>Row:</b> %{customdata[2]}',
            '<b>Stair:</b> %{customdata[3]}',
            '<b>Room Type:</b> %{customdata[4]}',
            '<b>Enemy Type:</b> %{customdata[5]}',
            '<b>Num Enemies:</b> %{customdata[6]}',
            '<extra></extra>'
        ]),
        showlegend=False
    ))

    # Add walls using shapes (much cleaner than separate glyphs!)
    for _, room in df.iterrows():
        # North wall
        if 'north_wall_x' in df.columns and pd.notna(room.get('north_wall_x')):
            fig.add_shape(
                type="rect",
                x0=room['north_wall_x'] - 0.5, y0=room['north_wall_y'] - 0.025,
                x1=room['north_wall_x'] + 0.5, y1=room['north_wall_y'] + 0.025,
                fillcolor=room.get('north_color', 'white'),
                opacity=0.6,
                line=dict(width=0)
            )

        # South wall
        if 'south_wall_x' in df.columns and pd.notna(room.get('south_wall_x')):
            fig.add_shape(
                type="rect",
                x0=room['south_wall_x'] - 0.5, y0=room['south_wall_y'] - 0.025,
                x1=room['south_wall_x'] + 0.5, y1=room['south_wall_y'] + 0.025,
                fillcolor=room.get('south_color', 'white'),
                opacity=0.6,
                line=dict(width=0)
            )

        # East wall
        if 'east_wall_x' in df.columns and pd.notna(room.get('east_wall_x')):
            fig.add_shape(
                type="rect",
                x0=room['east_wall_x'] - 0.025, y0=room['east_wall_y'] - 0.5,
                x1=room['east_wall_x'] + 0.025, y1=room['east_wall_y'] + 0.5,
                fillcolor=room.get('east_color', 'white'),
                opacity=0.6,
                line=dict(width=0)
            )

        # West wall
        if 'west_wall_x' in df.columns and pd.notna(room.get('west_wall_x')):
            fig.add_shape(
                type="rect",
                x0=room['west_wall_x'] - 0.025, y0=room['west_wall_y'] - 0.5,
                x1=room['west_wall_x'] + 0.025, y1=room['west_wall_y'] + 0.5,
                fillcolor=room.get('west_color', 'white'),
                opacity=0.6,
                line=dict(width=0)
            )

    # Add text annotations (no more dodge hacks!)
    for _, room in df.iterrows():
        # Stack 4 lines of text per room
        texts = [
            room.get('room_type', ''),
            room.get('enemy_info', ''),
            room.get('item_info', ''),
            room.get('stair_info', '')
        ]

        # Combine into one annotation with line breaks
        text_combined = '<br>'.join([t for t in texts if t])

        if text_combined:
            fig.add_annotation(
                x=room['col'] - 0.36,
                y=room['row'],
                text=text_combined,
                showarrow=False,
                xanchor='left',
                yanchor='middle',
                font=dict(size=8),
                align='left'
            )

    # Configure layout
    fig.update_layout(
        title=f"Level {level_num}",
        width=800,
        height=800,
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(
            range=[0.5, 8.5],
            showgrid=False,
            showticklabels=False,
            zeroline=False
        ),
        yaxis=dict(
            range=[0.5, 8.5],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            autorange='reversed'
        ),
        hovermode='closest',
        # Add legend with dummy traces
        showlegend=True,
        legend=dict(
            title=dict(text='The Legend of Door & Wall Types'),
            orientation='h',
            yanchor='top',
            y=-0.05,
            xanchor='center',
            x=0.5
        )
    )

    # Add legend items (without dummy data sources!)
    legend_items = [
        ('Open Door', '#333333'),
        ('Shutter Door', 'brown'),
        ('Key-Locked Door', 'orange'),
        ('Bombable Wall', 'blue'),
        ('Walk-Through Wall', 'purple'),
    ]

    for name, color in legend_items:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=10, color=color, opacity=0.6, symbol='square'),
            name=name,
            showlegend=True
        ))

    # Add solid wall to legend as a line
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        line=dict(color='red', width=3),
        name='Solid Wall',
        showlegend=True
    ))

    st.plotly_chart(fig, use_container_width=False, key=f"level_{level_num}")


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
