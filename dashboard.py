import pandas as pd
import folium
import json
import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

APP_TITLE =  'Portland Crime Analysis'
APP_SUBTITLE = 'Source: Portland Police Department'

def prepare_dataset(df):
    df = df.dropna(subset=['Neighborhood'])
    df['Neighborhood'] = df['Neighborhood'].fillna("")
    df['OccurTime'] = df['OccurTime'].astype(str)

    return df
def format_time(unformatted_time):
    unformatted_time_str = str(unformatted_time).zfill(4)
    formatted_time = unformatted_time_str[:2] + ":" + unformatted_time_str[2:]
    return formatted_time

def display_statistics(df, neighborhood_name, metric_title):
    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]
    else:
        df = df.groupby('OffenseType')['Count'].sum().reset_index()

    total = df['Count'].sum()
    st.metric(metric_title, '{:,}'.format(total))

def display_crime_table(df, neighborhood_name):
    st.write("### Crime Occurrences by Offense Type")

    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]
    else:
        # Sum the values with the same offense types but different neighborhoods
        df = df.groupby(['OffenseType', 'Neighborhood'])['Count'].sum().reset_index()

    df = df.groupby('OffenseType')['Count'].sum().reset_index()
    df = df.sort_values(by='Count', ascending=False)
    df_top10 = df.head(10).reset_index(drop=True)
    df_top10.index += 1

    df_top10 = df_top10.rename(columns={'OffenseType': 'Offense Type'})
    df_top10 = df_top10.drop(columns=['Neighborhood'], errors='ignore')

    st.table(df_top10)

    # Return the top 10 crimes and their counts
    return df_top10['Offense Type'].tolist()

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

def display_occurtime(df, neighborhood_name, top_offense_types):
    st.write("### Crime Occurrence times")

    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]

    df['OccurHour'] = pd.to_datetime(df['OccurTime']).dt.hour

    figure = plt.figure(figsize=(12, 8))
    figure.patch.set_alpha(0.0)
    sns.set(style="darkgrid")
    sns.boxplot(x='OffenseType', y='OccurHour', data=df[df['OffenseType'].isin(top_offense_types)], width=0.5)
    plt.xlabel('', color='white')
    plt.ylabel('Hour of Occurrence', color='white')
    plt.title('Crime Occurrence time for Each Type')
    plt.yticks(ha='right', ticks=range(1, 24), color='white')  
    plt.xticks(rotation=45, ha='right', color='white')  
    
    st.pyplot(plt)

def main():
    st.set_page_config(APP_TITLE)
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    df = pd.read_csv('portland-crime-data.csv', sep="\t")
    df = prepare_dataset(df)
    df['OccurTime'] = df['OccurTime'].apply(format_time)

    neighborhood_counts = df["Neighborhood"].value_counts().reset_index()
    neighborhood_counts.columns = ["Neighborhood", "Count"]

    offensetype_counts = df["Neighborhood"].value_counts().reset_index()
    offensetype_counts = df.groupby(['Neighborhood', 'OffenseType']).size().reset_index(name='Count')

    occur_times = df.groupby(['Neighborhood', 'OffenseType', 'OccurTime']).size().reset_index(name='Count')

    metric_title = f'Number of Reports'
    neighborhood_name = display_map(neighborhood_counts)

    top_offense_types_neighborhood = display_crime_table(offensetype_counts, neighborhood_name)
    
    display_statistics(offensetype_counts, neighborhood_name, metric_title)
    display_occurtime(occur_times, neighborhood_name, top_offense_types_neighborhood)
    
if __name__ == "__main__":
        main()
