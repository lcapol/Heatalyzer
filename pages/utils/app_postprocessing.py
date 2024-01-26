##EnergyPlus output visualization
import os
from eppy.modeleditor import IDF
import os.path
import pandas as pd
import plotly.graph_objects as go
from .epw import epw
from datetime import datetime, timedelta
import math
from numpy import trapz
import numpy as np
from plotly.subplots import make_subplots
from thermofeel import calculate_wbt, calculate_bgt, calculate_humidex
import streamlit as st
import sys
import shutil

iddfile = '/Applications/EnergyPlus-23-1-0/Energy+.idd'

metrics = ['Temperature', 'Relative Humidity' , 'Humidex', 'SET', 'PMV', 'WBGT']

metrics_dh_eh = ['Humidex', 'SET', 'Temperature']

#Variables to read for thermal comfort models
temp_var = "Zone Mean Air Temperature"
hum_var = "Zone Air Relative Humidity"
set_var = 'Zone Thermal Comfort Pierce Model Standard Effective Temperature'
pmv_var = 'Zone Thermal Comfort Fanger Model PMV'
mrt_var = 'Zone Thermal Comfort Mean Radiant Temperature'

def transform_date(input_dates):

    formatted_dates = []
    for input_date in input_dates:
        # Parse the input date string and remove leading whitespaces
        input_date = input_date.lstrip(' ')

        # Check if the input_date ends with '24:00:00' because datetime does not handle 24:00
        if input_date.endswith('24:00:00'):
            # Replace '24:00:00' with '00:00:00' and add one day
            input_date = input_date.replace('24:00:00', '00:00:00')
            parsed_date = datetime.strptime(input_date, "%m/%d  %H:%M:%S") + timedelta(days=1)
        else:
            parsed_date = datetime.strptime(input_date, "%m/%d  %H:%M:%S")

        # Format the date as "Month Day"
        formatted_date = parsed_date.strftime("%B %d %H:%M")
        formatted_dates.append(formatted_date)

    return formatted_dates

def postprocess(output_folders, building_folders, weather_folders):

    IDF.setiddname(iddfile)

    data_path = 'data'

    if os.path.exists(data_path):
        # Remove all files and folders in the directory
        for filename in os.listdir(data_path):
            file_path = os.path.join(data_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        # Create the directory if it does not exist
        os.makedirs(data_path)

    total_simulations = len(output_folders)
    completed_simulations = 0

    # Initialize Streamlit progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    st.session_state.zones = {}

    for building_folder in building_folders:


        building_path = building_folder + '/' + weather_folders[0] + '/in.idf'
        idf = IDF(building_path)
        zones = idf.idfobjects['ZONE']
        zone_names = [zone.Name.upper() for zone in zones]

        #Determine Zones that People live in (only those are relevant and have all thermal comfort values)
        zones_inh = []

        for zone in zone_names:
            people_objects = [obj for obj in idf.idfobjects['PEOPLE'] if obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name.upper() == zone]

            # skip this zone if no people live in it
            if people_objects == []:
                continue

            zones_inh.append(zone)

        st.session_state.zones[building_folder] = zones_inh

        #Initialize the dictionaries
        annual_data_dicts = {}
        summer_data_dicts = {}
        hottest_data_dicts = {}
        summer_differences_dicts = {}
        dh_eh_dicts = {}
        max_hum_dicts = {}

        for metric in metrics:
            annual_data_dicts[metric] = {}
            summer_data_dicts[metric] = {}
            hottest_data_dicts[metric] = {}
            summer_differences_dicts[metric] = {}
            for zone in zones_inh:
                annual_data_dicts[metric][zone] = {}
                summer_data_dicts[metric][zone] = {}
                hottest_data_dicts[metric][zone] = {}
                summer_differences_dicts[metric][zone] = {}
                max_hum_dicts[zone] = {}

        for metric in metrics_dh_eh:
            dh_eh_dicts[metric] = {}
            for zone in zones_inh:
                dh_eh_dicts[metric][zone] = {}

        #Read in baseline file data
        baseline_output_csv_path = building_folder + '/' + st.session_state.baseline_file + '/eplusout.csv'
        baseline_output = pd.read_csv(baseline_output_csv_path)
        baseline_time_step = baseline_output.loc[:, 'Date/Time'].values
        summer_filter = filter_summer_months(transform_date(baseline_time_step))
        baseline_file = st.session_state.baseline_file

        for weather_folder in weather_folders:

            # Update the progress bar
            progress_bar.progress(completed_simulations / total_simulations)
            status_text.text(f'Processing simulation {completed_simulations + 1} of {total_simulations}...')

            simulation_folder = building_folder + '/' + weather_folder

            building_path = simulation_folder + '/in.idf'
            weather_path = simulation_folder + '/weather.epw'

            output_csv_path = simulation_folder + '/eplusout.csv'
            output = pd.read_csv(output_csv_path)
            time_step = output.loc[:, 'Date/Time'].values
            time_step = transform_date(time_step)

            annual_file_path = data_path + '/annual_data.h5'  # Change this to your desired file path
            summer_file_path = data_path + '/summer_data.h5'  # Change this to your desired file path
            hottest_file_path = data_path + '/hottest_weeks_data.h5'  # Change this to your desired file path
            summer_diff_file_path = data_path + '/summer_differences_data.h5'
            dh_eh_file_path = data_path + '/dh_eh_data.h5'
            max_hum_file_path = data_path + '/max_hum_data.h5'

            # Look for hottest week in the year and extract time steps for the hottest week
            file = epw()
            file.read(weather_path)
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']

            (start_month, start_day), temp_extreme_weeks = find_most_extreme_week(file)
            start_month = months[start_month-1]
            start_day = f"{start_day:02d}"
            formatted_date = f"{start_month} {start_day} 01:00"
            hottest_week_start = time_step.index(formatted_date)
            hottest_start = hottest_week_start - 7*24
            hottest_end = hottest_week_start + 2*7*24

            for zone in zones_inh:
                temp_column = zone + ':' + temp_var
                hum_column = zone + ':' + hum_var
                set_column = zone + ':' + set_var
                pmv_column = zone + ':' + pmv_var
                mrt_column = zone + ':' + mrt_var

                # Extract temperature data form output
                temp_idx = output.columns.str.contains(temp_column)
                temp_data = output.loc[:, temp_idx].values.flatten()
                annual_data_dicts['Temperature'][zone][weather_folder] = temp_data

                # Extract temperature data for the hottest mean week and add to dictionary
                hottest_temp_data = temp_data[hottest_start:hottest_end]
                hottest_data_dicts['Temperature'][zone][weather_folder] = hottest_temp_data

                # Calculate Temperature Degree and Exceedance hours
                auc_input = [max(0, element - st.session_state.metrics_thresholds['Temperature']) for element in temp_data]
                auc_temp_val = trapz(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_temp_max, max_days_over = find_week_with_max_total(auc_input)
                dh_eh_dicts['Temperature'][zone][weather_folder] = (round(auc_temp_val, 2), days_over, round(auc_temp_max, 2), max_days_over)

                # Extract humidity data form output
                hum_idx = output.columns.str.startswith(hum_column)
                hum_data = output.loc[:, hum_idx].values.flatten()
                annual_data_dicts['Relative Humidity'][zone][weather_folder] = temp_data

                hottest_hum_data = hum_data[hottest_start:hottest_end]
                hottest_data_dicts['Relative Humidity'][zone][weather_folder] = hottest_hum_data

                # Compute humidex from the temperature and humidity
                humidex_data, max_hum_cond = humidex_list(temp_data, hum_data, True)
                max_hum_dicts[zone][weather_folder] = max_hum_cond # max_hum_cond = (max_humidex, max_hum_temp, max_hum_rh)
                hottest_humidex_data = humidex_data[hottest_start:hottest_end]
                hottest_data_dicts['Humidex'][zone][weather_folder] = hottest_humidex_data
                annual_data_dicts['Humidex'][zone][weather_folder] = humidex_data

                #Calculate Humidex Degree and Exceedance hours
                auc_input = [max(0, element - st.session_state.metrics_thresholds['Humidex']) for element in humidex_data]
                auc_humidex_val = trapz(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_humidex_max, max_days_over = find_week_with_max_total(auc_input)
                dh_eh_dicts['Humidex'][zone][weather_folder] = (round(auc_humidex_val, 2), days_over, round(auc_humidex_max, 2), max_days_over)

                # Extract SET data form output
                set_idx = output.columns.str.startswith(set_column)
                set_data = output.loc[:, set_idx].values.flatten()
                annual_data_dicts['SET'][zone][weather_folder] = set_data

                # Extract SET data for the hottest mean week and append to dictionary
                hottest_set_data = set_data[hottest_start:hottest_end]
                hottest_data_dicts['SET'][zone][weather_folder] = hottest_set_data

                # Calculate SET Degree and Exceedance hours
                auc_input = [max(0, element - st.session_state.metrics_thresholds['SET']) for element in set_data]
                auc_set_val = trapz(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_set_max, max_days_over = find_week_with_max_total(auc_input)
                dh_eh_dicts['SET'][zone][weather_folder] = (round(auc_set_val, 2), days_over, round(auc_set_max, 2), max_days_over)

                # Extract PMV data form output
                pmv_idx = output.columns.str.startswith(pmv_column)
                pmv_data = output.loc[:, pmv_idx].values.flatten()
                annual_data_dicts['PMV'][zone][weather_folder] = pmv_data

                # Extract PMV data for the hottest mean week and append to dictionary
                hottest_pmv_data = pmv_data[hottest_start:hottest_end]
                hottest_data_dicts['PMV'][zone][weather_folder] = hottest_pmv_data

                # Extract MRT data form output
                mrt_idx = output.columns.str.startswith(mrt_column)
                mrt_data = output.loc[:, mrt_idx].values.flatten()
                # calculate indoor WBGT from these values
                wbgt_data = calculate_wbgt_lis(temp_data, hum_data, mrt_data)
                annual_data_dicts['WBGT'][zone][weather_folder] = wbgt_data

                # Extract temperature data for the hottest mean week and append to dictionary
                hottest_wbgt_data = wbgt_data[hottest_start:hottest_end]
                hottest_data_dicts['WBGT'][zone][weather_folder] = hottest_wbgt_data

            completed_simulations += 1

        #Calculate differences
        for weather_folder in weather_folders:

            # Skip baseline folder
            if weather_folder == st.session_state.baseline_file:
                for metric in metrics:
                    for zone in zones_inh:
                        baseline_metric_data = annual_data_dicts[metric][zone][baseline_file]
                        summer_data_dicts[metric][zone][weather_folder] = np.array(baseline_metric_data)[summer_filter]

                continue

            # Calculate differences for each metric and zone
            for metric in metrics:
                for zone in zones_inh:
                    baseline_metric_data = annual_data_dicts[metric][zone][baseline_file]
                    current_metric_data = annual_data_dicts[metric][zone][weather_folder]

                    summer_data_dicts[metric][zone][weather_folder] = np.array(current_metric_data)[summer_filter]

                    # Calculate differences only for summer months
                    summer_diff = np.array(current_metric_data)[summer_filter] - np.array(baseline_metric_data)[summer_filter]
                    summer_differences_dicts[metric][zone][weather_folder] = summer_diff

        #Save annual data in hdf file
        for metric, data_dict in annual_data_dicts.items():
            for zone, data_dict2 in data_dict.items():
                for weather, data in data_dict2.items():
                    hdf_key = f'{building_folder}/{zone}/{weather}/{metric}'
                    df = pd.DataFrame(data)
                    df.to_hdf(annual_file_path, key=hdf_key, mode='a')

        # Save summer data in hdf file
        for metric, data_dict in summer_data_dicts.items():
            for zone, data_dict2 in data_dict.items():
                for weather, data in data_dict2.items():
                    hdf_key = f'{building_folder}/{zone}/{weather}/{metric}'
                    df = pd.DataFrame(data)
                    df.to_hdf(summer_file_path, key=hdf_key, mode='a')

        #Save data of hottest weeks in hdf file
        for metric, data_dict in hottest_data_dicts.items():
            for zone, data_dict2 in data_dict.items():
                for weather, data in data_dict2.items():
                    hdf_key = f'{building_folder}/{zone}/{weather}/{metric}'
                    df = pd.DataFrame(data)
                    df.to_hdf(hottest_file_path, key=hdf_key, mode='a')

        # Save the summer differences data
        for metric, data_dict in summer_differences_dicts.items():
            for zone, data_dict2 in data_dict.items():
                for weather, data in data_dict2.items():
                    hdf_key = f'{building_folder}/{zone}/{weather}/{metric}'
                    df = pd.DataFrame(data)
                    df.to_hdf(summer_diff_file_path, key=hdf_key, mode='a')

        # Save the dh and eh values
        for metric, data_dict in dh_eh_dicts.items():
            for zone, data_dict2 in data_dict.items():
                for weather, data in data_dict2.items():
                    hdf_key = f'{building_folder}/{zone}/{weather}/{metric}'
                    df = pd.DataFrame([data]) # data contains (annual_dh, annual_eh, max_dh, max_eh)
                    df.to_hdf(dh_eh_file_path, key=hdf_key, mode='a')

        for zone, data_dict2 in max_hum_dicts.items():
            for weather, data in data_dict2.items():
                hdf_key = f'{building_folder}/{zone}/{weather}/Humidex'
                df = pd.DataFrame([data])  # data contains (max_humidex, max_hum_temp, max_hum_rh)
                df.to_hdf(max_hum_file_path, key=hdf_key, mode='a')

    # Complete the progress bar
    progress_bar.progress(1.0)
    status_text.text(f'Processing complete. {total_simulations} simulations run.')

def filter_summer_months(time_step):
    summer_months = st.session_state.summer_months
    print(summer_months)
    month_filter = [datetime.strptime(x, "%B %d %H:%M").month in summer_months for x in time_step]
    return month_filter


#iterate over the whole array and find week with maximum total and report degrees over for that one
def find_week_with_max_total(array):

    week_start = 0
    week_end = week_hours = 24*7

    arr_len = len(array)

    week_data = array[week_start:week_end]
    max_total = sum(week_data)
    max_days_over = days_over = sum([int(item > 0) for item in week_data])

    prev_week_total = max_total

    for i in range(arr_len-week_hours-1):
        first_item = array[week_start]

        week_start+=1
        week_end+=1

        new_item = array[week_end]

        week_total = prev_week_total - first_item + new_item
        days_over = days_over - int(first_item > 0) + int(new_item > 0)

        if week_total > max_total:
            max_total = week_total
            max_days_over = days_over

        prev_week_total = week_total

    return max_total, max_days_over



def humidex_list(temp_list, rel_hum_list, max_cond=False):

    humidex_lis = []

    max_hum=0
    max_hum_temp=0
    max_hum_rh=0

    for (i, temp) in enumerate(temp_list):
        hum = rel_hum_list[i]
        humidex_val = humidex(temp, hum)

        if humidex_val > max_hum:
            max_hum = humidex_val
            max_hum_temp = temp
            max_hum_rh = hum

        humidex_lis.append(humidex_val)

    if max_cond:
        return humidex_lis, (max_hum, max_hum_temp, max_hum_rh)
    else:
        return humidex_lis

##Calculates the humidex from provided temperature (in Celcius) and relative humidity
def humidex(temperature, rel_humidity):

    #calculate dewpoint from temperature and humidity
    dewpoint_temp = dew_from_hum(temperature, rel_humidity)

    #calculate dewpoint temperature in kelvin
    Kelvin = 273.15
    dewpoint_temp_K = dewpoint_temp + Kelvin

    #calculate humidex
    e = 6.11 * math.exp(5417.7530 * ((1/273.16) - (1/dewpoint_temp_K)))
    h = (0.5555)*(e - 10.0)
    humidex = temperature + h

    return humidex

##Calculates the dewpoint temperature from provided temperature (in Celcius) and humidity
def dew_from_hum(temperature, rel_humdity):

    numer = 243.04 * (math.log(rel_humdity / 100) + ((17.625 * temperature) / (243.04 + temperature)))
    denom = (17.625 - math.log(rel_humdity / 100) - ((17.625 * temperature) / (243.04 + temperature)))
    dewpoint_temp = numer / denom

    return dewpoint_temp


#Identify most extreme (mean) week for the variable of interest
def find_most_extreme_week(file):

    epw_data = file.dataframe['Dry Bulb Temperature']

    # Initialize variables for tracking the hottest week
    extreme_week = epw_data[0:7 * 24]
    mean_extreme_week = extreme_week.mean()  # Initialize with the mean of the first week
    current_week_start = 0  # Index of the first day in the current 7-day window

    for i in range(7 * 24, len(epw_data), 24):        # Calculate the mean temperature for the next 7 days
        current_week_mean = epw_data[i - 7 * 24:i].mean()

        # Check if the current mean is greater than the current hottest week mean
        if current_week_mean > mean_extreme_week:
            mean_extreme_week = current_week_mean
            current_week_start = i - 7 * 24  # Update the start index of the hottest week

    current_week_end =  current_week_start + 7 * 24

    #we want to visualize the hottest week with its previous and succeeding week
    time_start = current_week_start -7*24
    time_end=current_week_end + 7*24

    start_month = file.dataframe['Month'].iloc[current_week_start]
    start_day = file.dataframe['Day'].iloc[current_week_start]

    extreme_weeks = epw_data[time_start:time_end]

    return (start_month, start_day), extreme_weeks


if __name__ == '__main__':

    output_folders = sys.argv[1]
    building_folders = sys.argv[2]
    weather_folders = sys.argv[3]

    postprocess(output_folders, building_folders, weather_folders)


#Calculate indoor WBGT temperature
def calculate_wbgt_lis(temperature, humidity, mrt, wind_speed=0.15):

    wbgt_lis = []
    K = 273.15

    for i in range(len(temperature)):
        mrt_K = mrt[i] + K
        temp_K = temperature[i] + K

        wbt = calculate_wbt(temp_K,humidity[i]) - K
        bgt = calculate_bgt(temp_K, mrt_K, wind_speed) - K

        wbgt = 0.7*wbt + 0.3*bgt
        wbgt_lis.append(wbgt)

    return wbgt_lis

def scale_windspeed(va, h):

    #c = 1 / np.log10(10 / 0.01)
    c = 0.333333333333
    vh = va * np.log10(h / 0.01) * c

    return vh