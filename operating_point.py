import numpy as np
import pandas as pd 
import plotly.graph_objs as go
import dash
import base64
import io
from dash import html, dcc, Input, Output, State
from scipy.interpolate import make_interp_spline
import math

df = pd.read_csv('pump_curve.csv')
discharge = np.linspace(df['discharge'].min(), df['discharge'].max(), 300)
spline1 = make_interp_spline(df['discharge'], df['head'], k=3)
spline2 = make_interp_spline(df['discharge'], df['efficiency'], k=3)
head = spline1(discharge)
efficiency = spline2(discharge)


D = [4,5,6,8,10,12,14,16,18,20,24]
d_inner = [4.026, 5.047, 6.065, 7.981, 10.02, 11.938, 13.125, 15, 16.874, 18.814, 22.626]
diameters = pd.DataFrame(
    {
        "D": D,
        "d_optimum": D,
        "d_inner": d_inner
    }
).set_index("D")

d_names = ['{} in'.format(i) for i in D]

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))

    except Exception as e:
        print(e)
        return None

    return df

app = dash.Dash(__name__)

server = app.server

app.layout = html.Div(
  children=[
    html.H1(
      "Welcome to Operating Point Calculator"
    ),
    html.H2(
      "This is the pump curve used in calculations:",
    ),
    html.Div(
      [
        html.Div(
          [
            dcc.Graph(
              id="pump-curve-graph",
              className="graph"
            )
          ],
            style={
                'width': '70%',
                'display': 'inline-block',
                'margin': 'auto',
                'padding': '20px',  
            },
            className="division"
        ),
        html.Div(
          [
            html.H3("Adjust pump curve:"),
            html.Label("Number of parallel pumps: "),
            dcc.Slider( 
              id='parallel_pumps',
              min=1,
              max=5,
              value=1,
              step=1,
              marks={i: str(i) for i in range(1, 6)},
              className="slider"
            ),
            html.Label("Number of series pumps: "),
            dcc.Slider( 
              id='series_pumps',
              min=1,
              max=10,
              step=1,
              value=1,
              marks={i: str(i) for i in range(1, 11)},
              className="slider"
            ),
            html.Label("Upload a pump curve (optional):"),
            dcc.Upload(
              id='upload-data',
              children=html.Div([
                'Drag and Drop or ',
                html.A('(Select Files)')
              ]),
              className="uploadfile",
              multiple=False),
              html.Pre(id='upload-status', className='uploadstatus'),
              html.Div(
                  [
                    html.Div(
                        [
                            html.Label("Viscosity (cp): "),
                            html.Br(),
                            html.Label("Density (kg/m3): "),
                            html.Br(),
                            html.Label("Length (km): "),
                            html.Br(),
                            html.Label("Delta Z (m): "),

                        ],style={'width':'40%', 'display':'inline-block', 'margin-bottom':'10px'}
                    ),
                    html.Div(
                        [
                            dcc.Input(id='viscosity', type='number', placeholder='viscosity', value=10, className='inputbox'),
                            html.Br(),
                            dcc.Input(id='density', type='number', placeholder='density', value=820, className='inputbox'),
                            html.Br(), 
                            dcc.Input(id='length', type='number', placeholder='length', value=20, className='inputbox'),
                            html.Br(),
                            dcc.Input(id='z', type='number', placeholder='z', value=50, className='inputbox'),
                        ],style={'width':'40%', 'display':'inline-block', 'margin-bottom':'10px'}
                    ),
                    html.Br(),
                    html.Label("Pipe diameter (in): "),
                    dcc.Dropdown(D, 8, id='pipediameter')
                  ]

              ),
          ],
          style={
            'width': '25%',
            'margin': 'auto'
          },
          className="division"
        )
      ],
      style={
        'color': '#FFFFFF',
        'padding': '20px',
        'display': 'flex'
      },
      className="division"

    )
  ],
  className="outermostdiv"
)


@app.callback(
        Output('pump-curve-graph', 'figure'),
        [
            Input('parallel_pumps', 'value'),
            Input('series_pumps', 'value'),
            Input('upload-data', 'contents'),
            Input('upload-data', 'filename'),
            Input('viscosity', 'value'),
            Input('density', 'value'),
            Input('length', 'value'),
            Input('z', 'value'),
            Input('pipediameter', 'value'),
        ]
        )
def update_pump_curve(parallel, series, contents, filename, viscosity, density, length, z, pipediameter):
    global discharge
    global head
    global efficiency
    global pipe_discharge_
    global pipe_losses_
    global d_inner
    global diameters
    parallel = int(parallel)
    series = int(series)
    pipediameter = int(pipediameter)
    Q = np.linspace(0.0001, 450, 20)
    ht_list = []
    for q in Q:
        r = 0.0018/diameters.loc[pipediameter]["d_optimum"]
        re = 13.924*(q*density / (viscosity*diameters.loc[pipediameter]["d_inner"]))
        x = math.log(1/((7/re)**0.9+(0.27*r)), math.e)
        a=(2.457*x)**16
        b=(37.53/re)**16
        f=8*((8/re)**12+(1/(a+b)**1.5))**(1/12)
        hf=603.042*(f*(q**2)*(length))/(diameters.loc[pipediameter]["d_inner"]**5)
        ht=1.15*hf+z+30
        ht_list.append(ht)

    if contents is not None:
        df = parse_contents(contents, filename)
        discharge = np.linspace(df['discharge'].min(), df['discharge'].max(), 300)
        spline1 = make_interp_spline(df['discharge'], df['head'], k=3)
        spline2 = make_interp_spline(df['discharge'], df['efficiency'], k=3)
        head = spline1(discharge)
        efficiency = spline2(discharge)
    trace1 = go.Scatter(x=discharge*parallel, y=head*series, mode='lines', yaxis='y1', name='Pump Head (m)')
    trace2 = go.Scatter(x=discharge*parallel, y=efficiency, mode='lines', yaxis='y2', name='Pump Efficiency')
    trace3 = go.Scatter(x=Q, y=ht_list, mode='lines', yaxis='y1', name='Pipeline Losses (m)')
    pump_curve_data = [trace1, trace2, trace3]
    pump_curve_layout = go.Layout(
        title='Pump Characteristic Curve',
        xaxis={
            'title': 'Discharge (m^3/hr)',
            'range': [0, 450],
            'gridcolor': '#908d96'
        },
        yaxis={
            'title': 'Head (m)',
            'range': [0, np.array(ht_list).max()+0.1*np.array(ht_list).max()],
            'gridcolor': '#908d96'
        },
        yaxis2={
            'title': 'Efficiency',
            'overlaying': 'y1',
            'side': 'right',
            'showgrid': False,
            'range': [0.3, 0.9]
        },
        font={
            'color': '#FFFFFF',
            'size': 16
        },
        legend={'x':1.1, 'y':1},
        paper_bgcolor='#46434c',
        plot_bgcolor='#46434c'
        )
    return go.Figure(pump_curve_data, pump_curve_layout)

@app.callback(
        Output('upload-status', 'children'),
        [Input('upload-data', 'filename')]
)
def update_upload_status(filename):
    if filename is not None:
        return "Pump Curve is Uploaded Successfully"
    else:
        return "Default Pump Curve is Used"

if __name__ == "__main__":
    app.run_server(debug=True)