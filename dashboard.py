import pandas as pd
import folium
import json
import streamlit as st
from streamlit_folium import st_folium

APP_TITLE =  'Portland Crime Analysis'
APP_SUBTITLE = 'Source: Portland Police Deptarment'

def display_statistics(df, neighborhood_name, metric_title):
    #df = df[(df['Neighborhood'] == neighborhood_name)]
    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]
        
    total = df['Count'].sum()
    st.metric(metric_title, '{:,}'.format(total))
def display_map(df):

    map = folium.Map(location=[45.5350, -122.675], zoom_start=11, scrollWheelZoom=False, tiles='CartoDB positron')

    choropleth = folium.Choropleth(
         geo_data='./portland.geojson',
         data=df,
         columns=("Neighborhood", "Count"), 
         key_on='feature.properties.name',
         line_opacity=0.8,
         highlight=True
    )
    choropleth.geojson.add_to(map)

    df = df.set_index('Neighborhood')

    for feature in choropleth.geojson.data['features']:
        neighborhood_name = feature['properties']['name']
        feature['properties']['records'] = 'Records: ' + str(df.loc[neighborhood_name, 'Count']) if neighborhood_name in df.index else 'N/A'

    choropleth.geojson.add_child(
         folium.features.GeoJsonTooltip(['name', 'records'], labels=False)
    )

    st_map = st_folium(map, width=700, height=450)

    neighborhood_name = ""
    if st_map['last_active_drawing']:
         neighborhood_name = st_map['last_active_drawing']['properties']['name']
    
    return neighborhood_name

def main():
    st.set_page_config(APP_TITLE)
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    df = pd.read_csv('portland-crime-data.csv', sep="\t")

    df['Neighborhood'] = df['Neighborhood'].fillna("") 
    neighborhood_counts = df["Neighborhood"].value_counts().reset_index()
    neighborhood_counts.columns = ["Neighborhood", "Count"]

    metric_title = f'# of Reports'
    
    neighborhood_name = ''
    crime = ''
    neighborhood_name = display_map(neighborhood_counts)
    display_statistics(neighborhood_counts, neighborhood_name, metric_title)

if __name__ == "__main__":
        main()
