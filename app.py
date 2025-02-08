import os
import pandas as pd
import datetime as dt

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

import dash_auth
import plotly.graph_objs as go

# Klasa DB do wczytywania i łączenia danych
class DB:
    def __init__(self):
        self.transactions = self.transaction_init()
        self.cc = pd.read_csv(r'db/country_codes.csv', index_col=0)
        self.customers = pd.read_csv(r'db/customers.csv', index_col=0)
        self.prod_info = pd.read_csv(r'db/prod_cat_info.csv')
    
    @staticmethod
    def transaction_init():
        transactions = pd.DataFrame()
        src = os.path.join(os.getcwd(), 'db', 'transactions')
        for filename in os.listdir(src):
            filepath = os.path.join(src, filename)
            transactions = pd.concat([transactions, pd.read_csv(filepath, index_col=0)], 
                                  ignore_index=True)
        
        def convert_dates(x):
            try:
                return dt.datetime.strptime(x, '%d-%m-%Y')
            except:
                return dt.datetime.strptime(x, '%d/%m/%Y')
        transactions['tran_date'] = transactions['tran_date'].apply(convert_dates)
        return transactions

    def merge(self):
        # Łączenie kategorii produktów
        df = self.transactions.join(
            self.prod_info.drop_duplicates(subset=['prod_cat_code'])
                         .set_index('prod_cat_code')['prod_cat'],
            on='prod_cat_code', how='left'
        )
        df = df.join(
            self.prod_info.drop_duplicates(subset=['prod_sub_cat_code'])
                         .set_index('prod_sub_cat_code')['prod_subcat'],
            on='prod_subcat_code', how='left'
        )
        # Łączenie klientów i krajów
        df = df.join(
            self.customers.join(self.cc, on='country_code')
                          .set_index('customer_Id'),
            on='cust_id'
        )
        self.merged = df

# Inicjalizacja danych
db_instance = DB()
db_instance.merge()

# Konfiguracja Basic Auth
USERNAME_PASSWORD = [['user', 'pass']]

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
auth = dash_auth.BasicAuth(app, USERNAME_PASSWORD)

# Layout główny z zakładkami
app.layout = html.Div([
    html.Div([
        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='Sprzedaż globalna', value='tab-1'),
            dcc.Tab(label='Produkty', value='tab-2'),
            dcc.Tab(label='Kanały sprzedaży', value='tab-3')
        ]),
        html.Div(id='tabs-content')
    ], style={'width': '80%', 'margin': 'auto'})
], style={'height': '100%'})

# Import layoutów zakładek
import tab1
import tab2
import tab3

# Callback renderujący zawartość zakładki
@app.callback(Output('tabs-content', 'children'),
              [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return tab1.render_tab(db_instance.merged)
    elif tab == 'tab-2':
        return tab2.render_tab(db_instance.merged)
    elif tab == 'tab-3':
        return tab3.render_tab(db_instance.merged)

# CALLBACKS DLA TAB1


# Wykres słupkowy - przychody w kolejnych miesiącach
@app.callback(Output('bar-sales', 'figure'),
              [Input('sales-range', 'start_date'),
               Input('sales-range', 'end_date')])
def tab1_bar_sales(start_date, end_date):
    # Convert string dates to datetime objects
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    truncated = db_instance.merged[(db_instance.merged['tran_date'] >= start_date) &
                                   (db_instance.merged['tran_date'] <= end_date)]
    grouped = truncated[truncated['total_amt'] > 0].groupby(
        [pd.Grouper(key='tran_date', freq='M'), 'Store_type']
    )['total_amt'].sum().round(2).unstack()
    
    traces = []
    for col in grouped.columns:
        traces.append(go.Bar(
            x=grouped.index, 
            y=grouped[col], 
            name=col,
            hoverinfo='text',
            hovertext=[f'{y/1e3:.2f}k' for y in grouped[col].values]
        ))
    fig = go.Figure(
        data=traces,
        layout=go.Layout(title='Przychody', barmode='stack', legend=dict(x=0, y=-0.5))
    )
    return fig

# Kartogram sprzedaży wg krajów
@app.callback(Output('choropleth-sales', 'figure'),
              [Input('sales-range', 'start_date'),
               Input('sales-range', 'end_date')])
def tab1_choropleth_sales(start_date, end_date):
    # Convert string dates to datetime objects
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    truncated = db_instance.merged[(db_instance.merged['tran_date'] >= start_date) &
                                   (db_instance.merged['tran_date'] <= end_date)]
    grouped = truncated[truncated['total_amt'] > 0].groupby('country')['total_amt'].sum().round(2)
    trace0 = go.Choropleth(
        colorscale='Viridis',
        reversescale=True,
        locations=grouped.index,
        locationmode='country names',
        z=grouped.values,
        colorbar=dict(title='Sales')
    )
    fig = go.Figure(
        data=[trace0],
        layout=go.Layout(
            title='Mapa',
            geo=dict(showframe=False, projection={'type': 'natural earth'})
        )
    )
    return fig

# CALLBACK DLA TAB2

# Poziomy wykres słupkowy zależny od dropdowna
@app.callback(Output('barh-prod-subcat', 'figure'),
              [Input('prod_dropdown', 'value')])
def tab2_barh_prod_subcat(chosen_cat):
    df = db_instance.merged
    grouped = df[(df['total_amt'] > 0) & (df['prod_cat'] == chosen_cat)].pivot_table(
        index='prod_subcat', columns='Gender', values='total_amt', aggfunc='sum'
    ).assign(_sum=lambda x: x['F'] + x['M']).sort_values(by='_sum').round(2)
    
    traces = []
    for col in ['F', 'M']:
        traces.append(go.Bar(
            x=grouped[col],
            y=grouped.index,
            orientation='h',
            name=col
        ))
    fig = go.Figure(data=traces, layout=go.Layout(barmode='stack', margin={'t': 20}))
    return fig

# CALLBACKS DLA TAB3 - nowa zakładka "Kanały sprzedaży"

# Wykres słupkowy: sprzedaż wg dni tygodnia dla wybranego kanału
@app.callback(Output('sales-day-chart', 'figure'),
              [Input('store_dropdown', 'value')])
def update_sales_day_chart(chosen_store):
    df = db_instance.merged
    filtered = df[df['Store_type'] == chosen_store].copy()
    # Dodajemy kolumnę z dniem tygodnia
    filtered['day_of_week'] = filtered['tran_date'].dt.day_name()
    # Grupujemy po dniach tygodnia i sumujemy sprzedaż
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    grouped = filtered.groupby('day_of_week')['total_amt'].sum().reindex(day_order).fillna(0)
    fig = go.Figure(
        data=[go.Bar(x=grouped.index, y=grouped.values)],
        layout=go.Layout(title=f'Sprzedaż wg dni tygodnia dla {chosen_store}')
    )
    return fig

# Wykres kołowy: analiza klientów wg płci dla wybranego kanału
@app.callback(Output('customer-gender-chart', 'figure'),
              [Input('store_dropdown', 'value')])
def update_customer_gender_chart(chosen_store):
    df = db_instance.merged
    filtered = df[df['Store_type'] == chosen_store]
    # Liczymy unikalnych klientów wg płci
    customers = filtered.groupby('Gender')['cust_id'].nunique()
    fig = go.Figure(
        data=[go.Pie(labels=customers.index, values=customers.values)],
        layout=go.Layout(title=f'Klienci wg płci dla {chosen_store}')
    )
    return fig

# Wykres kołowy: kanał sprzedaży dla wybranego dnia
@app.callback(Output('channel-pie-chart', 'figure'),
              [Input('day_dropdown', 'value')])
def update_channel_pie_chart(selected_day):

    df = db_instance.merged.copy()
    # Dodaj kolumnę z nazwą dnia tygodnia
    df['day_of_week'] = df['tran_date'].dt.day_name()
    # Filtruj dane dla wybranego dnia
    filtered = df[df['day_of_week'] == selected_day]
    # Grupuj dane wg kanału sprzedaży i sumuj obroty
    grouped = filtered.groupby('Store_type')['total_amt'].sum()
    
    fig = go.Figure(
        data=[go.Pie(labels=grouped.index, values=grouped.values)],
        layout=go.Layout(title=f'Kanał sprzedaży dla {selected_day}')
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
