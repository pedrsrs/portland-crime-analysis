import pandas as pd
import folium
import json
import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

session_state = st.session_state
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

def add_sidebar_neighborhood_filter(df, selected_map=None):
    unique_neighborhoods = df['Neighborhood'].unique().tolist()
    unique_neighborhoods.insert(0, "All")  # Add "All" option at the beginning
    default_value = selected_map if selected_map else unique_neighborhoods[0]
    neighborhood_filter = st.sidebar.selectbox("Neighborhood", unique_neighborhoods, index=unique_neighborhoods.index(default_value))
    if neighborhood_filter == "All":
        neighborhood_filter = ""
    return neighborhood_filter

def add_sidebar_crime_filter(df):
    unique_offense_types = df['OffenseType'].unique().tolist()
    unique_offense_types.insert(0, "All")  # Add "All" option at the beginning
    default_value = unique_offense_types[0]
    crime_filter = st.sidebar.selectbox("Offense Types", unique_offense_types, index=unique_offense_types.index(default_value))
    if crime_filter == "All":
        crime_filter = ""
    return crime_filter

def display_statistics(df, neighborhood_name, metric_title):
    total = 0  
    df_offensetype = df.groupby('OffenseType')['Count'].sum().reset_index()
    total_neighborhood = df_offensetype['Count'].sum()
    if neighborhood_name:
        df_neighborhood = df[df['Neighborhood'] == neighborhood_name]
        neighborhood_record = df_neighborhood['Count'].sum()

        average_neighborhood = total_neighborhood / len(df['Neighborhood'].unique())
        percentage_difference = ((neighborhood_record - average_neighborhood) / average_neighborhood) * 100
        total = neighborhood_record 

    else:
        average = total_neighborhood / len(df['Neighborhood'].unique())
        percentage_difference = ((total_neighborhood - average) / average) * 100
        total=total_neighborhood

    st.metric(metric_title, '{:,}'.format(total), delta=f"{percentage_difference:.2f}%", delta_color="inverse")
  
def display_crime_table(df, neighborhood_name):
    st.write("### Crime Occurrences by Offense Type")

    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]
    else:
        df = df.groupby(['OffenseType', 'Neighborhood'])['Count'].sum().reset_index()

    df = df.groupby('OffenseType')['Count'].sum().reset_index()
    df = df.sort_values(by='Count', ascending=False)
    df_top10 = df.head(10).reset_index(drop=True)
    df_top10.index += 1

    df_top10 = df_top10.rename(columns={'OffenseType': 'Offense Type'})
    df_top10 = df_top10.drop(columns=['Neighborhood'], errors='ignore')

    st.table(df_top10)

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

    # Resetting the index to make sure 'Neighborhood' is a column
    df = df.reset_index()

    for feature in choropleth.geojson.data['features']:
        neighborhood_name = feature['properties']['name']
        total = df.loc[df['Neighborhood'] == neighborhood_name, 'Count'].values[0] if neighborhood_name in df['Neighborhood'].tolist() else 0
        feature['properties']['records'] = 'Records: ' + str(total) if neighborhood_name in df['Neighborhood'].tolist() else 'N/A'

    choropleth.geojson.add_child(
        folium.features.GeoJsonTooltip(['name', 'records'], labels=False)
    )

    st_map = st_folium(map, width=800, height=500)

    neighborhood_name = ""
    if st_map['last_active_drawing']:
        neighborhood_name = st_map['last_active_drawing']['properties']['name']

    selected_neighborhood = add_sidebar_neighborhood_filter(df, neighborhood_name)
    return selected_neighborhood

    #return selected_neighborhood


def display_occurtime(df, neighborhood_name, top_offense_types):
    st.write("### Occurrence time")

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
    plt.yticks(ha='right', ticks=range(0, 24), color='white')  
    plt.xticks(rotation=45, ha='right', color='white')  
    
    st.pyplot(plt)


def display_heatmap(df):
    st.write("### Heatmap of Crime Records")

    top_neighborhoods = df.groupby('Neighborhood')['Count'].sum().nlargest(15).index.tolist()
    top_offense_types = df.groupby('OffenseType')['Count'].sum().nlargest(15).index.tolist()

    heatmap_data = df[(df['Neighborhood'].isin(top_neighborhoods)) & (df['OffenseType'].isin(top_offense_types))]
    heatmap_matrix = heatmap_data.pivot_table(values='Count', index='Neighborhood', columns='OffenseType', aggfunc=np.sum, fill_value=0)

    figure = plt.figure(figsize=(14, 10))
    figure.patch.set_alpha(0.0)

    # Create the heatmap using seaborn
    heatmap = sns.heatmap(heatmap_matrix, annot=True, cmap="YlGnBu", fmt='g')

    # Set the color of the numbers in the color bar to white
    cbar = heatmap.collections[0].colorbar
    cbar.set_ticks([0, 1000, 2000, 3000, 4000, 5000, 6000, 7000])  # Adjust the tick positions as needed
    cbar.set_ticklabels([str(label) for label in [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000]])
    cbar.ax.tick_params(axis='y', colors='white')  # Set the color of the tick labels to white

    plt.title('Heatmap of Crime Records by Neighborhood and Offense Type', color='white')
    plt.xlabel('Top 15 Offense Types', color='white')
    plt.ylabel('Top 15 Neighborhoods', color='white')
    plt.yticks(ha='right', color='white')
    plt.xticks(ha='right', color='white')
    st.pyplot(plt)

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon=":bar_chart:",layout="wide")
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    col1, col2 = st.columns([2, 1])

    df = pd.read_csv('portland-crime-data.csv', sep="\t")
    df = prepare_dataset(df)

    df['OccurTime'] = df['OccurTime'].apply(format_time)

    crime_filter=add_sidebar_crime_filter(df)
    if crime_filter:
        df = df[df['OffenseType'] == crime_filter]

    neighborhood_counts = df["Neighborhood"].value_counts().reset_index()
    neighborhood_counts.columns = ["Neighborhood", "Count"]

    offensetype_counts = df["Neighborhood"].value_counts().reset_index()
    offensetype_counts = df.groupby(['Neighborhood', 'OffenseType']).size().reset_index(name='Count')

    occur_times = df.groupby(['Neighborhood', 'OffenseType', 'OccurTime']).size().reset_index(name='Count')

    metric_title = f'Number of Reports'

    with col1:
        neighborhood_name=display_map(neighborhood_counts)
    with col2:
        top_offense_types_neighborhood = display_crime_table(offensetype_counts, neighborhood_name)
    display_statistics(offensetype_counts, neighborhood_name, metric_title)

    col3, col4 = st.columns([1, 1])
    with col3:
        display_occurtime(occur_times, neighborhood_name, top_offense_types_neighborhood)
    with col4:
        display_heatmap(offensetype_counts)
    
if __name__ == "__main__":
        main()
