import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, ALL
import plotly.express as px
import geopandas as gpd
import psycopg2

app = dash.Dash(__name__)

# Zugriff auf Datenbank
database = psycopg2.connect(database='mydb', user='marcelbauer', password='DBS123', host='localhost', port='5433')

# Laden der geojson-Dateien für die interaktive Map
geojson_data = gpd.read_file("bezirksgrenzen.geojson")
#geojson_data = gpd.read_file("lor_planungsraeume_2021.geojson")

# Layout der Map festlegen
app.layout = html.Div([
    html.H1('Fahrraddiebstähle in Berlin'),  #Header der map
    html.P('Wähle ein Bezirk um die Fahrraddiebstähle dort zu sehen'),
    dcc.Graph(
        id='map-graph',
        figure=px.choropleth_mapbox(
            geojson_data,
            geojson=geojson_data.geometry.__geo_interface__,
            locations=geojson_data.index,
            color='Gemeinde_name',
            color_continuous_scale='Viridis',
            range_color=(0, 12),
            mapbox_style='carto-positron',
            center={'lat': 52.5, 'lon': 13.5},
            zoom=8.5,
        ),
    ),
    html.Div(
        id='description',
        children=[
            html.H4('Wähle einen Planungsraum um die Tabelle danach zu filtern:'),
        ],
    ),
    html.Div(id='popup-div')
], className='container')

# Bezirk Name wird als globale variable genommen um überall darauf zugreifen zu können
bezirk_name = None

# Callbacks festlegen/ click handler
@app.callback(
    Output('popup-div', 'children'),
    [Input({'type': 'filter-button', 'index': ALL}, 'n_clicks'),
     Input('map-graph', 'clickData'),
    [State('popup-div', 'children')]
])

# Was beim click passiert
def update_popup_div(n_clicks_list, click_data,children):
    global bezirk_name
    
    # Was beim click auf einem Bezirk auf der Map passiert
    triggered_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if triggered_id == 'map-graph' and click_data is not None:
        location_id = click_data['points'][0]['location']
        bezirk_name = geojson_data.loc[location_id, 'Gemeinde_name']

        # Daten werden nach dem Bezirk aus der Datenbank in Postgresql entnommen
        cursor = database.cursor()
        last_query_command = "SELECT gemeinde_name, land_name, plr_name, stand, angelegt_am, tatzeit_anfang_datum, tatzeit_anfang_stunde, tatzeit_ende_datum, tatzeit_ende_stunde, schadenshoehe, versuch, art_des_fahrrads, delikt, erfassungsgrund FROM Bezirk, Planungsraum, Fahrraddiebstahl WHERE Gemeinde_name = %s AND Gemeinde_schluessel = bez AND lor = plr_id"
        result = cursor.fetchall()

        # eine Tabelle wird aus dem Informationen der Datenbank erstellt
        table_content = html.Div([
            html.Table(
                # Header der Tabelle
                [html.Tr([html.Th(column[0]) for column in cursor.description])] +
                # Reihen/rows der Tabelle
                [html.Tr([html.Td(cell) for cell in row]) for row in result]
            )
        ])

        # Die Filter Knöpfe/Button werden erstellt in dem man die Daten aus der ersten geojson-Datei mit der zweiten Vergleich, da die erste die Bezirke enthält und die zweite die Planungsräume
        filter_buttons = []
        for index, row in geojson_data.iterrows():
            if row['Gemeinde_name'] == bezirk_name:
                gemeinde_schluessel = row['Gemeinde_schluessel']
                matching_rows = geojson_data2[geojson_data2['BEZ'] == gemeinde_schluessel]
                for _, matching_row in matching_rows.iterrows():
                    plr_name = matching_row['PLR_NAME'].replace('-', '!')
                    button_id = {'type': 'filter-button', 'index': f'{index}-{plr_name}'}
                    filter_button = html.Button(
                        plr_name.replace('!', '-'),
                        id=button_id,
                        n_clicks=0,
                        style={'marginRight': '5px'},
                        value=plr_name
                    )
                    filter_buttons.append(filter_button)


        if children is None:
            children = []
        
        children = [child for child in children if 'Table' not in str(child) and 'Button' not in str(child)]
        children.extend(filter_buttons + [table_content])

    # Was beim Knopf/Button click passiert
    elif n_clicks_list:
        clicked_button_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]

        if 'filter-button' in clicked_button_id:
            # Name des Planungsraumes wird entnommen aus dem Knopf/Button um die Datenbank zu filtern
            plr_name = clicked_button_id.split('-')[1]
            plr_name = plr_name.replace('!', '-')
            plr_name = plr_name[:-16]

            # Daten werden aus der Datenbank entnommen, aber nur Reihen mit plr_name = ausgewähler Planungsraum
            cursor = database.cursor()
            cursor.execute("SELECT gemeinde_name, land_name, plr_name, stand, angelegt_am, tatzeit_anfang_datum, tatzeit_anfang_stunde, tatzeit_ende_datum, tatzeit_ende_stunde, schadenshoehe, versuch, art_des_fahrrads, delikt, erfassungsgrund FROM Bezirk, Planungsraum, Fahrraddiebstahl WHERE plr_name = %s AND Gemeinde_schluessel = bez AND lor = plr_id", (plr_name,))
            result = cursor.fetchall()

            # eine Tabelle wird aus dem Informationen der Datenbank erstellt
            table_content = html.Div([
                html.Table(
                    # Header der Tabelle
                    [html.Tr([html.Th(column[0]) for column in cursor.description])] +
                    # Reihen/rows der Tabelle
                    [html.Tr([html.Td(cell) for cell in row]) for row in result]
                )
            ])

            # Die Tabelle wird aktualisiert
            children = [child for child in children if 'Table' not in str(child)]
            children.append(table_content)

    return children



if __name__ == '__main__':
    app.run_server(debug=True)
