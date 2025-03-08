from bokeh.plotting import figure
from bokeh.transform import dodge
from bokeh.models import Legend, Line, ColumnDataSource, Rect
import pandas as pd
import streamlit as st
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
             plot_width=800,
            plot_height=400,
             x_range=x_range,
             y_range=list(reversed(y_range)),
             tools="hover",
             toolbar_location=None,
             tooltips=TOOLTIPS)
  r = p.rect("x_coord", "y_coord", 0.95, 0.95, source=df,
             fill_alpha=0.6, color='black')

  text_props = dict(source=df, text_align="left", text_baseline="middle")
  x = dodge("col", .1, range=p.x_range)
  p.text(x=x, y=dodge("y_coord", 0, range=p.y_range), text="cave_name_short",
                    text_font_size="14px", **text_props)
  p.outline_line_color = None
  p.grid.grid_line_color = None
  p.axis.visible = False
  p.axis.axis_line_color = None
  p.axis.major_tick_line_color = None
  p.axis.major_label_standoff = 0
             
  st.bokeh_chart(p)


def display_level(level_num):
  palette = de.GetLevelColorPalette(level_num)
  data = de.data[level_num]
  df = pd.DataFrame.from_dict(data, orient='index')

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
             tooltips=TOOLTIPS)

  r = p.rect("x_coord", "y_coord", 0.8, 0.8, source=df,
             fill_alpha=0.6, color=palette[2])
  r2 = p.rect("north.x", "north.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="north.color")
  r3 = p.rect("south.x", "south.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="south.color")
  r4 = p.rect("east.x", "east.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="east.color")
  r5 = p.rect("west.x", "west.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="west.color")

  r6 = p.rect("north.wall.x", "north.wall.y", 1, 0.01, source=df,
             fill_alpha=0.6, color="north.color")  #, legend_field="metal")
  r7 = p.rect("south.wall.x", "south.wall.y", 1, 0.01, source=df,
             fill_alpha=0.6, color="south.color")  #, legend_field="metal")
  r8 = p.rect("east.wall.x", "east.wall.y", 0.02, 1, source=df,
             fill_alpha=0.6, color="east.color")  #, legend_field="metal")
  r9 = p.rect("west.wall.x", "west.wall.y", 0.02, 1, source=df,
             fill_alpha=0.6, color="west.color")  #, legend_field="metal")

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
  solid_wall = p.add_glyph(
      source, Line(x="x", y="y", line_color="red", line_width=3, line_dash="solid"))
    
  legend = Legend(
         title='The Legend of Door & Wall Types',
         items=[
             ("Open Door    ", [open_door]),
             ("Shutter Door    ", [shutter_door]),
             ("Key-Locked Door    ", [locked_door]),
             ("Bombable Wall    ", [bomb_wall]),
             ("Walk-Through Wall    ", [walk_through_wall]),
             ("Solid Wall", [solid_wall])
           ],
         location='top_left', orientation='horizontal'
     )
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
  st.bokeh_chart(p)


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
    

successfully_parsed_level_data = False
st.set_page_config(page_title="Z1R Visualizer", layout="wide")
st.write(
    """
    # Z1R Visualizer
    """
)
    
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
        "ROMs created by Zelda Randomizer without the ‘Race ROM’ flag checked.",
        )
    st.stop()

de = DataExtractor(rom=uploaded_file)
try:
  de.Parse()
  successfully_parsed_level_data = True
except Exception as e:
  st.info("Sorry, this ROM doesn't seem to be supported. Features may not work correctly.")

options = [f"Level %d" % i for i in range(1, 10)] + ["Overworld", "Recorder Info"]
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
  