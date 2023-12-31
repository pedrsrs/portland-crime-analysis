import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import altair as alt

session_state = st.session_state
APP_TITLE =  'Portland Crime Analysis'
APP_SUBTITLE = 'Source: Portland Police Department'
st.set_page_config(page_title=APP_TITLE, page_icon=":bar_chart:", layout="wide")

with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

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
    unique_neighborhoods.insert(0, "All")  
    default_value = selected_map if selected_map else unique_neighborhoods[0]
    neighborhood_filter = st.sidebar.selectbox("Neighborhood", unique_neighborhoods, index=unique_neighborhoods.index(default_value))
    if neighborhood_filter == "All":
        neighborhood_filter = ""
    return neighborhood_filter

def add_sidebar_crime_filter(df):
    unique_offense_types = df['OffenseType'].unique().tolist()
    unique_offense_types.insert(0, "All") 
    default_value = unique_offense_types[0]
    crime_filter = st.sidebar.selectbox("Offense Types", unique_offense_types, index=unique_offense_types.index(default_value))
    if crime_filter == "All":
        crime_filter = ""
    return crime_filter

def add_sidebar_crime_against_filter(df):
    unique_crime_against = df['CrimeAgainst'].unique().tolist()
    default_values = unique_crime_against.copy()
    crime_against_filter = st.sidebar.multiselect("Crime Against", unique_crime_against, default_values)
    return crime_against_filter

def display_record_number(df, neighborhood_name):
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

    st.metric('Number of Reports', '{:,}'.format(total), delta=f"{percentage_difference:.2f}%", delta_color="inverse")

def get_neighborhood_rank(df, neighborhood_name):
    neighborhood_ranking = df.groupby('Neighborhood')['Count'].sum().sort_values(ascending=False).reset_index()
    neighborhood_rank = neighborhood_ranking.index[neighborhood_ranking['Neighborhood'] == neighborhood_name].tolist()

    if neighborhood_rank:
        return neighborhood_rank[0] + 1 
    else:
        return None

def occurences_per_day(df, neighborhood_name):
    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]
    else:
        df = df.groupby(['OffenseType', 'Neighborhood'])['Count'].sum().reset_index()
    
    df = df.groupby('OffenseType')['Count'].sum().reset_index()
    total_crime_count = df['Count'].sum()
    average_per_day = total_crime_count/3204
    st.metric('Average Occurences per Day', f"{average_per_day:.2f}")
    
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
        geo_data='./data/portland.geojson',
        data=df,
        columns=("Neighborhood", "Count"),
        key_on='feature.properties.name',
        line_opacity=0.8,
        highlight=True
    )
    choropleth.geojson.add_to(map)

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

import altair as alt

def months_ranking(df, neighborhood_name):
    st.markdown("<h3>Months With the Highest Number of Records</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]
    try:
        df['OccurDate'] = pd.to_datetime(df['OccurDate'], errors='coerce')
    except ValueError as e:
        st.error(f"Error: {e}")

    df = df.dropna(subset=['OccurDate'])
    df['Month'] = df['OccurDate'].dt.month_name()

    monthly_counts = df['Month'].value_counts().sort_values(ascending=False)
    sorted_months = monthly_counts.sort_values(ascending=False)

    top_8_months = sorted_months.head(12)

    chart = alt.Chart(top_8_months.reset_index(name='Count')).mark_bar().encode(
        x=alt.X('Count:Q', title='Number of Occurrences'),
        y=alt.Y('Month:N', title='Month', sort='-x')
    ).properties(
        width=550,
        height=600
    )
    st.altair_chart(chart)

def display_occurtime(df, neighborhood_name, top_offense_types):
    st.markdown("<h3>Crime Occurence Times</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if neighborhood_name:
        df = df[df['Neighborhood'] == neighborhood_name]

    df['OccurHour'] = pd.to_datetime(df['OccurTime']).dt.hour

    df_top_offenses = df[df['OffenseType'].isin(top_offense_types[:5])]

    df_grouped = df_top_offenses.groupby(['OccurHour', 'OffenseType']).size().reset_index(name='Count')

    figure = plt.figure(figsize=(12, 8))
    figure.patch.set_alpha(0.0)
    sns.set(style="whitegrid") 

    sns.lineplot(x='OccurHour', y='Count', hue='OffenseType', data=df_grouped, linewidth=2)

    plt.xlabel('Hour of Occurrence', color='white')
    plt.ylabel('Number of Occurrences', color='white')
    plt.title('Crime Occurrence time for Top 5 Offense Types')
    plt.yticks(ha='right', color='white')
    plt.xticks(np.arange(0, 24, 1), ha='right', color='white')

    legend = plt.legend(title='Offense Type')
    legend.get_title().set_color('white')

    st.pyplot(plt)

def display_heatmap(df):
    st.markdown("<h3>Heatmap of Crime Records</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    top_neighborhoods = df.groupby('Neighborhood')['Count'].sum().nlargest(15).index.tolist()
    top_offense_types = df.groupby('OffenseType')['Count'].sum().nlargest(20).index.tolist()

    heatmap_data = df[(df['Neighborhood'].isin(top_neighborhoods)) & (df['OffenseType'].isin(top_offense_types))]
    heatmap_matrix = heatmap_data.pivot_table(values='Count', index='Neighborhood', columns='OffenseType', aggfunc=np.sum, fill_value=0)

    figure = plt.figure(figsize=(18, 12))
    figure.patch.set_alpha(0.0)

    heatmap = sns.heatmap(heatmap_matrix, annot=True, cmap="YlGnBu", fmt='g')

    cbar = heatmap.collections[0].colorbar
    cbar.set_ticks([0, 1000, 2000, 3000, 4000, 5000, 6000, 7000])  
    cbar.set_ticklabels([str(label) for label in [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000]])
    cbar.ax.tick_params(axis='y', colors='white')  #

    plt.title('Heatmap of Crime Records by Neighborhood and Offense Type', color='white')
    plt.xlabel('Top 20 Offense Types', color='white')
    plt.ylabel('Top 15 Neighborhoods', color='white')
    plt.yticks(ha='right', color='white')
    plt.xticks(ha='right', color='white')
    st.pyplot(plt)

def main():
    st.title("Portland Crime Data Analysis")
    st.write("Analysis of Portland's public crime data from 2015 to 2023, available on the City of Portland website.", color="gray")
    st.markdown("---")

    df = pd.read_csv('./data/portland-crime-data.csv', sep="\t")
    df = prepare_dataset(df)

    st.sidebar.header("Filters")
    st.sidebar.markdown("---")
    crime_filter=add_sidebar_crime_filter(df)
    if crime_filter:
        df = df[df['OffenseType'] == crime_filter]
    crime_against_filter = add_sidebar_crime_against_filter(df)
    if crime_against_filter:
        df = df[df['CrimeAgainst'].isin(crime_against_filter)]

    neighborhood_counts = df["Neighborhood"].value_counts().reset_index()
    neighborhood_counts.columns = ["Neighborhood", "Count"]

    df['OccurTime'] = df['OccurTime'].apply(format_time)

    col1, col2 = st.columns([3, 2])

    with col1:
        neighborhood_name=display_map(neighborhood_counts)

    offensetype_counts = df["Neighborhood"].value_counts().reset_index()
    offensetype_counts = df.groupby(['Neighborhood', 'OffenseType']).size().reset_index(name='Count')

    occur_times = df.groupby(['Neighborhood', 'OffenseType', 'OccurTime']).size().reset_index(name='Count')
    
    with col2:
        top_offense_types_neighborhood = display_crime_table(offensetype_counts, neighborhood_name)
    
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        neighborhood_rank = get_neighborhood_rank(offensetype_counts, neighborhood_name)
        if neighborhood_rank is not None:
            st.metric('Neighborhood Ranking by Crime Records', f"{neighborhood_rank}/{len(offensetype_counts['Neighborhood'].unique())}")
        else:
            st.metric('Neighborhood Ranking by Crime Records', "Select a Neighborhood")

    with col2:
        display_record_number(offensetype_counts, neighborhood_name)

    with col3: 
        occurences_per_day(offensetype_counts, neighborhood_name)
        
    st.sidebar.markdown("----")
    st.sidebar.header("Linechart Offense Types")
    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    selected_offense_types = st.sidebar.multiselect("Select up to 5 Offense Types", df['OffenseType'].unique())
    st.sidebar.markdown("----")

    st.markdown("----")

    col1, col2= st.columns([3, 4])
    with col1:
        months_ranking(df, neighborhood_name)
    with col2:
        if selected_offense_types:
            df_filtered = df[df['OffenseType'].isin(selected_offense_types)]
            display_occurtime(df_filtered, neighborhood_name, selected_offense_types)
        else:
            display_occurtime(occur_times, neighborhood_name, top_offense_types_neighborhood)
    st.markdown("----")

    col1, col2, col3 = st.columns([1, 5, 1])
    with col2:
        display_heatmap(offensetype_counts)


    st.sidebar.markdown("<a class='contact' href='https://github.com/pedrsrs'>Developed by Pedro Soares</a>", unsafe_allow_html=True)

if __name__ == "__main__":
        main()
