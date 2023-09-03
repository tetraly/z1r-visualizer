from bokeh.plotting import figure
from bokeh.transform import dodge
import pandas as pd
import streamlit as st
from data_extractor import DataExtractor

try:
    st.set_page_config(layout="wide")
except:
    st.beta_set_page_config(layout="wide")
    
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload a Legend of Zelda ROM by dragging and dropping a file or clicking the \"Browse Files\" button below.",
    key="1",
    help="Please upload a Legend of Zelda ROM",
)
if uploaded_file is None:
    st.info(
        "Please upload a Legend of Zelda ROM using the file widget above.")
    st.stop()

try:
  de = DataExtractor(uploaded_file)
except Exception:
  st.info("Sorry, this ROM doesn't isn't supported. Please try a different ROM.")
  st.stop()
  
level_number_selectbox = st.selectbox(
    'Which level to display?',
    ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'))
level_number = int(level_number_selectbox)
assert level_number in range(0,10)

if level_number == 0:
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
  p = figure(title="Level %d" % level_number,
        plot_width=800, plot_height=400,
         #    width=700,
        #     height=400,
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

else:
  palette = de.GetLevelColorPalette(level_number)
  data = de.data[level_number]
  df = pd.DataFrame.from_dict(data, orient='index')

  TOOLTIPS = [
      ("Room Number", "@{room_num}"),
      ("Col", "@{col}"),
      ("Row", "@{row}"),
      ("Stairway", "@{stairway_info}"),
  ]
  x_range = [str(x) for x in range(1, 9)]
  y_range = [str(y) for y in range(1, 9)]

  p = figure(title="Level %d" % level_number,
             width=800,
             height=800,
             x_range=x_range,
             y_range=list(reversed(y_range)),
             tools="hover",
             toolbar_location=None,
             tooltips=TOOLTIPS)

  r = p.rect("x_coord", "y_coord", 0.8, 0.8, source=df,
             fill_alpha=0.6, color=palette[2])  #, legend_field="metal")
  r2 = p.rect("north.x", "north.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="north.color")  #, legend_field="metal")
  r3 = p.rect("south.x", "south.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="south.color")  #, legend_field="metal")
  r4 = p.rect("east.x", "east.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="east.color")  #, legend_field="metal")
  r5 = p.rect("west.x", "west.y", 0.1, 0.1, source=df,
             fill_alpha=0.6, color="west.color")  #, legend_field="metal")

  r6 = p.rect("north.wall.x", "north.wall.y", 1, 0.01, source=df,
             fill_alpha=0.6, color="red")  #, legend_field="metal")
  r7 = p.rect("south.wall.x", "south.wall.y", 1, 0.01, source=df,
             fill_alpha=0.6, color="red")  #, legend_field="metal")
  r8 = p.rect("east.wall.x", "east.wall.y", 0.02, 1, source=df,
             fill_alpha=0.6, color="red")  #, legend_field="metal")
  r9 = p.rect("west.wall.x", "west.wall.y", 0.02, 1, source=df,
             fill_alpha=0.6, color="red")  #, legend_field="metal")

  text_props = dict(source=df, text_align="left", text_baseline="middle")
  p.text(x="col", y="row", text="room_num", text_font_style="bold", **text_props)
  p.outline_line_color = None
  p.grid.grid_line_color = None
  p.axis.visible = False
  p.axis.axis_line_color = None
  p.axis.major_tick_line_color = None
  p.axis.major_label_standoff = 0
  p.hover.renderers = [r]  # only hover element boxes
  st.bokeh_chart(p)
