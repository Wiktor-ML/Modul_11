import dash_core_components as dcc
import dash_html_components as html

def render_tab(df):
    layout = html.Div([
        html.H1('Kanały sprzedaży', style={'text-align': 'center'}),
        html.Div([
            html.Div([
                # Dropdown wyboru kanału sprzedaży (Store_type)
                dcc.Dropdown(
                    id='store_dropdown',
                    options=[{'label': store, 'value': store} for store in df['Store_type'].unique()],
                    value=df['Store_type'].unique()[0]
                ),
                # Wykres słupkowy: sprzedaż wg dni tygodnia
                dcc.Graph(id='sales-day-chart')
            ], style={'width': '50%', 'display': 'inline-block'}),
            html.Div([
                # Wykres kołowy: klienci wg płci dla wybranego kanału
                dcc.Graph(id='customer-gender-chart')
            ], style={'width': '50%', 'display': 'inline-block'})
        ]),
            html.Br(),
            html.Div([
            html.H2('Kanał sprzedaży wg dnia tygodnia', style={'text-align': 'center'}),
            # Dropdown wyboru dnia tygodnia
            dcc.Dropdown(
                id='day_dropdown',
                options=[{'label': day, 'value': day} for day in 
                         ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]],
                value="Monday"
            ),
            # Wykres kolowy: sprzedaż wg kanału dla wybranego dnia tygodnia
            dcc.Graph(id='channel-pie-chart')
        ], style={'width': '80%', 'margin': 'auto'}) 
    ])
    return layout