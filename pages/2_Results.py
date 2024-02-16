import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from thermofeel import calculate_wbt
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import plotly.express as px

st.set_page_config(page_title='Results')

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'selected_building' not in st.session_state:
    st.session_state['selected_building'] = None

if 'building_names' not in st.session_state:
        st.session_state['building_names'] = []

if 'metrics_thresholds' not in st.session_state:
    st.session_state.metrics_thresholds = {'Humidex': 35, 'SET': 30, 'Temperature': 30, 'PMV': 1.5, 'WBGT': 23}

result_types = ['Thermal comfort during hottest weeks', 'Summer distribution shifts', 'Survivability and liveability during hottest week']

comparison_types = ['Degree and Exceedance hours', 'Peak Humidex values']

metrics = ['Temperature', 'Humidex', 'SET', 'PMV', 'WBGT']

def main():
    st.markdown("# Results")

    building_options = st.session_state.building_names + ['Comparisons across buildings']

    if st.session_state.current_page == 'results':
        option = st.sidebar.selectbox("Choose building", building_options)
        if option == 'Comparisons across buildings':
            building_comparison_page(option)
        else:
            building_details_page(option)
    else:
        st.error('Please run simulation first')


def building_comparison_page(option):

    comparison_type = st.sidebar.selectbox("Choose comparison type", comparison_types)
    st.write("### " + option)
    st.write("##### " + comparison_type)

    if comparison_type == 'Degree and Exceedance hours':
        dh_eh_comparison()
    elif comparison_type == 'Peak Humidex values':
        peak_humidex_comparison()

def building_details_page(building):
    result_type = st.sidebar.selectbox("Choose result type", result_types)

    st.write("### " + building)
    st.write("##### " + result_type)

    if result_type == 'Thermal comfort during hottest weeks':
        hottest_weeks_plot(building)
    elif result_type == 'Summer distribution shifts':
        summer_diff_distr_plot(building)
    elif  result_type == 'Survivability and liveability during hottest week':
        hottest_week_survivability(building)

def peak_humidex_comparison():

    max_hum_file_path = 'Output/data/max_hum_data.h5'
    weather_folders = st.session_state.weather_folders
    building_names = st.session_state.building_names
    all_zones = np.unique([value for values in st.session_state.zones.values() for value in values])

    selected_buildings = st.multiselect("Select buildings to display:", building_names, default=building_names)
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

        for i, building in enumerate(st.session_state.building_names):

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

    for i, building in enumerate(st.session_state.building_names):

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

#Visualize Degree and Exceedance Hours for Temperature, Humidex and SET with options for annual or maximum value over one week
def dh_eh_comparison():

    tc_model = st.radio("Select thermal comfort model", ["Humidex", "SET", "Temperature"])
    time_period = st.radio("Select time period", ["Annual", "Maximum Week"])
    metric_type = st.radio("Select metric type", ["Degree hours", "Exceedance hours"])

    dh_eh_file_path = "Output/data/dh_eh_data.h5"

    # Function call to create the table based on selections
    create_dh_eh_table(dh_eh_file_path, tc_model, time_period, metric_type)

#Visualize liveability and survivability over the hottest summer week
def hottest_week_survivability(building):

    #Extract survivability line
    surv_path_elderly = 'pages/survivability_data/rh_version_NewSurvivability_limits_Night-Indoors_3H-65_over.csv'
    surv_path_young = 'pages/survivability_data/rh_version_NewSurvivability_limits_Night-Indoors_3H-Young_adult.csv'
    survivability_elderly = pd.read_csv(surv_path_elderly)
    survivability_young = pd.read_csv(surv_path_young)

    #Extract liveability line
    liv_path_elderly = 'pages/survivability_data/rh_version_Liveability_limits_Night-Indoors_3H-65_over.csv'
    liv_path_young = 'pages/survivability_data/rh_version_Liveability_limits_Night-Indoors_3H-Young_adult.csv'
    liv_elderly = pd.read_csv(liv_path_elderly)
    liv_young = pd.read_csv(liv_path_young)

    #Extract liveability ranges
    mmax_path_elderly = 'pages/survivability_data/rh_Mmax_Livability_Night-Indoors_3H-65_over.csv'
    mmax_path_young = 'pages/survivability_data/rh_Mmax_Livability_Night-Indoors_3H-Young_adult.csv'

    #Extract survivable but not liveable region
    surv_not_liv_path_elderly = 'pages/survivability_data/rh_survive_but_not_livable_survivability_Night-Indoors_3H-65_over.csv'
    surv_not_liv_path_young = 'pages/survivability_data/rh_survive_but_not_livable_survivability_Night-Indoors_3H-Young_adult.csv'

    #Extract not survivable region
    not_surv_path_elderly = 'pages/survivability_data/rh_survivability_array_Night-Indoors_3H-65_over.csv'
    not_surv_path_young = 'pages/survivability_data/rh_survivability_array_Night-Indoors_3H-Young_adult.csv'

    #Temperature and relative humidity ranges
    temperature = np.arange(25, 60, 0.1)
    humidity = np.arange(0.5, 100.5, 0.5)

    #Calculate WBT and Humidex grid
    temp_grid, humid_grid = np.meshgrid(temperature, humidity)
    K = 273.15
    wbt_grid = calculate_wbt(temp_grid + K, humid_grid) - K
    humidex_grid = calculate_humidex(temp_grid, humid_grid)

    weather_files = st.session_state.weather_folders

    zones = st.session_state.zones[building]
    zone = st.sidebar.selectbox("Choose zone", zones)

    hottest_file_path = 'Output/data/hottest_weeks_data.h5'

    #Colors for plotting the hourly values of the different scenarios
    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    #Colorscale for Humidex ranges
    pastel_colorscale = [
        (0, 'rgba(173, 216, 230, 0.4)'),  # Light Blue
        (0.05, 'rgba(144, 238, 144, 0.4)'),  # Light Green
        (0.5, 'rgba(255, 255, 0, 0.4)'),  # Light Yellow
        (0.95, 'rgba(255, 165, 0, 0.4)'),  # Orange
        (1, 'rgba(255, 99, 71, 0.4)')  # Red
    ]

    ##Allow users to select weather files to display WBT, Survivability and Liveability, or Humidex lines

    #User selection for weather files
    selected_weather_files = st.multiselect("Select weather files to display:", weather_files, default=weather_files)

    #Checkboxes for WBT and survivability lines
    st.markdown("""Select survivability limits to display:""")
    show_survivability_young= st.checkbox("Survivability limit for young (18-40)", True)
    show_survivability_elderly= st.checkbox("Survivability limit for elderly (over 65)", False)
    show_wbt_line = st.checkbox("WBT of 35°C line", False)

    #Selection for liveability ranges to show. Only one of these ranges can be shown at a time.
    selected_option = st.radio("Select liveability ranges to display:", ["Liveability ranges for young (18-40)",
                                                     "Liveability ranges for elderly (over 65)", "Humidex ranges"], index=0)

    show_humidex_range = show_liv_elderly = show_liv_young = False
    if selected_option == "Humidex ranges":
        show_humidex_range = True
    elif selected_option == "Liveability ranges for young (18-40)":
        show_liv_young = True
    elif selected_option == "Liveability ranges for elderly (over 65)":
        show_liv_elderly = True

    #Extract the liveability ranges for the selected option
    if show_liv_young:
        liv = liv_young
        title_ending = 'Young (18-40)'
        surv_not_liv_path = surv_not_liv_path_young
        Mmax_MET = pd.read_csv(mmax_path_young, index_col=0)
        not_surv = pd.read_csv(not_surv_path_young, index_col=0)
        not_surv = not_surv.map(lambda x: None if x else 1)

    if show_liv_elderly:
        liv = liv_elderly
        title_ending = 'Elderly (over 65)'
        surv_not_liv_path = surv_not_liv_path_elderly
        Mmax_MET = pd.read_csv(mmax_path_elderly, index_col=0)
        Mmax_MET.iloc[185:, 50:] = np.nan
        not_surv = pd.read_csv(not_surv_path_elderly, index_col=0)
        not_surv = not_surv.map(lambda x: None if x else 1)

    # Plotting
    fig = go.Figure()

    #Add trace for WBT 35 line
    if show_wbt_line:
        fig.add_trace(
            go.Contour(x=temperature, y=humidity, z=wbt_grid, name='WBT of 35\N{DEGREE SIGN}C', showscale=False,
                       legendgrouptitle_text="Survivability limit", legendgroup='group1',
                       contours=dict(type='constraint', value=35, operation='='), line=dict(color='black', width=2)))

    #Add survivability limits
    if show_survivability_young:
        fig.add_trace(
            go.Scatter(x=survivability_young['Tair'], y=survivability_young['rh'], mode='lines', name='Young (18-40)',
                       legendgrouptitle_text="Survivability limit", legendgroup='group1',
                       showlegend=True, line=dict(color='purple', width=2)))

    if show_survivability_elderly:
        fig.add_trace(
            go.Scatter(x=survivability_elderly['Tair'], y=survivability_elderly['rh'], mode='lines', name='Elderly (over 65)',
                       legendgrouptitle_text="Survivability limit", legendgroup='group1',
                       showlegend=True, line=dict(color='darkred', width=2)))

    #Add liveability and survivabiltiy ranges
    if show_liv_young or show_liv_elderly:

        fig.add_trace(
            go.Scatter(x=liv['Tair'], y=liv['rh'], mode='lines', name=title_ending,legendgroup='group3',
                       legendgrouptitle_text="Liveability limit", showlegend=True, line=dict(color='darkblue', width=2)))

        surv_not_liv = pd.read_csv(surv_not_liv_path, index_col=0)
        surv_not_liv = surv_not_liv.map(lambda x: 1 if x else None)

        set3_colors = px.colors.qualitative.Set3
        muted_yellow = set3_colors[11]
        muted_yellow = muted_yellow.replace('rgb', 'rgba').replace(')', f', {0.2})')

        # Add survivable but not liveable region
        fig.add_trace(go.Heatmap(x=temperature, y=humidity, z=surv_not_liv,
                       name='Survivable but not liveable (no activity possible without storing heat internally)',
                       showscale=False,  # Hide the color scale
                       colorscale=[[0, muted_yellow], [1, muted_yellow]]))

        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(color=muted_yellow, symbol='square', size=20),
            showlegend=True,
            legendgrouptitle_text="Liveability limit",
            name='No activities possible',
            legendgroup='group3'
        ))

        # Add not survivable region
        muted_orange = set3_colors[5]
        muted_orange = muted_orange.replace('rgb', 'rgba').replace(')', f', {0.2})')
        fig.add_trace(go.Heatmap(x=temperature, y=humidity, z=not_surv,
                       name='Not survivable',
                       showscale=False,
                       colorscale=[[0, muted_orange], [1, muted_orange]]))

        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(color=muted_orange, symbol='square', size=20),
            showlegend=True,
            legendgrouptitle_text="Not survivable",
            name='Not survivable',
            legendgroup='group1'
        ))

        #Add liveability ranges
        grey_scale = [[0, 'rgb(70, 70, 70)'], [1, 'rgb(255, 255, 255)']]
        grey_scale_r = [[0, 'rgb(255, 255, 255)'], [1, 'rgb(70, 70, 70)']]

        fig.add_trace(
            go.Contour(
                x=temperature,
                y=humidity,
                z=Mmax_MET,
                colorscale=grey_scale,
                name='Maximum Metabolic Rate',
                showscale=False,

                contours=dict(
                    start=1,
                    end=8.0,
                    size=1,
                    coloring='fill',
                    showlabels=False,
                    labelfont=dict(
                        size=12,
                        color='black'
                    )
                )
            )
        )

        #Create a minimal dataset for enabling creating a custom colorbar
        x = [0, 1]
        y = [0, 1]
        z = [[1, 2], [2, 3]]

        #Create a separate plot to show the colorbar
        fig.add_trace(
            go.Contour(
                x=x,
                y=y,
                z=z,
                colorscale=grey_scale_r,
                name='Maximum Metabolic Rate',
                showscale=True,
                colorbar=dict(
                    title='Safe sustained activity<br> (Maximum METs)',
                    titleside='top',
                    len=0.7,
                    x=1.02,
                    y=0,
                    xanchor='left',  # Anchor the left edge of the colorbar
                    yanchor='bottom',
                    tickvals=[1, 2, 3, 4, 5, 6, 7, 7.5],  # Values on the colorbar
                    ticktext=['8', '7', '6 ------------------------', '5', '4', '3 ------------------------', '2', '1.5 ---------------------']
                ),
                contours=dict(
                    start=1,
                    end=8,
                    size=1,
                    coloring='fill',
                    showlabels=False,
                    labelfont=dict(
                        size=18,
                        color='black'
                    )
                )
            )
        )

        #Add annotations to the colorbar
        colorbar_annotations = [
            # Labels for sustainable activities
            dict(
                xref='paper', yref='paper',
                x=1.17, y=0.49,  # y position for the label,
                text = 'Light physical <br>activities',
                showarrow = False, align='center'
                ),
            dict(
                xref='paper', yref='paper',
                x=1.18, y=0.3,  # y position for the label,
                text='Medium physical <br>activities',
                showarrow=False, align='center'
            ),
            dict(
                xref='paper', yref='paper',
                x=1.18, y=0.09,  # y position for the label,
                text='Vigorous physical <br>activities',
                showarrow=False, align='center'
            )
        ]

        for annotation in colorbar_annotations:
            if 'line' in annotation:
                fig.add_shape(annotation)
            else:
                fig.add_annotation(annotation)

        #Make sure the colorbar is fully displayed by adjusting the margins
        fig.update_layout(
            margin=dict(l=50, r=200, t=50, b=50)
        )

    #Show Humidex range
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

        #We only display the values for the hottest week (not previous and succeeding week)
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

    #Set plot titles and labels
    fig.update_layout(xaxis_title='Dry Bulb Air Temperature (°C)',
                      yaxis_title='Relative Humidity (%)', template='simple_white',
                      legend2=dict(yanchor="top", xanchor="center", y=-0.12, x=0.5, orientation='h',
                      title='Weather scenarios:'),
                      width=1200, height=900)

    fig.update_xaxes(range=[25, 60])
    fig.update_yaxes(range=[0, 80])

    st.plotly_chart(fig)

#Visualization for the distribution shifts of the hourly summer values compared to the baseline file
def summer_diff_distr_plot(building):

    zones = st.session_state.zones[building]
    zone = st.sidebar.selectbox("Choose zone", zones)
    summer_diff_file_path = 'Output/data/summer_differences_data.h5'
    weather_files = st.session_state.weather_folders

    #Need to uplaod at least two weather scenarios for calculating differences to baseline scenario
    if len(weather_files) == 1:
        st.error("Comparison Not Available: Only one weather file has been uploaded. To enable assessment of distribution shifts, please upload additional weather files.")
        return

    #Colors to use for displaying distribution shifts
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

    fig.update_layout(template='simple_white', width=1000, height=700, violinmode='group')
    fig.update_xaxes(linecolor='lightgrey', showticklabels=False, ticks="")
    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="black", opacity=1)
    fig.update_yaxes(secondary_y=False, gridcolor='lightgrey', showgrid=True)

    #Add a legend for the weather scenarios
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

#Visualization of the indoor conditions over the hottest week with previous and succeeding weeks
def hottest_weeks_plot(building):

    weather_files = st.session_state.weather_folders
    zones = st.session_state.zones[building]
    zone = st.sidebar.selectbox("Choose zone", zones)

    hottest_file_path = 'Output/data/hottest_weeks_data.h5'

    x_values = np.arange(1, 21 * 24 + 1)
    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    rows = len(metrics)
    row_titles = metrics
    cols = 1

    fig = make_subplots(rows=rows, cols=cols, shared_xaxes=True, vertical_spacing=0.05)

    for k, metric in enumerate(metrics):
        for i, weather in enumerate(weather_files):

            data = read_data_for_display(hottest_file_path, building, weather, metric, zone)

            fig.add_trace(go.Scatter(x=x_values, y=data, xaxis="x1", line_dash='solid', name=weather,line=dict(color=colors[i]), showlegend=False), row=k + 1, col=1)

        fig.add_hline(y=st.session_state.metrics_thresholds[metric], row=k + 1, col=1, line_width=1.5, line_dash="dash", line_color='black',opacity=1)

    x_values = x_values[::24]
    ticktext = 21 * ['']
    ticktext[3] = '     Hottest Week - 1'
    ticktext[10] = '      Hottest Week'
    ticktext[17] = '      Hottest Week + 1'

    fig.update_layout(width=1500, height=900, template='simple_white')

    fig.update_xaxes(tickvals=x_values, ticktext=ticktext)
    fig.update_yaxes(gridcolor='lightgrey', showgrid=True)

    for k, metric in enumerate(metrics):
        yaxis_nr = 'yaxis' + str(k + 1)
        fig['layout'][yaxis_nr].update(title=row_titles[k])

    fig.add_vline(x=7 * 24, line_width=1, line_color='black', opacity=1)
    fig.add_vline(x=14 * 24, line_width=1, line_color='black', opacity=1)

    #Add a legend for the weather scenarios
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


#Reading data for a specific building, weather file, metric and zone
def read_data_for_display(hdf5_file_path, building_folder, weather, metric, zone):
    hdf_key = f'{building_folder}/{zone}/{weather}/{metric}'
    arr = pd.read_hdf(hdf5_file_path, key=hdf_key).to_numpy()
    return np.concatenate(arr)


def calculate_humidex(temperature, humidity):
    e = 6.112 * np.exp(17.67 * temperature / (temperature + 243.5)) * humidity / 100
    humidex = temperature + (5/9) * (e - 10)
    return humidex

def create_dh_eh_table(dh_eh_file_path, tc_model, time_period, metric_type):
    # metric_type: 'dh' or 'eh'
    # time_period: 'annual' or 'max'

    # Reading data from HDF and creating a table
    all_data = []

    show_leeds = False

    idx = 0
    if time_period == 'Annual' and metric_type == "Exceedance hours":
        idx = 1
    elif time_period == "Maximum Week" and metric_type == "Degree hours":
        idx = 2
        if tc_model == 'SET':
            show_leeds = st.radio("Highlight archetype zones that surpass LEED's passive survivability threshold (120 SET Dh)", ["Yes", "No"]) == "Yes"
            if show_leeds and st.session_state.metrics_thresholds['SET'] != 30:
                st.error(f"SET threshold is set to {round(st.session_state.metrics_thresholds['SET'], 1)} and not 30 as specified by LEED's passive survivability pilot")
    elif time_period == "Maximum Week" and metric_type == "Exceedance hours":
        idx = 3

    with pd.HDFStore(dh_eh_file_path, 'r') as store:

        for building_key in store.keys():
            building_key = building_key.lstrip('/')
            building_data = store[building_key]
            building_name, zone, weather, metric = building_key.split('/')
            if metric == tc_model:
                data = {
                    'Building': building_name,
                    'Zone': zone,
                    'Weather': weather,
                    metric_type: building_data[idx]
                }
                all_data.append(data)

    # Creating a DataFrame for the table
    df = pd.DataFrame(all_data)

    pivot_df = df.pivot_table(index=['Building', 'Zone'], columns='Weather', values=metric_type)
    pivot_df = pivot_df.reset_index()

    gb = GridOptionsBuilder.from_dataframe(pivot_df)

    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=True)

    for col in pivot_df.columns[2:]:  # Skip the first two columns (Building and Zone)
        if show_leeds:
            gb.configure_column(col, cellStyle=color_formatter_js())
        else:
            gb.configure_column(col)

    gb.configure_grid_options(headerHeight=50)

    gb.configure_grid_options(
        domLayout='autoHeight',
        pagination=False
    )

    gridOptions = gb.build()
    theme = 'alpine'

    AgGrid(pivot_df, gridOptions=gridOptions, theme=theme,fit_columns_on_grid_load=True, height=400, allow_unsafe_jscode=True)

def color_formatter_js():
    return JsCode("""
    function(params) {
        if (params.value >= 120) {
            return {
                'color': 'red',
            };
        } else {
            return {
                'color': 'black',
            };
        }
    };
    """)

if __name__ == "__main__":
    main()