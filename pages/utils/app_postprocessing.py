##EnergyPlus output postprocessing
import os
from eppy.modeleditor import IDF
import os.path
import pandas as pd
from .epw import epw
from datetime import datetime, timedelta
from numpy import trapz
import numpy as np
from thermofeel import calculate_wbt, calculate_bgt
import streamlit as st
import shutil
from pythermalcomfort import humidex

iddfile = '/Applications/EnergyPlus-23-1-0/Energy+.idd'

#Metrics to report for analysis
metrics = ['Temperature', 'Relative Humidity' , 'Humidex', 'SET', 'PMV', 'WBGT']
tc_models = ['Temperature', 'Humidex', 'SET', 'PMV', 'WBGT']

#Metrics to report for Dh/Eh analysis
metrics_dh_eh = ['Humidex', 'SET', 'Temperature']

#Variables to read for thermal comfort models
variables = {'Temperature': 'Zone Mean Air Temperature',
             'Relative Humidity':'Zone Air Relative Humidity',
             'SET': 'Zone Thermal Comfort Pierce Model Standard Effective Temperature',
             'PMV': 'Zone Thermal Comfort Fanger Model PMV',
             'MRT': 'Zone Thermal Comfort Mean Radiant Temperature'}

def postprocess(output_folders, building_folders, weather_folders):

    IDF.setiddname(iddfile)

    #Folder to save EnergyPlus simulation result data in
    data_path = 'Output/data'

    if os.path.exists(data_path):
        #Remove all files and folders in the directory (from potential previous runs)
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
        #Create the directory if it does not exist
        os.makedirs(data_path)

    #Output paths for all data files
    annual_file_path = data_path + '/annual_data.h5'
    summer_file_path = data_path + '/summer_data.h5'
    hottest_file_path = data_path + '/hottest_weeks_data.h5'
    summer_diff_file_path = data_path + '/summer_differences_data.h5'
    dh_eh_file_path = data_path + '/dh_eh_data.h5'
    max_hum_file_path = data_path + '/max_hum_data.h5'

    #Total number of simulations to process
    total_simulations = len(output_folders)
    completed_simulations = 0

    #Initialize Streamlit progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    #Keep track of zones to report for different buildings
    st.session_state.zones = {}

    for building_folder in building_folders:

        #Read in building file
        _, building_name = building_folder.split('/')
        building_path = building_folder + '/' + weather_folders[0] + '/in.idf'
        idf = IDF(building_path)

        zones = idf.idfobjects['ZONE']
        zone_names = [zone.Name.upper() for zone in zones]

        #Determine Zones that People live in (only those are relevant and have all thermal comfort values)
        zones_inh = []

        for zone in zone_names:
            people_objects = [obj for obj in idf.idfobjects['PEOPLE'] if obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name.upper() == zone]

            #Skip this zone if no people live in it
            if people_objects == []:
                continue

            #Otherwise, append it to the list of zones to report
            zones_inh.append(zone)

        st.session_state.zones[building_name] = zones_inh

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

        #Read in output data for baseline building
        baseline_output_csv_path = building_folder + '/' + st.session_state.baseline_file + '/eplusout.csv'
        baseline_output = pd.read_csv(baseline_output_csv_path)
        baseline_time_step = baseline_output.loc[:, 'Date/Time'].values

        #Determine summer filter based on baseline file
        summer_filter = filter_summer_months(transform_date(baseline_time_step))
        baseline_file = st.session_state.baseline_file

        #Process all weather sceanarios for current building
        for weather_folder in weather_folders:

            # Update the progress bar
            progress_bar.progress(completed_simulations / total_simulations)
            status_text.text(f'Processing simulation {completed_simulations + 1} of {total_simulations}...')

            simulation_folder = building_folder + '/' + weather_folder
            weather_path = simulation_folder + '/weather.epw'
            output_csv_path = simulation_folder + '/eplusout.csv'

            output = pd.read_csv(output_csv_path)
            time_step = output.loc[:, 'Date/Time'].values
            time_step = transform_date(time_step)

            #Look for hottest week in the year and extract time steps for the hottest week
            file = epw()
            file.read(weather_path)
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']

            start_month, start_day = find_most_extreme_week(file)
            start_month = months[start_month-1]
            start_day = f"{start_day:02d}"
            formatted_date = f"{start_month} {start_day} 01:00"
            hottest_week_start = time_step.index(formatted_date)
            hottest_start = hottest_week_start - 7*24
            hottest_end = hottest_week_start + 2*7*24

            for zone in zones_inh:

                for model in tc_models:
                    if model == 'Humidex':
                        temp_data = annual_data_dicts['Temperature'][zone][weather_folder]

                        #Extract relative humidity data form output
                        hum_column = zone + ':' + variables['Relative Humidity']
                        hum_idx = output.columns.str.startswith(hum_column)
                        hum_data = output.loc[:, hum_idx].values.flatten()
                        annual_data_dicts['Relative Humidity'][zone][weather_folder] = hum_data

                        #Extract relative humidity data for the hottest mean week and add to dictionary
                        hottest_hum_data = hum_data[hottest_start:hottest_end]
                        hottest_data_dicts['Relative Humidity'][zone][weather_folder] = hottest_hum_data

                        #Compute humidex from the temperature and humidity
                        data, max_hum_cond = humidex_list(temp_data, hum_data, True)
                        max_hum_dicts[zone][weather_folder] = max_hum_cond  # max_hum_cond = (max_humidex, max_hum_temp, max_hum_rh)

                    elif model == 'WBGT':
                        #Extract MRT data form output
                        mrt_column = zone + ':' + variables['MRT']
                        mrt_idx = output.columns.str.contains(mrt_column)
                        mrt_data = output.loc[:, mrt_idx].values.flatten()

                        #Calculate indoor WBGT from these values
                        hum_data = annual_data_dicts['Relative Humidity'][zone][weather_folder]
                        temp_data = annual_data_dicts['Temperature'][zone][weather_folder]
                        data = calculate_wbgt_lis(temp_data, hum_data, mrt_data)

                    else: #mode == Temperature, SET, and PMV

                        #Extract data form output
                        column = zone + ':' + variables[model]
                        idx = output.columns.str.contains(column)
                        data = output.loc[:, idx].values.flatten()

                    #Add annual data to dictionary
                    annual_data_dicts[model][zone][weather_folder] = data

                    #Extract data for the hottest mean week and add to dictionary
                    hottest_data = data[hottest_start:hottest_end]
                    hottest_data_dicts[model][zone][weather_folder] = hottest_data

                    if model in metrics_dh_eh:
                        # Calculate Temperature Degree and Exceedance hours
                        data = annual_data_dicts[model][zone][weather_folder]
                        auc_input = [max(0, element - st.session_state.metrics_thresholds[model]) for element in data]
                        auc_val = trapz(auc_input)
                        days_over = sum(elem > 0 for elem in auc_input)
                        auc_max, max_days_over = find_week_with_max_total(auc_input)
                        dh_eh_dicts[model][zone][weather_folder] = (round(auc_val, 2), days_over, round(auc_max, 2), max_days_over)

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

            #Calculate differences for each metric and zone
            for metric in metrics:
                for zone in zones_inh:
                    baseline_metric_data = annual_data_dicts[metric][zone][baseline_file]
                    current_metric_data = annual_data_dicts[metric][zone][weather_folder]

                    summer_data_dicts[metric][zone][weather_folder] = np.array(current_metric_data)[summer_filter]

                    # Calculate differences only for summer months
                    summer_diff = np.array(current_metric_data)[summer_filter] - np.array(baseline_metric_data)[summer_filter]
                    summer_differences_dicts[metric][zone][weather_folder] = summer_diff

        save_data_to_hdf(annual_data_dicts, annual_file_path, building_name)
        save_data_to_hdf(summer_data_dicts, summer_file_path, building_name)
        save_data_to_hdf(hottest_data_dicts, hottest_file_path, building_name)
        save_data_to_hdf(summer_differences_dicts, summer_diff_file_path, building_name)
        save_data_to_hdf(dh_eh_dicts, dh_eh_file_path, building_name, is_dh_eh=True)
        save_data_to_hdf(max_hum_dicts, max_hum_file_path, building_name, is_max_hum=True)

    # Complete the progress bar
    progress_bar.progress(1.0)
    status_text.text(f'Processing complete. {total_simulations} simulations run.')



def transform_date(input_dates):

    formatted_dates = []
    for input_date in input_dates:
        #Parse the input date string and remove leading whitespaces
        input_date = input_date.lstrip(' ')

        #Check if the input_date ends with '24:00:00' because datetime does not handle 24:00
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

def save_data_to_hdf(data_dicts, file_path, building_name, is_dh_eh=False, is_max_hum=False):
    for metric, data_dict in data_dicts.items():
        for zone, data_dict2 in (data_dict.items() if not is_max_hum else [(metric, data_dict)]):
            for weather, data in data_dict2.items():
                hdf_key = f'{building_name}/{zone}/{weather}/{"Humidex" if is_max_hum else metric}'
                if is_dh_eh or is_max_hum:
                    df = pd.DataFrame([data]) # Handle special case for dh/eh and max_hum
                else:
                    df = pd.DataFrame(data)
                df.to_hdf(file_path, key=hdf_key, mode='a')

def filter_summer_months(time_step):
    summer_months = st.session_state.summer_months
    month_filter = [datetime.strptime(x, "%B %d %H:%M").month in summer_months for x in time_step]
    return month_filter


#Iterate over an array to find the week with maximum total Degree hours (Dh) over 0; returns the respective Dh and Exceedance hours (Eh)
def find_week_with_max_total(array):

    week_hours = 24 * 7
    arr_len = len(array)

    #Extend the array to make sure we also wrap around the last month when looking for week with maximum Dh
    array_extended = array * 2

    #Initialize the first window
    week_data = array_extended[:week_hours]
    week_total = sum(week_data)
    days_over = sum(int(item > 0) for item in week_data)

    max_total = week_total
    max_days_over = days_over

    for week_start in range(1, arr_len):

        #Update the start and end of the window
        week_end = week_start + week_hours

        #Update totals by subtracting the first item and adding the new item
        first_item = array_extended[week_start - 1]
        new_item = array_extended[week_end - 1]

        week_total = week_total - first_item + new_item
        days_over = days_over - int(first_item > 0) + int(new_item > 0)

        #Update maximum Dh and Ex values if this window has a higher Dh value
        if week_total > max_total:
            max_total = week_total
            max_days_over = days_over

    return max_total, max_days_over

#Calculate Humidex for lists of temperature and relative humidity values
#If max_cond = True return the maximum humidex value reached with the respective temperature and relative humidity values
def humidex_list(temp_list, rel_hum_list, max_cond=False):

    humidex_lis = []

    max_hum=0
    max_hum_temp=0
    max_hum_rh=0

    for (i, temp) in enumerate(temp_list):
        hum = rel_hum_list[i]
        humidex_val = humidex(temp, hum, round=False)['humidex']

        if humidex_val > max_hum:
            max_hum = humidex_val
            max_hum_temp = temp
            max_hum_rh = hum

        humidex_lis.append(humidex_val)

    if max_cond:
        return humidex_lis, (max_hum, max_hum_temp, max_hum_rh)
    else:
        return humidex_lis

#Identify the hottest (mean) week
def find_most_extreme_week(file):

    epw_data = file.dataframe['Dry Bulb Temperature']
    week_hours = 24 * 7
    arr_len = len(epw_data)

    #Replicate data to make sure we also wrap around the last month when looking for hottest week
    epw_data_extended = pd.concat([epw_data, epw_data]).reset_index(drop=True)

    #Initialize variables for tracking the hottest week
    week_data = epw_data_extended[:week_hours]
    week_mean_temp = week_data.mean()

    max_mean_temp = week_mean_temp
    current_week_start = 0

    # Iterate in steps of 24 hours / 1 day
    for week_start in range(0, arr_len, 24):

        #Calculate the mean temperature for the current window of one week
        week_end = week_start + week_hours
        week_data = epw_data_extended[week_start:week_end]
        week_mean_temp = week_data.mean()

        #Update if the current week's mean temperature is higher than the max found so far
        if week_mean_temp > max_mean_temp:
            max_mean_temp = week_mean_temp
            current_week_start = week_start

    start_month = file.dataframe['Month'].iloc[current_week_start % arr_len]
    start_day = file.dataframe['Day'].iloc[current_week_start % arr_len]

    return start_month, start_day


#Calculate indoor WBGT temperature for lists of temperature and relative humidity values
def calculate_wbgt_lis(temperature, humidity, mrt, wind_speed=0.15):

    wbgt_lis = []
    K = 273.15

    for i in range(len(temperature)):

        #transform temperature into Kelvin for calculate_wbt and calculate_bgt
        mrt_K = mrt[i] + K
        temp_K = temperature[i] + K

        wbt = calculate_wbt(temp_K,humidity[i]) - K
        bgt = calculate_bgt(temp_K, mrt_K, wind_speed) - K

        wbgt = 0.7*wbt + 0.3*bgt
        wbgt_lis.append(wbgt)

    return wbgt_lis