import streamlit as st
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from thermofeel import calculate_wbt

#from app_preprocessing import preprocess
#from app_BEM import BEM_simulation
#from app_postprocessing import postprocess

st.set_page_config(page_title='Results', page_icon="📊")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'selected_building' not in st.session_state:
    st.session_state['selected_building'] = None

if 'building_folders' not in st.session_state:
        st.session_state['building_folders'] = []

result_types = ['Thermal comfort during hottest weeks', 'Distribution of differences to baseline file', 'Survivability during hottest weeks']
comparison_types = ['Degree and Exceedance hours', 'Peak Humidex values']

metrics = ['Temperature', 'Humidex', 'SET', 'PMV', 'WBGT']
metrics_thresholds = [30, 35, 30, 1.5, 23]

def main():
    st.markdown("# Results")
    #st.sidebar.header("Results")
    st.write("""Please choose the building, result type and building zone of interest.""")

    building_options = st.session_state.building_folders + ['Comparisons across buildings']

    if st.session_state.current_page == 'results':
        option = st.sidebar.selectbox("Choose building", building_options)
        if option == 'Comparisons across buildings':
            building_comparison_page(option)
        else:
            building_details_page(option)
    else:
        st.error('Please run simulation first')


def building_comparison_page(option):
    st.write("### " + option)

    comparison_type = st.sidebar.selectbox("Choose comparison type", comparison_types)

    if comparison_type == 'Degree and Exceedance hours':
        dh_eh_comparison()
    elif comparison_type == 'Peak Humidex values':
        peak_humidex_comparison()

def building_details_page(building):
    st.write("### " + building)
    result_type = st.sidebar.selectbox("Choose result type", result_types)

    if result_type == 'Thermal comfort during hottest weeks':
        hottest_weeks_plot(building)
    elif result_type == 'Distribution of differences to baseline file':
        summer_diff_distr_plot(building)
    elif  result_type == 'Survivability during hottest weeks':
        hottest_weeks_surviability(building)
    else:
        st.write("To be added...")


def peak_humidex_comparison():

    max_hum_file_path = 'data/max_hum_data.h5'
    weather_folders = st.session_state.weather_folders
    building_folders = st.session_state.building_folders
    all_zones = np.unique([value for values in st.session_state.zones.values() for value in values])

    selected_buildings = st.multiselect("Select buildings to display:", building_folders, default=building_folders)
    selected_weather_files = st.multiselect("Select weather files to display:", weather_folders, default=weather_folders)
    selected_zones = st.multiselect("Select zones to display:", all_zones, default=all_zones)

    fig = go.Figure()

    colors = ['green', 'orange', 'red', 'purple', 'royalblue']
    symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'triangle-down', 'hexagon', 'octagon','star']

    pastel_colorscale = [
        (0, 'rgba(173, 216, 230, 0.4)'),  # Light Blue
        (0.05, 'rgba(144, 238, 144, 0.4)'),  # Light Green
        (0.5, 'rgba(255, 255, 0, 0.4)'),  # Light Yellow
        (0.95, 'rgba(255, 165, 0, 0.4)'),  # Orange
        (1, 'rgba(255, 99, 71, 0.4)')  # Red
    ]

    temperature = np.linspace(25, 45, 200)  # Temperature range
    humidity = np.linspace(0, 100, 200)

    temp_grid, humid_grid = np.meshgrid(temperature, humidity)
    humidex_grid = calculate_humidex(temp_grid, humid_grid)
    fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, colorscale=pastel_colorscale, showscale=False,
                             contours=dict(start=29, end=54, size=1, coloring='heatmap'),
                             line=dict(color='black', width=0)))
    # colorbar=dict(tickvals=[29,39,45,54], ticktext=['low', 'med', 'high', 'extreme'], len=.8)))

    fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                             contours=dict(type='constraint', operation='=', value=29),
                             line=dict(color='grey', width=2), showlegend=False))

    fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                             contours=dict(type='constraint', operation='=', value=39),
                             line=dict(color='grey', width=2), showlegend=False))

    fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                             contours=dict(type='constraint', operation='=', value=45),
                             line=dict(color='grey', width=2), showlegend=False))

    fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                             contours=dict(type='constraint', operation='=', value=54),
                             line=dict(color='grey', width=2), showlegend=False))

    for k, weather_folder in enumerate(weather_folders):

        if weather_folder not in selected_weather_files:
            continue

        for i, building in enumerate(st.session_state.building_folders):
            symbol = symbols[i]

            if building not in selected_buildings:
                continue

            for zone in st.session_state.zones[building]:

                if zone not in selected_zones:
                    continue

                (max_humidex, max_hum_temp, max_hum_rh) = read_data_for_display(max_hum_file_path, building, weather_folder, 'Humidex', zone)

                fig.add_trace(
                    go.Scatter(x=[max_hum_temp], y=[max_hum_rh], name=zone, marker_color=colors[k], marker_symbol=symbol,
                               marker=dict(size=12, line=dict(width=2, color=colors[k])), mode="markers+text",
                               textposition="top center", textfont=dict(color=colors[k]), showlegend=False))

        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=weather_folder,
                                 legendgrouptitle_text="Weather scenario", legendgroup='group1',
                                 marker=dict(size=7, color=colors[k], symbol='square',
                                             line=dict(width=2, color=colors[k]))))

    for i, building in enumerate(st.session_state.building_folders):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=building,
                                 legendgrouptitle_text="Buildings", legendgroup='group2',
                                 marker=dict(size=7, color='black', symbol=symbols[i],
                                             line=dict(width=2, color='black'))))

    fig.update_layout(title="Comparison of peak Humidex values",
        xaxis_title="Temperature (\N{DEGREE SIGN}C)",
        yaxis_title="Humidity (%)",template='simple_white', width=1200, height=900)
    fig.update_xaxes(gridcolor='lightgrey', showgrid=True, range=[25, 45],
                     title='Dry Bulb Temperature (\N{DEGREE SIGN}C)')
    fig.update_yaxes(gridcolor='lightgrey', showgrid=True, range=[0, 100], title='Relative Humidity (%)')

    color_scale_labels = ['<29: No discomfort', '30-39: Some discomfort', '40-45: Great discomfort; avoid exertion',
                          '45-54: Dangerous', '>54: Heat stroke imminent']

    for i, (_, color) in enumerate(pastel_colorscale):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=color_scale_labels[i],
                                 legendgrouptitle_text="Humidex range", legendgroup='group4',
                                 marker=dict(size=12, color=color, symbol='square')))

    st.plotly_chart(fig)

def dh_eh_comparison():

    tc_model = st.radio("Select Thermal Comfort Model", ["Humidex", "SET"])
    time_period = st.radio("Select Time Period", ["Annual", "Maximum Week"])
    metric_type = st.radio("Select Metric Type", ["Degree hours", "Exceedance hours"])

    dh_eh_file_path = "data/dh_eh_data.h5"

    # Function call to create the table based on selections
    fig = create_dh_eh_table(dh_eh_file_path, tc_model, time_period, metric_type)

    st.plotly_chart(fig)

def hottest_weeks_surviability(building):

    # Extract survivability line
    file_path_elderly = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Survivability/rh_version_NewSurvivability_limits_Night-Indoors_6H-65_over.csv'
    file_path_young = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Survivability/rh_version_NewSurvivability_limits_Night-Indoors_6H-Young_adult.csv'
    survivability_elderly = pd.read_csv(file_path_elderly)
    survivability_young = pd.read_csv(file_path_young)

    temperature = np.linspace(20, 60, 200)  # Temperature range
    humidity = np.linspace(0, 100, 200)

    temp_grid, humid_grid = np.meshgrid(temperature, humidity)
    K = 273.15
    wbt_grid = calculate_wbt(temp_grid + K, humid_grid) - K
    humidex_grid = calculate_humidex(temp_grid, humid_grid)

    weather_files = st.session_state.weather_folders
    zones = st.session_state.zones[building]
    zone = st.sidebar.selectbox("Choose zone", zones)

    hottest_file_path = 'data/hottest_weeks_data.h5'

    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    pastel_colorscale = [
        (0, 'rgba(173, 216, 230, 0.4)'),  # Light Blue
        (0.05, 'rgba(144, 238, 144, 0.4)'),  # Light Green
        (0.5, 'rgba(255, 255, 0, 0.4)'),  # Light Yellow
        (0.95, 'rgba(255, 165, 0, 0.4)'),  # Orange
        (1, 'rgba(255, 99, 71, 0.4)')  # Red
    ]

    ##Allow users to select weather files to display WBT/survivability/Humidex lines
    # User selection for weather files
    selected_weather_files = st.multiselect("Select weather files to display:", weather_files, default=weather_files)

    # Checkboxes for WBT and survivability lines
    st.markdown("""Select survivability limits/ranges to display:""")
    show_survivability_young= st.checkbox("Show survivability limit line for young (18-40)", True)
    show_survivability_elderly= st.checkbox("Show survivability limit line for elderly (over 65)", True)
    show_wbt_line = st.checkbox("Show WBT of 35°C line", True)
    show_humidex_range = st.checkbox("Show Humidex ranges", True)


    # Plotting
    fig = go.Figure()

    # Add traces for relative humidity and dry bulb air temperature

    if show_survivability_young:
        fig.add_trace(
            go.Scatter(x=survivability_young['Tair'], y=survivability_young['rh'], mode='lines', name='Updated for young (18-40)',
                       legendgrouptitle_text="Survivability limit", legendgroup='group1',
                       showlegend=True, line=dict(color='purple', width=2)))

    if show_survivability_elderly:
        fig.add_trace(
            go.Scatter(x=survivability_elderly['Tair'], y=survivability_elderly['rh'], mode='lines', name='Updated for elderly (over 65)',
                       legendgrouptitle_text="Survivability limit", legendgroup='group1',
                       showlegend=True, line=dict(color='darkred', width=2)))

    # Add trace for WBT line
    if show_wbt_line:
        fig.add_trace(
            go.Contour(x=temperature, y=humidity, z=wbt_grid, name='WBT of 35\N{DEGREE SIGN}C', showscale=False,
                       legendgrouptitle_text="Survivability limit", legendgroup='group1',
                       contours=dict(type='constraint', value=35, operation='='), line=dict(color='black', width=2)))

    if show_humidex_range:
        fig.add_trace(
            go.Contour(x=temperature, y=humidity, z=humidex_grid, colorscale=pastel_colorscale, showscale=False,
                       contours=dict(start=29, end=54, size=1, coloring='heatmap'), line=dict(color='black', width=0)))

        fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                                 contours=dict(type='constraint', operation='=', value=29),
                                 line=dict(color='grey', width=2), showlegend=False))

        fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                                 contours=dict(type='constraint', operation='=', value=39),
                                 line=dict(color='grey', width=2), showlegend=False))

        fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                                 contours=dict(type='constraint', operation='=', value=45),
                                 line=dict(color='grey', width=2), showlegend=False))

        fig.add_trace(go.Contour(x=temperature, y=humidity, z=humidex_grid, showscale=False,
                                 contours=dict(type='constraint', operation='=', value=54),
                                 line=dict(color='grey', width=2), showlegend=False))

        color_scale_labels = ['<29: No discomfort', '30-39: Some discomfort', '40-45: Great discomfort; avoid exertion',
                              '45-54: Dangerous', '>54: Heat stroke imminent']

        for i, (_, color) in enumerate(pastel_colorscale):
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=color_scale_labels[i],
                                     legendgrouptitle_text="Humidex range", legendgroup='group2',
                                     marker=dict(size=12, color=color, symbol='square')))

    for k, weather in enumerate(weather_files):
        if weather not in selected_weather_files:
            continue

        #we only use the values for the hottest week
        temp = read_data_for_display(hottest_file_path, building, weather, 'Temperature', zone)[7*24:2*7*24]
        rh = read_data_for_display(hottest_file_path, building, weather, 'Relative Humidity', zone)[7*24:2*7*24]

        fig.add_trace(go.Scatter(x=temp, y=rh, mode='markers+text', name=weather,showlegend=False, textposition='top center', marker=dict(color=colors[k], size=5)))

    for k in range(len(weather_files)):
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(color=colors[k], symbol='circle', size=8),
            showlegend=True,
            legend='legend2',
            name=weather_files[k]
        ))

    # Set plot titles and labels
    fig.update_layout(title=zone +': Survivability over hottest weeks',
                      xaxis_title='Dry Bulb Air Temperature (°C)',
                      yaxis_title='Relative Humidity (%)', template='simple_white',
                      legend2=dict(yanchor="top", xanchor="center", y=-0.12, x=0.5, orientation='h',
                                   title='Weather scenarios:'),
                      width=1200, height=900)

    fig.update_xaxes(range=[20, 50])
    fig.update_yaxes(range=[0, 100])

    st.plotly_chart(fig)


def summer_diff_distr_plot(building):

    zones = st.session_state.zones[building]
    zone = st.sidebar.selectbox("Choose zone", zones)
    summer_diff_file_path = 'data/summer_differences_data.h5'
    weather_files = st.session_state.weather_folders

    colors = ['orange', 'red', 'purple', 'royalblue']

    nr_rows = len(metrics)
    fig = make_subplots(rows=nr_rows, cols=1, shared_xaxes=True, vertical_spacing=0.05)

    for i, metric in enumerate(metrics):
        j = 0
        for weather in weather_files:

            if weather == st.session_state.baseline_file:
                continue

            y_values = read_data_for_display(summer_diff_file_path, building, weather, metric, zone)
            x_values = [zone] * len(y_values)

            fig.add_trace(go.Violin(x=x_values, y=y_values, box_visible=False, name=weather + ' - Baseline', line_color=colors[j], showlegend=False, offsetgroup=j), row=i + 1, col=1)

            j+=1

    fig.update_traces(meanline_visible=True)

    for i, metric in enumerate(metrics):
        yaxis_nr = 'yaxis' + str(i + 1)
        fig['layout'][yaxis_nr].update(title=metrics[i])

    fig.update_layout(template='simple_white', width=1000, height=700, violinmode='group',
                      title=zone + ': Differences in Summer Distribution to Baseline')
    fig.update_xaxes(linecolor='lightgrey', showticklabels=False, ticks="")
    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="black", opacity=1)
    fig.update_yaxes(secondary_y=False, gridcolor='lightgrey', showgrid=True)

    # Add a legend for the weather scenarios
    i=0
    for weather_file in weather_files:
        if weather_file == st.session_state.baseline_file:
            continue

        line_dash = 'solid'
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            line_dash=line_dash,
            mode="markers",
            legend='legend2',
            marker=dict(symbol="square", color=colors[i], size=13),
            name=weather_file + ' - Baseline',
            line=dict(color=colors[i])))

        i+=1

    fig.update_layout(
        legend2=dict(yanchor="top", xanchor="center", y=-0.12, x=0.5, orientation='h', title='Weather scenarios:'))

    st.plotly_chart(fig)

def summer_distribution_plot(building):

    weather_files = st.session_state.weather_folders
    zones = st.session_state.zones[building]
    zone = st.sidebar.selectbox("Choose zone", zones)

    summer_months = [6,7,8]

    annual_file_path = 'data/annual_data.h5'

    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for i, weather in enumerate(weather_files):
        x_array = []
        y_array = []

        for metric in metrics:
            y_values = read_data_for_display(annual_file_path, building, weather, metric, zone)
            if metric == "PMV":
                y_values += 25
            x_array.extend([metric] * len(y_values))
            y_array.extend(y_values)

        fig.add_trace(go.Violin(x=x_array, y=y_array, box_visible=False, name=weather, line_color=colors[i], showlegend=False))


    fig.add_trace(go.Violin(x=[None], y=[None], name="Dummy Data", showlegend=False), secondary_y=True)

    fig.update_traces(meanline_visible=True)
    # Adjust Layout and save
    fig.update_layout(template='simple_white', width=1200, height=600, violinmode='group',title=zone +': Distribution of hourly summer thermal comfort model values')
    fig.update_xaxes(title='Thermal Comfort Model')
    fig.update_yaxes(title='Temperature, SET, WBGT (\N{DEGREE SIGN}C) and Humidex', secondary_y=False, range=[10, 50],
                     gridcolor='lightgrey', showgrid=True)
    fig.update_yaxes(title='PMV', secondary_y=True, overlaying='y', side='right', range=[-15, 25])

    # Add a legend for the weather scenarios
    for i, weather_file in enumerate(weather_files):
        line_dash = 'solid'
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            line_dash=line_dash,
            mode="markers",
            legend='legend2',
            marker=dict(symbol="square", color=colors[i], size=13),
            name=weather_file,
            line=dict(color=colors[i])))

    fig.update_layout(
        legend2=dict(yanchor="top", xanchor="center", y=-0.18, x=0.5, orientation='h', title='Weather scenarios:'))

    st.plotly_chart(fig)


def hottest_weeks_plot(building):

    weather_files = st.session_state.weather_folders
    zones = st.session_state.zones[building]
    zone = st.sidebar.selectbox("Choose zone", zones)

    hottest_file_path = 'data/hottest_weeks_data.h5'

    x_values = np.arange(1, 21 * 24 + 1)
    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    rows = len(metrics)
    cols = 1

    row_titles = metrics

    fig = make_subplots(rows=rows, cols=cols, shared_xaxes=True, vertical_spacing=0.05)

    for k, metric in enumerate(metrics):
        for i, weather in enumerate(weather_files):

            data = read_data_for_display(hottest_file_path, building, weather, metric, zone)

            fig.add_trace(go.Scatter(x=x_values, y=data, xaxis="x1", line_dash='solid', name=weather,line=dict(color=colors[i]), showlegend=False), row=k + 1, col=1)

        fig.add_hline(y=metrics_thresholds[k], row=k + 1, col=1, line_width=1.5, line_dash="dash", line_color='black',opacity=1)

    # to update x-axis
    x_values = x_values[::24]

    # to update x-axis
    ticktext = 21 * ['']
    ticktext[3] = '     Hottest Week - 1'
    ticktext[10] = '      Hottest Week'
    ticktext[17] = '      Hottest Week + 1'

    fig.update_xaxes(tickvals=x_values, ticktext=ticktext)

    fig.update_layout(
        title=zone + ': Thermal comfort during hottest summer weeks for different weather scenarios and thermal comfort models',
        width=1500, height=900, template='simple_white')

    fig.update_yaxes(gridcolor='lightgrey', showgrid=True)

    for k, metric in enumerate(metrics):
        yaxis_nr = 'yaxis' + str(k + 1)

        #tc_range = tc_ranges[tc_model]
        fig['layout'][yaxis_nr].update(title=row_titles[k])#, range=tc_range)


    fig.add_vline(x=7 * 24, line_width=1, line_color='black', opacity=1)
    fig.add_vline(x=14 * 24, line_width=1, line_color='black', opacity=1)

    # Add a legend for the weather scenarios
    for i, weather_file in enumerate(weather_files):
        line_dash = 'solid'
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            line_dash=line_dash,
            mode="lines",
            legend='legend2',
            name=weather_file,
            line=dict(color=colors[i])))

    fig.update_layout(
        legend2=dict(yanchor="top", xanchor="center", y=-0.08, x=0.5, orientation='h', title='Weather scenarios:'))

    st.plotly_chart(fig)


# Example of reading data for a specific building, weather file, and zone
def read_data_for_display(hdf5_file_path, building_folder, weather, metric, zone):
    hdf_key = f'{building_folder}/{zone}/{weather}/{metric}'
    arr = pd.read_hdf(hdf5_file_path, key=hdf_key).to_numpy()
    return np.concatenate(arr)


def calculate_humidex(temperature, humidity):
    # Constants for the humidex calculation
    # You can adjust this formula based on the specific humidex calculation you're using
    e = 6.112 * np.exp(17.67 * temperature / (temperature + 243.5)) * humidity / 100
    humidex = temperature + (5/9) * (e - 10)
    return humidex

def create_dh_eh_table(dh_eh_file_path, tc_model, time_period, metric_type):
    # metric_type: 'dh' or 'eh'
    # time_period: 'annual' or 'max'

    # Reading data from HDF and creating a table
    all_data = []
    buildings = st.session_state.building_folders
    all_zones = np.unique([value for values in st.session_state.zones.values() for value in values])

    # Filter by Building
    selected_buildings = st.multiselect('Select Buildings:', buildings, default=buildings)
    selected_zones = st.multiselect('Select Zones:', all_zones, default=all_zones)

    if selected_buildings == [] or selected_zones==[]:
        st.error('Please choose at least one building and zone.')
        return go.Figure(go.Table())

    idx = 0
    if time_period == 'Annual' and metric_type == "Exceedance hours":
        idx = 1
    elif time_period == "Maximum Week" and metric_type == "Degree hours":
        idx = 2
    elif time_period == "Maximum Week" and metric_type == "Exceedance hours":
        idx = 3

    with pd.HDFStore(dh_eh_file_path, 'r') as store:

        for building_key in store.keys():
            building_key = building_key.lstrip('/')
            building_data = store[building_key]
            building_folder, zone, weather, metric = building_key.split('/')
            if building_folder not in selected_buildings:
                continue
            if zone not in selected_zones:
                continue
            if metric == tc_model:
                data = {
                    'Building': building_folder,
                    'Zone': zone,
                    'Weather': weather,
                    metric_type: building_data[idx]
                }
                all_data.append(data)

    # Creating a DataFrame for the table
    df = pd.DataFrame(all_data)
    ##
    # Pivoting the DataFrame
    pivot_df = df.pivot_table(index=['Building', 'Zone'], columns='Weather', values=metric_type)
    pivot_df = pivot_df.reset_index()

    # Header with weather files
    header_values = list(pivot_df.columns)
    header_values[0] = "<b>Building</b>"  # Bold for Building
    header_values[1] = "<b>Zone</b>"  # Bold for Zone

    # Cells with values
    cell_values = [pivot_df[col] for col in pivot_df.columns]

    # Create Plotly Table
    fig = go.Figure(data=[go.Table(
        header=dict(values=header_values, align='left', font=dict(color='black', size=12)),
        cells=dict(values=cell_values, align='left', font=dict(color='darkblue', size=11))
    )])
    fig.update_layout(width=800, height=600, title='Comparison of Degree and Exceedance hours')


    return fig

if __name__ == "__main__":
    main()