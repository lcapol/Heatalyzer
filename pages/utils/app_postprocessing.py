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

iddfile = '/Applications/EnergyPlus-23-1-0/Energy+.idd'

metrics = ['Temperature', 'Relative Humidity' , 'Humidex', 'SET', 'PMV', 'WBGT']

metrics_dh_eh = ['Humidex', 'SET']
dh_eh_thresholds = {'Humidex': 35, 'SET': 30}

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
    os.makedirs(data_path, exist_ok=True)

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
            epw_data = file.dataframe['Dry Bulb Temperature']
            (hottest_start, hottest_end), temp_extreme_weeks = find_most_extreme_week(epw_data)

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
                auc_input = [max(0, element - dh_eh_thresholds['Humidex']) for element in humidex_data]
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
                auc_input = [max(0, element - dh_eh_thresholds['SET']) for element in set_data]
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

        #print(hottest_data_dicts)

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
    summer_months = [6, 7, 8]  # June, July, August
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


if __name__ == '__main__':

    output_folders = sys.argv[1]
    building_folders = sys.argv[2]
    weather_folders = sys.argv[3]

    postprocess(output_folders, building_folders, weather_folders)


######## OLD POSTPROCESSING

def postprocess2(output_folders, building_folders, weather_folders):

    nr_simulations = len(output_folders)
    nr_buildings = len(building_folders)
    nr_weather = len(weather_folders)

    mean_diff_temp_2022 = []
    mean_diff_hum_2022 = []
    mean_diff_set_2022 = []
    mean_diff_pmv_2022 = []
    mean_diff_wbgt_2022 = []
    mean_diff_temp_2022e = []
    mean_diff_hum_2022e = []
    mean_diff_set_2022e = []
    mean_diff_pmv_2022e = []
    mean_diff_wbgt_2022e = []
    mean_diff_temp_2080 = []
    mean_diff_hum_2080 = []
    mean_diff_set_2080 = []
    mean_diff_pmv_2080 = []
    mean_diff_wbgt_2080 = []
    mean_diff_temp_2080h = []
    mean_diff_hum_2080h = []
    mean_diff_set_2080h = []
    mean_diff_pmv_2080h = []
    mean_diff_wbgt_2080h = []

    humidex_eh_dh_dict = {
        "KL:ZONE": {},
        "BD:ZONE": {},
        "OT:ZONE": {}
    }

    temperature_eh_dh_dict = {
        "KL:ZONE": {},
        "BD:ZONE": {},
        "OT:ZONE": {}
    }
    set_eh_dh_dict = {
        "KL:ZONE": {},
        "BD:ZONE": {},
        "OT:ZONE": {}
    }
    pmv_eh_dh_dict = {
        "KL:ZONE": {},
        "BD:ZONE": {},
        "OT:ZONE": {}
    }

    humidex_max_eh_dh_dict = {
        "KL:ZONE": {},
        "BD:ZONE": {},
        "OT:ZONE": {}
    }

    set_max_eh_dh_dict = {
        "KL:ZONE": {},
        "BD:ZONE": {},
        "OT:ZONE": {}
    }

    max_hum_cond_dict = {
        "KL:ZONE": {},
        "BD:ZONE": {},
        "OT:ZONE": {}
    }
    zone_names = ["KL:ZONE", "BD:ZONE", "OT:ZONE"]

    for zone in zone_names:
        for weather_folder in weather_folders:
            max_hum_cond_dict[zone][weather_folder] = []

    for i in range(nr_simulations):

        output_folder = output_folders[i]

        archetype = find_archetype(output_folder)

        # Collect total energy demand across all zones for each weather file

        # OUTPUT:METER:DistrictCooling:Building (Hourly; J)
        mtr_var, unit = ("Cooling:DistrictCooling", 'J')

        ed_dict = {
            "Haringey_TMY": [],
            "Haringey_2022_Historical": [],
            "Haringey_2022_Extended_7": [],
            "Haringey_2080": [],
            "Haringey_2080_Heatwave": []
        }

        #Create visualizations for the thermal comfort metrics (temperature, humidex, SET, and PMV) for the specified zones
        temp_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        humidex_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        set_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        pmv_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        wbgt_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        summer_temp_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        summer_humidex_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        summer_pmv_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        summer_set_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        summer_wbgt_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        #Specify the zone names we are interested in plotting
        zone_names = ['KL:ZONE', 'BD:ZONE', 'OT:ZONE']

        auc_temp_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        auc_humidex_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        auc_set_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        auc_pmv_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        auc_wbgt_dict = {
            "KL:ZONE": {},
            "BD:ZONE": {},
            "OT:ZONE": {}
        }

        # Specify the summer months
        summer_months = [6, 7, 8]

        for zone in zone_names:
            humidex_eh_dh_dict[zone][archetype] = {}
            temperature_eh_dh_dict[zone][archetype] = {}
            set_eh_dh_dict[zone][archetype] = {}
            pmv_eh_dh_dict[zone][archetype] = {}

            humidex_max_eh_dh_dict[zone][archetype] = {}
            set_max_eh_dh_dict[zone][archetype] = {}

        for weather_folder in weather_folders:

            simulation_folder = output_folder + weather_folder

            #Input files for simulation
            weather_path = simulation_folder + '/weather.epw'
            #building_path = simulation_folder + '/in.idf'

            #Read in IDF File and get all Zone names
            #idf1 = IDF(building_path)

            #Extract all Zone names from the Input File and make them all upper case or specify the zone names we are interested in plotting
            #zones = idf1.idfobjects['Zone']
            #zone_names = [zone.Name.upper() for zone in zones]
            #zone_names = ['KL:ZONE', 'BD:ZONE', 'OT:ZONE']

            #Prepare Folder for the plots
            plots_path = simulation_folder + '/Plots'
            if not os.path.exists(plots_path):
                os.makedirs(plots_path)

            #Read in the output files
            output = pd.read_csv(simulation_folder + '/eplusout.csv')
            time_step = output.loc[:,'Date/Time'].values
            time_step = transform_date(time_step)
            # month_filter = time_step.isin(summer_months)
            month_filter = [datetime.strptime(x, "%B %d %H:%M").month in summer_months for x in time_step]

            #Read data for thermal comfort models
            temp_var = "Zone Mean Air Temperature"
            hum_var = "Zone Air Relative Humidity"
            set_var = 'Zone Thermal Comfort Pierce Model Standard Effective Temperature'
            pmv_var = 'Zone Thermal Comfort Fanger Model PMV'
            mrt_var = 'Zone Thermal Comfort Mean Radiant Temperature'

            #Collect AUC for humidex and number of days over threshold value for all zones
            auc_temp_thres = 30
            auc_humidex_thres = 35
            auc_set_thres = 30
            auc_pmv_thres = 1.5
            auc_wbgt_thres = 23

            #Specify if you also want to plot data for week before and after hottest week of the year
            weekbefore = True
            weekafter = True

            #Look for hottest week in the year and extract time steps for the hottest week
            file = epw()
            file.read(weather_path)
            epw_data = file.dataframe['Dry Bulb Temperature']
            (hottest_start, hottest_end), temp_extreme_weeks = find_most_extreme_week(epw_data)
            hottest_time = time_step[hottest_start:hottest_end]

            for zone in zone_names:
                temp_column = zone + ':' + temp_var
                hum_column = zone + ':' + hum_var
                set_column = 'PEOPLE ' + zone + ':' + set_var
                pmv_column = 'PEOPLE ' +zone + ':' + pmv_var
                mrt_column = 'PEOPLE ' + zone + ':' + mrt_var

                #Extract temperature data form output
                temp_idx = output.columns.str.startswith(temp_column)
                temp_data = output.loc[:, temp_idx].values.flatten()
                summer_temp_dict[zone][weather_folder] = temp_data[month_filter]

                #Extract temperature data for the hottest mean week and append to dictionary
                hottest_temp_data = temp_data[hottest_start:hottest_end]
                temp_dict[zone][weather_folder] = hottest_temp_data

                #Calculate AUC Metrics for Temperature
                auc_input = [max(0, element - auc_temp_thres) for element in temp_data]
                auc_temp_val = trapz(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_temp_dict[zone][weather_folder] = (auc_temp_val, days_over)
                temperature_eh_dh_dict[zone][archetype][weather_folder] = (auc_temp_val, days_over)

                #Extract humidity data form output
                hum_idx = output.columns.str.startswith(hum_column)
                hum_data = output.loc[:, hum_idx].values.flatten()

                #Compute humidex from the temperature and humidity
                humidex_lis, max_hum_cond = humidex_list(temp_list=temp_data, rel_hum_list=hum_data, max_cond=True)
                max_hum, max_hum_temp, max_hum_rh = max_hum_cond
                max_hum_cond_dict[zone][weather_folder].append((archetype, max_hum, max_hum_temp, max_hum_rh))

                #Append humidex for summer months to dict to calculate distribution later
                summer_humidex_dict[zone][weather_folder] = np.array(humidex_lis)[month_filter]

                #Extract humidex data for the hottest mean week and append to dictionary
                hottest_hum_lis = humidex_lis[hottest_start:hottest_end]
                humidex_dict[zone][weather_folder] = hottest_hum_lis

                #Calculate AUC Metrics for Humidex
                auc_input = [max(0, element - auc_humidex_thres) for element in humidex_lis]
                auc_humidex_val = trapz(auc_input)
                auc_humidex_max, max_days_over = find_week_with_max_total(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_humidex_dict[zone][weather_folder] = (auc_humidex_val, days_over)
                humidex_eh_dh_dict[zone][archetype][weather_folder] = (auc_humidex_val, days_over)
                humidex_max_eh_dh_dict[zone][archetype][weather_folder] = (auc_humidex_max, max_days_over)

                #Extract SET data form output
                set_idx = output.columns.str.startswith(set_column)
                set_data = output.loc[:, set_idx].values.flatten()

                # Append set for summer months to dict to calculate distribution later
                summer_set_dict[zone][weather_folder] = np.array(set_data)[month_filter]

                # Extract SET data for the hottest mean week and append to dictionary
                hottest_set_lis = set_data[hottest_start:hottest_end]
                set_dict[zone][weather_folder] = hottest_set_lis

                # Calculate AUC Metrics for SET
                auc_input = [max(0, element - auc_set_thres) for element in set_data]
                auc_set_val = trapz(auc_input)
                auc_set_max, max_days_over = find_week_with_max_total(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_set_dict[zone][weather_folder] = (auc_set_val, days_over)
                set_eh_dh_dict[zone][archetype][weather_folder] = (auc_set_val, days_over)
                set_max_eh_dh_dict[zone][archetype][weather_folder] = (auc_set_max, max_days_over)

                #Extract PMV data form output
                pmv_idx = output.columns.str.startswith(pmv_column)
                pmv_data = output.loc[:, pmv_idx].values.flatten()

                # Append set for summer months to dict to calculate distribution later
                summer_pmv_dict[zone][weather_folder] = np.array(pmv_data)[month_filter]

                # Extract PMV data for the hottest mean week and append to dictionary
                hottest_pmv_lis = pmv_data[hottest_start:hottest_end]
                pmv_dict[zone][weather_folder] = hottest_pmv_lis

                # Calculate AUC Metrics for PMV
                auc_input = [max(0, element - auc_pmv_thres) for element in pmv_data]
                auc_pmv_val = trapz(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_pmv_dict[zone][weather_folder] = (auc_pmv_val, days_over)
                pmv_eh_dh_dict[zone][archetype][weather_folder] = (auc_pmv_val, days_over)

                #Extract MRT data form output
                mrt_idx = output.columns.str.startswith(mrt_column)
                mrt_data = output.loc[:, mrt_idx].values.flatten()

                # calculate indoor WBGT from these values
                wbgt_data = calculate_wbgt_lis(temp_data, hum_data, mrt_data)

                #Extract temperature data for the hottest mean week and append to dictionary
                summer_wbgt_dict[zone][weather_folder] = np.array(wbgt_data)[month_filter]
                hottest_wbgt_data = wbgt_data[hottest_start:hottest_end]
                wbgt_dict[zone][weather_folder] = hottest_wbgt_data

                #Calculate AUC Metrics for WBGT
                auc_input = [max(0, element - auc_wbgt_thres) for element in wbgt_data]
                auc_wbgt_val = trapz(auc_input)
                days_over = sum(elem > 0 for elem in auc_input)
                auc_wbgt_dict[zone][weather_folder] = (auc_wbgt_val, days_over)


        #Calculate difference in mean humidex, temperature, SET, and PMV from the summer_humidex_dict/summer_temp_dict
        #For both 2022-TMY and 2080-TMY
        for zone in zone_names:
            temp_zone = summer_temp_dict[zone]
            tmy = temp_zone['/Haringey_TMY']
            _2080 = temp_zone['/Haringey_2080']
            _2022 = temp_zone['/Haringey_2022_Historical']
            _2022e = temp_zone['/Haringey_2022_Extended_7']
            _2080h = temp_zone['/Haringey_2080_Heatwave']
            meann = sum(tmy) / len(tmy)
            diff1 = (sum(_2080) / len(_2080)) - meann
            diff2 = (sum(_2022) / len(_2022)) - meann
            diff3 = (sum(_2022e) / len(_2022e)) - meann
            diff4 = (sum(_2080h) / len(_2080h)) - meann
            mean_diff_temp_2080.append((meann, diff1))
            mean_diff_temp_2022.append((meann, diff2))
            mean_diff_temp_2022e.append((meann, diff3))
            mean_diff_temp_2080h.append((meann, diff4))

            hum_zone = summer_humidex_dict[zone]
            tmy = hum_zone['/Haringey_TMY']
            _2080 = hum_zone['/Haringey_2080']
            _2022 = hum_zone['/Haringey_2022_Historical']
            _2022e = hum_zone['/Haringey_2022_Extended_7']
            _2080h = hum_zone['/Haringey_2080_Heatwave']
            meann = sum(tmy) / len(tmy)
            diff1 = (sum(_2080) / len(_2080)) - meann
            diff2 = (sum(_2022) / len(_2022)) - meann
            diff3 = (sum(_2022e) / len(_2022e)) - meann
            diff4 = (sum(_2080h) / len(_2080h)) - meann
            mean_diff_hum_2080.append((meann, diff1))
            mean_diff_hum_2022.append((meann, diff2))
            mean_diff_hum_2022e.append((meann, diff3))
            mean_diff_hum_2080h.append((meann, diff4))

            set_zone = summer_set_dict[zone]
            tmy = set_zone['/Haringey_TMY']
            _2080 = set_zone['/Haringey_2080']
            _2022 = set_zone['/Haringey_2022_Historical']
            _2022e = set_zone['/Haringey_2022_Extended_7']
            _2080h = set_zone['/Haringey_2080_Heatwave']
            meann = sum(tmy) / len(tmy)
            diff1 = (sum(_2080) / len(_2080)) - meann
            diff2 = (sum(_2022) / len(_2022)) - meann
            diff3 = (sum(_2022e) / len(_2022e)) - meann
            diff4 = (sum(_2080h) / len(_2080h)) - meann
            mean_diff_set_2080.append((meann, diff1))
            mean_diff_set_2022.append((meann, diff2))
            mean_diff_set_2022e.append((meann, diff3))
            mean_diff_set_2080h.append((meann, diff4))

            pmv_zone = summer_pmv_dict[zone]
            tmy = pmv_zone['/Haringey_TMY']
            _2080 = pmv_zone['/Haringey_2080']
            _2022 = pmv_zone['/Haringey_2022_Historical']
            _2022e = pmv_zone['/Haringey_2022_Extended_7']
            _2080h = pmv_zone['/Haringey_2080_Heatwave']
            meann = sum(tmy) / len(tmy)
            diff1 = (sum(_2080) / len(_2080)) - meann
            diff2 = (sum(_2022) / len(_2022)) - meann
            diff3 = (sum(_2022e) / len(_2022e)) - meann
            diff4 = (sum(_2080h) / len(_2080h)) - meann
            mean_diff_pmv_2080.append((meann, diff1))
            mean_diff_pmv_2022.append((meann, diff2))
            mean_diff_pmv_2022e.append((meann, diff3))
            mean_diff_pmv_2080h.append((meann, diff4))

            wbgt_zone = summer_wbgt_dict[zone]
            tmy = wbgt_zone['/Haringey_TMY']
            _2080 = wbgt_zone['/Haringey_2080']
            _2022 = wbgt_zone['/Haringey_2022_Historical']
            _2022e = wbgt_zone['/Haringey_2022_Extended_7']
            _2080h = wbgt_zone['/Haringey_2080_Heatwave']
            meann = sum(tmy) / len(tmy)
            diff1 = (sum(_2080) / len(_2080)) - meann
            diff2 = (sum(_2022) / len(_2022)) - meann
            diff3 = (sum(_2022e) / len(_2022e)) - meann
            diff4 = (sum(_2080h) / len(_2080h)) - meann
            mean_diff_wbgt_2080.append((meann, diff1))
            mean_diff_wbgt_2022.append((meann, diff2))
            mean_diff_wbgt_2022e.append((meann, diff3))
            mean_diff_wbgt_2080h.append((meann, diff4))

        # Call the function for creating the Temperature plot
        #create_hottest_week_plot(temp_dict, auc_temp_dict, auc_temp_thres, archetype, zone_names,weather_folders, weather_dict, output_folder, 'Temperature', 'temp_plot', [20, 50])

        # Call the function for creating the Humidex plot
        #create_hottest_week_plot(humidex_dict, auc_humidex_dict, auc_humidex_thres, archetype, zone_names,weather_folders,weather_dict, output_folder,'Humidex', 'humidex_plot', [20,50])

        # Call the function for creating the SET plot
        #create_hottest_week_plot(set_dict, auc_set_dict, auc_set_thres, archetype, zone_names,weather_folders,weather_dict, output_folder, 'SET','set_plot', [20,40])

        # Call the function for creating the PMV plot
        #create_hottest_week_plot(pmv_dict, auc_pmv_dict, auc_pmv_thres, archetype, zone_names,weather_folders,weather_dict, output_folder, 'PMV','pmv_plot', [-6,6])

        # Call the function for creating the WBGT plot
        #create_hottest_week_plot(wbgt_dict, auc_wbgt_dict, auc_wbgt_thres, archetype, zone_names,weather_folders,weather_dict, output_folder, 'WBGT','wbgt_plot', [10,40])

        #Create a plot showing all the different thermal comfort models and the specified zones
        zones = ['KL:ZONE', 'BD:ZONE']
        tc_dicts = [temp_dict, humidex_dict, set_dict, pmv_dict, wbgt_dict]
        auc_tc_dicts = [auc_temp_dict, auc_humidex_dict, auc_set_dict, auc_pmv_dict, auc_wbgt_dict]
        tc_thres = [auc_temp_thres, auc_humidex_thres, auc_set_thres, auc_pmv_thres, auc_wbgt_thres]

        tc_ranges = {
            'Temperature': [20, 50],
            'Humidex': [20, 50],
            'SET': [20, 40],
            'PMV': [-6, 6],
            'WBGT': [10, 40]
        }

        create_combined_hottest_week_plot(tc_dicts, auc_tc_dicts, tc_thres, archetype, zones, weather_folders,weather_dict, output_folder, tc_ranges)

        #Create a bar plot showing the energy demand needed to meet a cooling setpoint
        '''
        if True in ideal_load_options:
            df2 = df.applymap(lambda x: x / 1000000000) ##note y in MJ
            x = [weather_dict['/' + item] for item in df2.index]

            #add one trace per cooling setpoint
            data = []
            ys = df2.columns
            color_scale = px.colors.sequential.Blues

            for i, y in enumerate(ys):
                y_vals=df2[y]
                trace = go.Bar(x=x, y=y_vals, name=str(y) + '\N{DEGREE SIGN} C', marker_color=color_scale[i+4])
                data.append(trace)

            color_scale = px.colors.sequential.Blues
            layout = go.Layout(barmode='group', legend=dict(title='Cooling Setpoint'), yaxis=dict(range=[0, 20],title='Energy demand (GJ)'))
            fig2 = (go.Figure(data=data, layout=layout))
            fig2.write_image(output_folder + "/energydemand_plot" + ".png", scale=5)
            fig2.update_layout(title=archetype + ': Energy demand for different weather scenarios and cooling setpoints')
            if show:
                fig2.show()
        '''

        #Show the distribution of the indoor temperature for Kitchen and Living Area for summer months (different zones are very similar)
        zone_names2 = ['KL:ZONE']
        '''
        xaxis = dict(range = [15,45], title='Temperature (\N{DEGREE SIGN}C)')
        create_dist_plot(summer_temp_dict,  archetype, zone_names2, variable_name='Temperature', xaxis=xaxis,output_folder=output_folder)

        #Show the distribution of the humidex per zone for summer months
        xaxis = dict(range = [20,50], title='Humidex')
        create_dist_plot(summer_humidex_dict, archetype, zone_names2, variable_name='Humidex', xaxis=xaxis, output_folder=output_folder)

        # Show the distribution of the SET per zone for summer months
        xaxis = dict(range=[20, 40], title='SET')
        create_dist_plot(summer_set_dict, archetype, zone_names2, variable_name='SET', xaxis=xaxis,output_folder=output_folder)

        # Show the distribution of the PMV per zone for summer months
        xaxis = dict(range=[-6, 6], title='PMV')
        create_dist_plot(summer_pmv_dict, archetype, zone_names2, variable_name='PMV', xaxis=xaxis,output_folder=output_folder)
        
        '''

        #Show the distribution of the hourly thermal comfort metrics for Kitchen and Living Area for summer months (different zones are very similar) for each archetype
        zone = 'KL:ZONE'
        create_summer_thermal_comfort_distr_plot(zone, weather_folders, temp_dict, humidex_dict, set_dict, pmv_dict, wbgt_dict, archetype, zone_dict, output_folder)

        zones = ['KL:ZONE', 'BD:ZONE']
        tc_diff_ranges = {
            'Temperature': [-10,15],
            'Humidex': [-15,25],
            'SET': [-10,15],
            'PMV': [-6, 6],
            'WBGT': [-10,15],
        }
        thermal_comfort_dict_mapping = {
            #'Temperature': temp_dict,
            'Humidex': humidex_dict,
            'SET': set_dict,
            #'WBGT': wbgt_dict,
            #'PMV': pmv_dict
        }

        create_summer_diff_distr_plot(zones, weather_folders, thermal_comfort_dict_mapping, archetype, zone_dict, output_folder, tc_diff_ranges)

    #Now we want to plot a chart showing these differences compared to the mean value
    '''
    output_folder = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Output/UK Archetypes/'
    fig = go.Figure()

    #2022 and 2080 colors
    year_diff = ['2022-TMY', '2022 extended-TMY', '2080-TMY']
    colors = ['orange','red', 'purple', 'royalblue']

    x_values_2022 = []
    y_values_2022 = []
    x_values_2022e = []
    y_values_2022e = []
    x_values_2080 = []
    y_values_2080 = []
    x_values_2080h = []
    y_values_2080h = []

    #TEMPERATURE
    # 2022-TMY
    _, y_values = zip(*mean_diff_temp_2022)
    y_values = np.asarray(y_values)
    x_values = ['Temperature']*len(y_values)
    x_values_2022.extend(x_values)
    y_values_2022.extend(y_values)

    # 2022e-TMY
    _, y_values = zip(*mean_diff_temp_2022e)
    y_values = np.asarray(y_values)
    x_values = ['Temperature'] * len(y_values)
    x_values_2022e.extend(x_values)
    y_values_2022e.extend(y_values)

    # 2080-TMY
    _, y_values = zip(*mean_diff_temp_2080)
    y_values=np.asarray(y_values)
    x_values = ['Temperature']*len(y_values)
    x_values_2080.extend(x_values)
    y_values_2080.extend(y_values)

    # 2080h-TMY
    _, y_values = zip(*mean_diff_temp_2080h)
    y_values=np.asarray(y_values)
    x_values = ['Temperature']*len(y_values)
    x_values_2080h.extend(x_values)
    y_values_2080h.extend(y_values)

    #HUMIDEX
    # 2022-TMY
    _, y_values = zip(*mean_diff_hum_2022)
    y_values = np.asarray(y_values)
    x_values = ['Humidex']*len(y_values)
    x_values_2022.extend(x_values)
    y_values_2022.extend(y_values)

    # 2022e-TMY
    _, y_values = zip(*mean_diff_hum_2022e)
    y_values = np.asarray(y_values)
    x_values = ['Humidex'] * len(y_values)
    x_values_2022e.extend(x_values)
    y_values_2022e.extend(y_values)

    # 2080-TMY
    _, y_values = zip(*mean_diff_hum_2080)
    y_values = np.asarray(y_values)
    x_values = ['Humidex']*len(y_values)
    x_values_2080.extend(x_values)
    y_values_2080.extend(y_values)

    # 2080h-TMY
    _, y_values = zip(*mean_diff_hum_2080h)
    y_values = np.asarray(y_values)
    x_values = ['Humidex']*len(y_values)
    x_values_2080h.extend(x_values)
    y_values_2080h.extend(y_values)

    # SET
    # 2022-TMY
    _, y_values = zip(*mean_diff_set_2022)
    y_values = np.asarray(y_values)
    x_values = ['SET'] * len(y_values)
    x_values_2022.extend(x_values)
    y_values_2022.extend(y_values)

    # 2022e-TMY
    _, y_values = zip(*mean_diff_set_2022e)
    y_values = np.asarray(y_values)
    x_values = ['SET'] * len(y_values)
    x_values_2022e.extend(x_values)
    y_values_2022e.extend(y_values)

    # 2080-TMY
    _, y_values = zip(*mean_diff_set_2080)
    y_values = np.asarray(y_values)
    x_values = ['SET'] * len(y_values)
    x_values_2080.extend(x_values)
    y_values_2080.extend(y_values)

    # 2080h-TMY
    _, y_values = zip(*mean_diff_set_2080h)
    y_values = np.asarray(y_values)
    x_values = ['SET'] * len(y_values)
    x_values_2080h.extend(x_values)
    y_values_2080h.extend(y_values)

    #WBGT
    # 2022-TMY
    _, y_values = zip(*mean_diff_wbgt_2022)
    y_values = np.asarray(y_values)
    x_values = ['WBGT']*len(y_values)
    x_values_2022.extend(x_values)
    y_values_2022.extend(y_values)

    # 2022e-TMY
    _, y_values = zip(*mean_diff_wbgt_2022e)
    y_values = np.asarray(y_values)
    x_values = ['WBGT'] * len(y_values)
    x_values_2022e.extend(x_values)
    y_values_2022e.extend(y_values)

    # 2080-TMY
    _, y_values = zip(*mean_diff_wbgt_2080)
    y_values = np.asarray(y_values)
    x_values = ['WBGT']*len(y_values)
    x_values_2080.extend(x_values)
    y_values_2080.extend(y_values)

    # 2080-TMY
    _, y_values = zip(*mean_diff_wbgt_2080h)
    y_values = np.asarray(y_values)
    x_values = ['WBGT']*len(y_values)
    x_values_2080h.extend(x_values)
    y_values_2080h.extend(y_values)

    #PMV
    # 2022-TMY
    _, y_values = zip(*mean_diff_pmv_2022)
    y_values = np.asarray(y_values)
    x_values = ['PMV']*len(y_values)
    x_values_2022.extend(x_values)
    y_values_2022.extend(y_values)

    # 2022e-TMY
    _, y_values = zip(*mean_diff_pmv_2022e)
    y_values = np.asarray(y_values)
    x_values = ['PMV'] * len(y_values)
    x_values_2022e.extend(x_values)
    y_values_2022e.extend(y_values)

    # 2080-TMY
    _, y_values = zip(*mean_diff_pmv_2080)
    y_values = np.asarray(y_values)
    x_values = ['PMV']*len(y_values)
    x_values_2080.extend(x_values)
    y_values_2080.extend(y_values)

    # 2080h-TMY
    _, y_values = zip(*mean_diff_pmv_2080h)
    y_values = np.asarray(y_values)
    x_values = ['PMV']*len(y_values)
    x_values_2080h.extend(x_values)
    y_values_2080h.extend(y_values)


    #Add a legend for the year differences
    for i, elem in enumerate(year_diff):
        fig.add_trace(go.Violin(
            x=[None],
            y=[None],
            legend='legend2',
            name=elem,
            fillcolor=colors[i],
            line_color=colors[i]))

    fig.update_layout(legend2=dict(yanchor="top", xanchor="center", y=-0.08, x=0.5, orientation='v', title='Year differences:'))
    
    fig.add_trace(go.Violin(x=x_values_2022, y=y_values_2022, box_visible=False, name='2022 Heatwave - Historical TMY', points='all', line_color=colors[0]))
    fig.add_trace(go.Violin(x=x_values_2022e, y=y_values_2022e, box_visible=False, name='2022 Heatwave+ - HistoricalTMY', points='all', line_color=colors[1]))
    fig.add_trace(go.Violin(x=x_values_2080, y=y_values_2080, box_visible=False, name='2080 TMY - Historical TMY', points='all', line_color=colors[2]))
    fig.add_trace(go.Violin(x=x_values_2080h, y=y_values_2080h, box_visible=False, name='2080 Heatwave- Historical TMY', points='all', line_color=colors[2]))
    fig.update_traces(meanline_visible=True)
    # Adjust Layout and save
    fig.update_layout(template='simple_white', width=1200, height=600, violinmode='group', title='Distribution of differences of mean hourly summer thermal comfort for 2022-TMY, 2022 extended-TMY and 2080-TMY for all archetypes and zones')
    fig.update_yaxes(gridcolor='lightgrey', showgrid=True)
    fig.write_image(output_folder + 'distr_diff_2080_2022_2022e' + ".png", scale=5)
    if show:
        fig.show()
    '''

    #Create one plot visualizing the Degree hours and Exceedance hours for the different weather files for all archetypes (for a particular zone)
    #make_subplots(rows=3, cols=4, shared_xaxes=True, subplot_titles=subplot_titles, y_title=y_title, vertical_spacing=0.1)
    archetypes = list(archetype_dict.values())
    output_folder = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Output/UK Archetypes/'

    eh_dh_dicts = {
        'Temperature': temperature_eh_dh_dict,
        'Humidex': humidex_eh_dh_dict,
        'PMV': pmv_eh_dh_dict,
        'SET': set_eh_dh_dict,
    }

    max_eh_dh_dicts = {
        'Humidex': humidex_max_eh_dh_dict,
        'SET': set_max_eh_dh_dict,
    }


    thres_dict = {
        'Temperature': auc_temp_thres,
        'Humidex': auc_humidex_thres,
        'PMV': auc_pmv_thres,
        'SET': auc_set_thres,
    }

    column_titles=['Degree hours', 'Exceedance hours']

    #This code creates one combined plot for the specified thermal comfort models
    thermal_models = ['Humidex', 'SET']
    zone_names = ['KL:ZONE','BD:ZONE']

    #create one for annual Dh and Eh
    ranges = [[-2000, 2000], [-700, 700]]
    create_dh_eh_combined_plot_hum_set(thermal_models,zone_names, weather_folders, eh_dh_dicts,output_folder, ranges, 'Annual', 'dh')
    create_dh_eh_combined_plot_hum_set(thermal_models, zone_names, weather_folders, eh_dh_dicts,output_folder, ranges, 'Annual', 'eh')

    #create one for summer max Dh and Eh
    ranges = [[0, 1000], [0, 600]]
    create_dh_eh_combined_plot_hum_set(thermal_models, zone_names, weather_folders, max_eh_dh_dicts, output_folder, ranges, 'Max', 'dh')
    create_dh_eh_combined_plot_hum_set(thermal_models,zone_names, weather_folders, max_eh_dh_dicts, output_folder, ranges, 'Max', 'eh')

    '''
    thermal_models = ['SET']
    zone_names = ['KL:ZONE', 'BD:ZONE']
    ranges = [[0, 250], [0, 250]]
    tc_thr = [120]
    create_dh_eh_combined_plot_hum_set(thermal_models, zone_names, weather_folders, max_eh_dh_dicts, output_folder, ranges, 'SET Max', 'dh_set', tc_thr)
    '''

    #Create a plot that plots the temperature and relative humidity for the most extreme humidex value
    zone_names = ['KL:ZONE', 'BD:ZONE']
    create_max_hum_cond_plot(max_hum_cond_dict, zone_names, weather_folders, output_folder)


    #This code creates one plot per thermal model
    thermal_models = ['Temperature', 'Humidex', 'PMV', 'SET']
    '''
    for thermal_model in thermal_models:

        eh_dh_dict = eh_dh_dicts[thermal_model]

        for j, zone in enumerate(zone_names):
            fig = make_subplots(2, 1, shared_xaxes=True, subplot_titles=subplot_titles, vertical_spacing=0.2)
            for i, weather_folder in enumerate(weather_folders):
                yvals_dh= []
                yvals_eh = []
                for archetype in archetypes:
                    eh_dh_dict_arch = eh_dh_dict[zone][archetype]
                    (auc_val, days_over) = eh_dh_dict_arch[weather_folder]
                    yvals_dh.append(auc_val)
                    yvals_eh.append(days_over)

                fig.add_trace(go.Bar(name=weather_dict[weather_folder], x=archetypes, y=yvals_dh, marker_color=colors[i]), row=1, col=1)
                fig.add_trace(go.Bar(name=weather_dict[weather_folder], x=archetypes, y=yvals_eh, marker_color=colors[i], showlegend=False), row=2, col=1)

            fig.update_layout(template='simple_white', width=1200, height=600, title=thermal_model + ': Degree hours and Exceedance hours over ' + str(thres_dict[thermal_model]) + ' per archetype for ' + zone_dict[zone])
            fig.update_layout(yaxis=dict(range=[0,1800]),yaxis2=dict(range=[0,700]))
            fig.write_image(output_folder + thermal_model + '_dh_eh_' + zone_dict[zone] + ".png", scale=5)
            fig.show()

    '''

def calculate_humidex(temperature, humidity):
    # Constants for the humidex calculation
    # You can adjust this formula based on the specific humidex calculation you're using
    e = 6.112 * np.exp(17.67 * temperature / (temperature + 243.5)) * humidity / 100
    humidex = temperature + (5/9) * (e - 10)
    return humidex

def create_max_hum_cond_plot(max_hum_cond_dict, zone_names, weather_folders, output_folder):

    fig = go.Figure()
    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

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
                             contours=dict(start=29, end=54, size=1, coloring='heatmap'), line=dict(color='black', width=0)))
                             #colorbar=dict(tickvals=[29,39,45,54], ticktext=['low', 'med', 'high', 'extreme'], len=.8)))

    fig.add_trace(go.Contour(x=temperature,y=humidity,z=humidex_grid,showscale=False,contours=dict(type='constraint',operation='=',value=29),
                            line=dict(color='grey', width=2), showlegend=False))

    fig.add_trace(go.Contour(x=temperature,y=humidity,z=humidex_grid,showscale=False,contours=dict(type='constraint',operation='=',value=39),
                            line=dict(color='grey', width=2), showlegend=False))

    fig.add_trace(go.Contour(x=temperature,y=humidity,z=humidex_grid,showscale=False,contours=dict(type='constraint',operation='=',value=45),
                            line=dict(color='grey', width=2), showlegend=False))

    fig.add_trace(go.Contour(x=temperature,y=humidity,z=humidex_grid,showscale=False,contours=dict(type='constraint',operation='=',value=54),
                            line=dict(color='grey', width=2), showlegend=False))

    # Update layout with annotations
    fig.update_layout(
        title="Temperature vs Humidity with Humidex Comfort Levels",
        xaxis_title="Temperature (\N{DEGREE SIGN}C)",
        yaxis_title="Humidity (%)",
    )

    archetype_mapping = {
        "Ground floor flat":  'triangle-down-open',
        "Mid floor flat": 'triangle-right-open',
        "Top floor flat": 'triangle-up-open',
        "Mid terrace (Solid/suspended)": 'square',
        "Mid terrace (Cavity/solid)": 'square-open',
        "Medium house, solid (semi-d)": 'diamond',
        "Compact house (semi-d)": 'diamond-open',
        "Bungalow (detached)": 'hexagon-open',
        "Sprawling, solid (detached)": 'circle',
        "Sprawling house, cavity (detached)": 'circle-open'
    }

    #I want to plot Flats (G, M, T), Terraced (S, C), Semi-Detached (S, C), and Detached (B, S, C)
    symbols = ['triangle-down', 'triangle-right', 'triangle-up', 'square', 'square-open', 'diamond', 'diamond-open', 'hexagon-open', 'circle', 'circle-open']
    symbols = []

    for k, weather_folder in enumerate(weather_folders):
        temp = []
        rh = []
        text = []
        hum = []

        for i, zone in enumerate(zone_names):
            max_cond_arr = max_hum_cond_dict[zone][weather_folder]

            idx=0

            for elem in max_cond_arr:

                (archetype, max_hum, max_hum_temp, max_hum_rh) = elem

                if archetype not in archetype_mapping:
                    continue

                if i == 0:
                    symbols.append(archetype_mapping[archetype])
                    temp.append(max_hum_temp)
                    rh.append(max_hum_rh)
                    hum.append(max_hum)

                elif max_hum > hum[idx]:
                    temp[idx] = max_hum_temp
                    rh[idx] = max_hum_rh
                    hum[idx] = max_hum

                idx+=1

        #fig.add_trace(go.Scatter(x=temp, y=rh, text=text, name=weather_dict[weather_folder], marker_color= colors[k], marker_symbol=symbols, mode="markers+text", textposition="top center", textfont=dict(color=colors[k])))
        fig.add_trace(go.Scatter(x=temp, y=rh, name=weather_dict[weather_folder], marker_color=colors[k],marker_symbol=symbols, marker=dict(size=12, line=dict(width=2, color=colors[k])), mode="markers+text", textposition="top center",textfont=dict(color=colors[k]), showlegend=False))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=weather_dict[weather_folder], legendgrouptitle_text="Weather scenario", legendgroup='group1', marker=dict(size=7, color=colors[k], symbol='square', line=dict(width=2, color=colors[k]))))

    #Construction material
    fig.add_trace(go.Scatter(x=[None],y=[None],mode="markers",name="Solid",legendgrouptitle_text="Construction", legendgroup='group3',marker=dict(size=7, color="black", symbol='square', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None],y=[None],mode="markers",name="Cavity", legendgrouptitle_text="Construction",legendgroup='group3',marker=dict(size=7, color="black", symbol='square-open', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Top Floor", legendgrouptitle_text="Construction",legendgroup='group3', marker=dict(size=7, color="grey", symbol='triangle-up', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Mid Floor", legendgrouptitle_text="Construction",legendgroup='group3',marker=dict(size=7, color="grey", symbol='triangle-right', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Ground Floor", legendgrouptitle_text="Construction",legendgroup='group3',marker=dict(size=7, color="grey", symbol='triangle-down', line=dict(width=2, color='black'))))

    #Archetype
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Flat", legendgrouptitle_text="Archetype", legendgroup='group2', marker=dict(size=7, color="grey", symbol='triangle-right', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Terraced", legendgrouptitle_text="Archetype", legendgroup='group2',marker=dict(size=7, color="grey", symbol='square', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Semi-detached", legendgrouptitle_text="Archetype", legendgroup='group2',marker=dict(size=7, color="grey", symbol='diamond', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Bungalow (detached)", legendgrouptitle_text="Archetype", legendgroup='group2',marker=dict(size=7, color="grey", symbol='hexagon', line=dict(width=2, color='black'))))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Sprawling (detached)", legendgrouptitle_text="Archetype", legendgroup='group2',marker=dict(size=7, color="grey", symbol='circle', line=dict(width=2, color='black'))))


    fig.update_layout(template='simple_white', width=1200, height=900) #margin=dict(r=300),
    fig.update_xaxes( gridcolor='lightgrey', showgrid=True, range=[25,45], title='Dry Bulb Temperature (\N{DEGREE SIGN}C)')
    fig.update_yaxes( gridcolor='lightgrey', showgrid=True, range=[0,100], title='Relative Humidity (%)')


    color_scale_labels = ['<29: No discomfort', '30-39: Some discomfort', '40-45: Great discomfort; avoid exertion', '45-54: Dangerous', '>54: Heat stroke imminent']

    for i, (_,color) in enumerate(pastel_colorscale):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=color_scale_labels[i],
                             legendgrouptitle_text="Humidex range", legendgroup='group4',
                             marker=dict(size=12, color=color, symbol='square')))

    fig.write_image(output_folder + 'peak_humidex_plot' + ".png", scale=5)
    fig.show()


#same as create create_dh_eh_combined_plot but it only shows the Degree hours and uses the zones as columns
def create_dh_eh_combined_plot_hum_set(thermal_models,zone_names, weather_folders, eh_dh_dicts, output_folder, ranges, name, type,  tc_thr=None):

    archetypes = ["Ground floor flat",
        "Mid floor flat",
        "Top floor flat",
        "Mid terrace (Solid/suspended)",
        "Mid terrace (Cavity/solid)",
        "Medium house, solid (semi-d)",
        "Compact house (semi-d)",
        "Bungalow (detached)",
        "Sprawling, solid (detached)",
        "Sprawling house, cavity (detached)"]

    archetypes_plot = [
                  ["<b>Flat<b>",
                  "<b>Flat<b>",
                  "<b>Flat<b>",
                  "<b>Terraced<b>",
                  "<b>Terraced<b>",
                  "<b>Semi-detached<b>",
                  "<b>Semi-detached<b>",
                  "<b>Detached<b>",
                  "<b>Detached<b>",
                  "<b>Detached<b>"],
                  ["Ground",
                   "Mid",
                    "Top",
                     "Solid",
                     "Cavity",
                     "Solid",
                     "Cavity",
                     "Bungalow",
                     "Solid",
                     "Cavity"]
    ]

    nr_rows=1
    nr_cols=len(zone_names)
    colors = ['green', 'orange', 'red', 'purple', 'royalblue']
    clip_val = 2000

    column_names = [zone_dict[item] for item in zone_names]

    fig = make_subplots(rows=nr_rows, cols=nr_cols, column_titles=column_names, shared_xaxes=True, vertical_spacing=0.1)

    for i, thermal_model in enumerate(thermal_models):
        eh_dh_dict = eh_dh_dicts[thermal_model]

        for j, zone in enumerate(zone_names):

            for k, weather_folder in enumerate(weather_folders):
                yvals_dh = []
                yvals_eh = []

                for archetype in archetypes:
                    eh_dh_dict_arch = eh_dh_dict[zone][archetype]
                    (auc_val, days_over) = eh_dh_dict_arch[weather_folder]
                    yvals_dh.append(auc_val)
                    yvals_eh.append(days_over)

                if i == 0 and j ==0:
                    showlegend = True
                else:
                    showlegend = False

                y = np.clip(yvals_dh, 0, clip_val)

                if thermal_model == 'SET':
                    y =  [ -x for x in y]
                    yvals_eh = [ -x for x in yvals_eh]

                if type=='dh' or type =='dh_set':
                    fig.add_trace(go.Bar(name=weather_dict[weather_folder], x=archetypes_plot, y=y, marker_color=colors[k],showlegend=showlegend, offsetgroup=k),row=1, col=j+1)
                else:
                    fig.add_trace(go.Bar(name=weather_dict[weather_folder], x=archetypes_plot, y=yvals_eh, marker_color=colors[k],showlegend=showlegend, offsetgroup=k),row=1, col=j+1)

                for ii, yy in enumerate(yvals_dh):
                    if yy > 2000:
                        y_plot = 2100
                        if thermal_model == 'SET':
                            y_plot = -y_plot
                        fig.add_annotation(x=[archetypes_plot[0][ii], archetypes_plot[1][ii]], xshift=22, y=y_plot, text=str(int(yy)), row=1, col=j+1, font=dict(size=10,color=colors[k]), showarrow=False)


    model_string = ', '.join(thermal_models)

    if type == 'dh' or type =='dh_set':
        range = ranges[0]
        title = name + ' Degree hours over thresholds per archetype'
        if type == 'dh_set':
            fig.add_hline(y=tc_thr[0], row=1, col=1, line_width=1.5, line_dash="dash", line_color='black', opacity=1)
            fig.add_hline(y=tc_thr[0], row=1, col=2, line_width=1.5, line_dash="dash", line_color='black', opacity=1)
    else:
        range = ranges[1]
        title = name + ' Exceedance hours over thresholds per archetype'


    fig.update_layout(template='simple_white', width=1800, height=900, title=model_string + ': ' + title, legend = dict(yanchor="top", xanchor="center", y=-0.12, x=0.5, orientation='h', title='Weather scenarios:'))

    range2 = [range[0]-200, range[1]+200]
    fig.update_yaxes(title=25*' ' + 'SET' + 60*' ' + 'Humidex', range=range2, row=1, col=1)
    fig.update_yaxes(title='', range=range2, row=1, col=2)
    y_ticks = np.arange(range[0], range[1]+1, 500)
    fig.update_yaxes(tickvals=y_ticks,ticktext=np.abs(y_ticks), gridcolor='lightgrey', showgrid=True)

    fig.update_xaxes(linecolor='lightgrey')

    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="black", opacity=1)

    #fig.add_hline(x0=0.5,x1=0.55,y=-0.07,annotation=dict(text="Flats"), line_color="black")

    #fig.add_annotation(text='Flats',yanchor="top", xanchor="center",showarrow=False,xref='paper',yref='paper',x=0.01,y=-0.07)

    fig.write_image(output_folder + name + '_' + type + ".png", scale=5)
    fig.show()


##NOTE: does not work yet!!
def create_dh_eh_combined_plot(thermal_models, zone_names, weather_folders, eh_dh_dicts, archetypes, output_folder, ranges, name):

    nr_rows = len(thermal_models)
    nr_cols = len(zone_names)
    #colors_dh = ['green', 'orange', 'red', 'purple', 'royalblue']
    #colors_eh = ['lightgreen', 'yellow', 'orangered', 'lavender', 'lightblue']

    # Define colors for the weather files and dh/eh combinations
    colors = {
        'Historical TMY': {
            "Eh": "lightgreen",
            "Dh": "green"
        },
        '2022 Heatwave': {
            "Eh": "yellow",
            "Dh": "orange"
        },
        '2022 Heatwave+': {
            "Eh": "orangered",
            "Dh": "red"
        },
        '2080 TMY': {
            "Eh": "lavender",
            "Dh": "purple"
        },
        '2080 Heatwave': {
            "Eh": "lightblue",
            "Dh": "royalblue"
        }
    }

    keys = list(colors.keys())

    column_names = [zone_dict[item] for item in zone_names]

    fig = make_subplots(rows=nr_rows, cols=nr_cols, column_titles=column_names, shared_xaxes=True, vertical_spacing=0.1,
    figure=go.Figure(layout=go.Layout(barmode='relative', yaxis2=go.layout.YAxis(visible=False,matches="y",overlaying="y",anchor="x"),
                                      yaxis3=go.layout.YAxis(visible=False,matches="y",overlaying="y",anchor="x"),
                                      yaxis4=go.layout.YAxis(visible=False,matches="y",overlaying="y",anchor="x"),
                                      yaxis5=go.layout.YAxis(visible=False,matches="y",overlaying="y",anchor="x"))))


    for i, thermal_model in enumerate(thermal_models):
        eh_dh_dict = eh_dh_dicts[thermal_model]

        for j, zone in enumerate(zone_names):

            df_total = pd.DataFrame()

            for k, weather_folder in enumerate(weather_folders):

                yvals_dh_diff = []
                yvals_eh = []

                for archetype in archetypes:
                    eh_dh_dict_arch = eh_dh_dict[zone][archetype]
                    (auc_val, days_over) = eh_dh_dict_arch[weather_folder]
                    yvals_dh_diff.append(auc_val-days_over) #difference between dh and eh for the plot
                    yvals_eh.append(days_over)

                if i == 0 and j == 0:
                    showlegend = True
                else:
                    showlegend = False

                data = np.transpose([yvals_eh, yvals_dh_diff])
                col = pd.DataFrame(data, index=archetypes, columns=['Eh', 'Dh'])
                df_total = pd.concat([df_total, col], axis=1, keys=keys[:k+1])

            for ii, t in enumerate(colors):
                for jj, col in enumerate(df_total[k].columns):
                    if (df_total[t][col] == 0).all():
                        continue

                    fig.add_trace(go.Bar(name=weather_dict[weather_folder], x=archetypes, y=df_total[t][col],yaxis=f"y{ii + 1}", offsetgroup=str(ii), offset=(ii - 1) * 1000000000, width=1000000000, legendgroup=t,
                     legendgrouptitle_text=t, marker_color=colors[t][col]), row=i + 1, col=j + 1)

            #fig.add_trace(go.Bar(name=weather_dict[weather_folder] + 'eh', x=archetypes, y=yvals_eh, marker_color=colors_eh[k],showlegend=False), row=i + 1, col=j + 1)
            #fig.add_trace(go.Bar(name=weather_dict[weather_folder], x=archetypes, y=yvals_dh_diff, marker_color=colors_dh[k],showlegend=showlegend), row=i + 1, col=j + 1)

    model_string = ', '.join(thermal_models)
    title = name + ' Comparison of annual Degree hours and Exceedance hours across archetypes'

    fig.update_layout(template='simple_white', width=1200, height=600, title=model_string + ': ' + title)
    fig.show()

    fig.write_image(output_folder + name + '_dh_eh_all_arch'  + ".png", scale=5)


def create_summer_diff_distr_plot(zones, weather_folders, thermal_comfort_dict_mapping, archetype, zone_dict, output_folder, tc_ranges):

    colors = ['green', 'orange', 'red', 'purple', 'royalblue']
    thermal_models = list(thermal_comfort_dict_mapping.keys())
    nr_rows = len(thermal_models)

    #Add the x-axis zone titles on top
    nr_cols = len(zones)
    xx = 70
    subplot_title= zone_dict[zones[0]]
    for i in range(nr_cols-1):
        subplot_title += xx*" " + zone_dict[zones[i+1]]
    subplot_title += 10*" "

    fig = make_subplots(rows=nr_rows, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=[subplot_title])

    tc_y = [-13, -7]
    x_shifts = [-135, -45, 45, 135]
    x_shift_mean = -210

    for i, model in enumerate(thermal_models):
        model_dict = thermal_comfort_dict_mapping[model]
        y_array_tmy = []
        y_tmy_means = []

        for zone in zones:
            y_values = model_dict[zone]["/Haringey_TMY"]
            y_tmy_means.append(np.mean(y_values))
            y_array_tmy.extend(y_values)

        for j, weather_folder in enumerate(weather_folders):
            if weather_folder == "/Haringey_TMY":
                continue
            weather_name = weather_dict[weather_folder]

            x_array = []
            y_array = []
            y_means = []

            for k, zone in enumerate(zones):
                y_values = model_dict[zone][weather_folder]
                y_means.append(np.mean(y_values) - y_tmy_means[k])
                x_array.extend([zone_dict[zone]] * len(y_values))
                y_array.extend(y_values)

            y_array = np.subtract(y_array,y_array_tmy)

            if i == 0:
                showlegend=True
            else:
                showlegend = False

            fig.add_trace(go.Violin(x=x_array, y=y_array, box_visible=False, name=weather_name+' - Historical TMY', line_color=colors[j], showlegend=showlegend, offsetgroup=j), row=i+1, col=1)

            for k, zone in enumerate(zones):
                x_val = zone_dict[zone]
                y_val = round(y_means[k], 1)
                fig.add_annotation(x=x_val, xshift=x_shifts[j - 1], y=tc_y[i], text=str(y_val), row=i + 1, col=1,font=dict(color=colors[j]), showarrow=False)
                if k == 0 and j == 1:
                    fig.add_annotation(x=x_val, xshift=x_shift_mean, y=tc_y[i], text='mean:', row=i+1, col=1, font=dict(color='black'), showarrow=False)

    fig.update_traces(meanline_visible=True)

    fig.update_layout(template='simple_white', width=1200, height=900, violinmode='group',
                      title=archetype + ': Distribution of hourly summer thermal comfort model values')

    for k, tc_model in enumerate(thermal_models):
        yaxis_nr = 'yaxis' + str(k+1)
        tc_range = tc_ranges[tc_model]
        fig['layout'][yaxis_nr].update(title=thermal_models[k], range=tc_range)

    fig.update_xaxes(linecolor='lightgrey', showticklabels=False, ticks="")
    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="black", opacity=1)
    fig.update_yaxes(gridcolor='lightgrey', showgrid=True)

    fig.update_layout(legend=dict(yanchor="top", xanchor="center", y=-0.08, x=0.5, orientation='h', title='Weather scenarios:'))

    fig.write_image(output_folder + '/thermal_comfort_diff' + ".png", scale=5)

    if show:
        fig.show()

def create_summer_thermal_comfort_distr_plot(zone, weather_folders, temp_dict, humidex_dict, set_dict, pmv_dict, wbgt_dict, archetype, zone_dict, output_folder):
    x_values_tmy = []
    y_values_tmy = []
    x_values_2022 = []
    y_values_2022 = []
    x_values_2022e = []
    y_values_2022e = []
    x_values_2080 = []
    y_values_2080 = []
    x_values_2080h = []
    y_values_2080h = []

    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    weather_folder_mapping = {
        "/Haringey_TMY": {"x_values": x_values_tmy, "y_values": y_values_tmy},
        "/Haringey_2022_Historical": {"x_values": x_values_2022, "y_values": y_values_2022},
        "/Haringey_2022_Extended_7": {"x_values": x_values_2022e, "y_values": y_values_2022e},
        "/Haringey_2080": {"x_values": x_values_2080, "y_values": y_values_2080},
        "/Haringey_2080_Heatwave": {"x_values": x_values_2080h, "y_values": y_values_2080h}
    }

    for weather_folder in weather_folders:
        x_array = weather_folder_mapping[weather_folder]["x_values"]
        y_array = weather_folder_mapping[weather_folder]["y_values"]

        y_values = temp_dict[zone][weather_folder]
        x_array.extend(['Temperature'] * len(y_values))
        y_array.extend(y_values)

        y_values = humidex_dict[zone][weather_folder]
        x_array.extend(['Humidex'] * len(y_values))
        y_array.extend(y_values)

        y_values = set_dict[zone][weather_folder]
        x_array.extend(['SET'] * len(y_values))
        y_array.extend(y_values)

        y_values = wbgt_dict[zone][weather_folder]
        x_array.extend(['WBGT'] * len(y_values))
        y_array.extend(y_values)

        y_values = pmv_dict[zone][weather_folder] + 25  # add an offset of 25 and then a second y-axis for PMV
        x_array.extend(['PMV'] * len(y_values))
        y_array.extend(y_values)


    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Violin(x=x_values_tmy, y=y_values_tmy, box_visible=False, name='Historical TMY', line_color=colors[0]))
    fig.add_trace(go.Violin(x=x_values_2022, y=y_values_2022, box_visible=False, name='2022 Heatwave', line_color=colors[1]))
    fig.add_trace(go.Violin(x=x_values_2022e, y=y_values_2022e, box_visible=False, name='2022 Heatwave+', line_color=colors[2]))
    fig.add_trace(go.Violin(x=x_values_2080, y=y_values_2080, box_visible=False, name='2080 TMY', line_color=colors[3]))
    fig.add_trace(go.Violin(x=x_values_2080h, y=y_values_2080h, box_visible=False, name='2080 Heatwave', line_color=colors[4]))

    fig.add_trace(go.Violin(x=[None], y=[None], name="Dummy Data", showlegend=False), secondary_y=True)

    fig.update_traces(meanline_visible=True)
    # Adjust Layout and save
    fig.update_layout(template='simple_white', width=1200, height=600, violinmode='group',
                      title=archetype + ': Distribution of hourly summer thermal comfort model values for ' +
                            zone_dict[zone])
    fig.update_xaxes(title='Thermal Comfort Model')
    fig.update_yaxes(title='Temperature, Humidex, SET, WBGT (\N{DEGREE SIGN}C)', secondary_y=False, range=[10, 50],
                     gridcolor='lightgrey', showgrid=True)
    fig.update_yaxes(title='PMV', secondary_y=True, overlaying='y', side='right', range=[-15, 25])
    fig.write_image(output_folder + '/thermal_comfort' + ".png", scale=5)

    if show:
        fig.show()

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

def create_combined_hottest_week_plot(tc_dicts, archetype, zone_names, weather_folders, weather_dict, output_folder, tc_ranges):

    x_values = np.arange(1, 21 * 24 + 1)

    rows = len(tc_dicts)
    cols = len(zone_names)

    column_titles = [zone_dict[elem] for elem in zone_names]
    row_titles = list(tc_ranges.keys())

    fig = make_subplots(rows=rows, cols=cols, shared_xaxes=True, column_titles = column_titles, vertical_spacing=0.05)

    for k, tc_model in enumerate(row_titles):
        tc_dict = tc_dicts[k]
        auc_tc_dict = auc_tc_dicts[k]
        tc_thr = tc_thres[k]
        tc_range = tc_ranges[tc_model]

        yaxis_nr = 'y' + str(k + 1)

        for j, zone in enumerate(zone_names):
            values = tc_dict[zone]

            colors = ['green', 'orange', 'red', 'purple', 'royalblue']

            for i, weather_folder in enumerate(weather_folders):
                (auc_val, days_over) = auc_tc_dict[zone][weather_folder]
                line_name = str(int(auc_val)) + ' (' + str(days_over) + ')'
                y_values = values[weather_folder]
                line_dash = 'solid'

                fig.add_trace(go.Scatter(x=x_values, y=y_values, xaxis="x1", line_dash=line_dash, name=line_name,
                                        line=dict(color=colors[i]), legendgroup=str(k + 1)), row=k + 1, col=j+1)

            fig.add_hline(y=tc_thr, row=k + 1, col=j+1, line_width=1.5, line_dash="dash", line_color='black', opacity=1)

    # to update x-axis
    x_values = x_values[::24]

    # to update x-axis
    ticktext = 21 * ['']
    ticktext[3] = '     Hottest Week - 1'
    ticktext[10] = '      Hottest Week'
    ticktext[17] = '      Hottest Week + 1'

    fig.update_xaxes(tickvals=x_values, ticktext=ticktext)

    fig.update_layout(title=archetype + f': Thermal comfort of hottest summer weeks for different weather scenarios and thermal comfort models',
                      width=1500, height=900, legend_tracegroupgap=70, template='simple_white',
                      legend_title_text=f'Degree hours (Exceedance hours) over threshold')

    fig.update_yaxes(gridcolor='lightgrey',showgrid=True)

    for k, tc_model in enumerate(row_titles):
        yaxis_nrl = 'yaxis' + str(2*k+1)
        yaxis_nrr = 'yaxis' + str(2*k+2)

        tc_range = tc_ranges[tc_model]
        fig['layout'][yaxis_nrl].update(title=row_titles[k], range=tc_range)
        fig['layout'][yaxis_nrr].update(title='', range=tc_range)

    fig.add_vline(x=7 * 24, line_width=1, line_color='black', opacity=1)
    fig.add_vline(x=14 * 24, line_width=1, line_color='black', opacity=1)

    # Add a legend for the weather scenarios
    for i, weather_folder in enumerate(weather_folders):
        line_dash = 'solid'
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            line_dash=line_dash,
            mode="lines",
            legend='legend2',
            name=weather_dict[weather_folder],
            line=dict(color=colors[i])))

    fig.update_layout(
        legend2=dict(yanchor="top", xanchor="center", y=-0.08, x=0.5, orientation='h', title='Weather scenarios:'))


    # Write the image and show the plot
    fig.write_image(output_folder + '/tc_hottest_weeks' + ".png", scale=5)

    fig.show()




def create_hottest_week_plot(y_values_dict, auc_dict, auc_thres, archetype, zone_names, weather_folders, weather_dict, output_folder, y_title, plot_filename, y_range):
    subplot_titles = [zone_dict[elem] for elem in zone_names]
    x_values = np.arange(1, 21 * 24 + 1)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=subplot_titles, y_title=y_title,
                        vertical_spacing=0.1)
    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    for j, zone in enumerate(zone_names):
        values = y_values_dict[zone]

        for i, weather_folder in enumerate(weather_folders):
            (auc_val, days_over) = auc_dict[zone][weather_folder]
            line_name = str(int(auc_val)) + ' (' + str(days_over) + ')'
            y_values = values[weather_folder]
            line_dash = 'solid'
            fig.add_trace(go.Scatter(x=x_values, y=y_values, xaxis="x1", yaxis="y1", line_dash=line_dash, name=line_name,
                                    line=dict(color=colors[i]), legendgroup=str(j + 1)), row=j + 1, col=1)

        fig.add_hline(y=auc_thres, row=j + 1, col=1, line_width=1.5, line_dash="dash", line_color='black', opacity=1)

    # to update x-axis
    x_values = x_values[::24]

    # to update x-axis
    ticktext = 21 * ['']
    ticktext[3] = '     Hottest Week - 1'
    ticktext[10] = '      Hottest Week'
    ticktext[17] = '      Hottest Week + 1'

    fig.update_xaxes(tickvals=x_values, ticktext=ticktext)

    fig.update_layout(title=archetype + f': {y_title} of hottest summer weeks for different weather scenarios',
                      width=1200, height=600, legend_tracegroupgap=70, template='simple_white',
                      legend_title_text=f'Degree hours (Exceedance hours) over {str(auc_thres)}')

    fig.update_yaxes(gridcolor='lightgrey',showgrid=True)

    fig.add_vline(x=7 * 24, line_width=1, line_color='black', opacity=1)
    fig.add_vline(x=14 * 24, line_width=1, line_color='black', opacity=1)

    # Add a legend for the weather scenarios
    for i, weather_folder in enumerate(weather_folders):
        line_dash = 'solid'
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            line_dash=line_dash,
            legend='legend2',
            name=weather_dict[weather_folder],
            line=dict(color=colors[i])))

    fig.update_layout(
        legend2=dict(yanchor="top", xanchor="center", y=-0.08, x=0.5, orientation='h', title='Weather scenarios:'))

    # Set the y-axis range
    fig.update_yaxes(range=y_range)

    # Write the image and show the plot
    fig.write_image(output_folder + f'/{plot_filename}' + ".png", scale=5)

    if show:
        fig.show()



#Given a dictionary of values for each weather file, create a plot comparing the distributions for that variable across the weather scenarios for the specified zones
def create_dist_plot(data_dict, archetype, zone_names, variable_name, xaxis, output_folder):

    nr_plots = len(zone_names)
    subplot_titles = [zone_dict[elem] for elem in zone_names]

    fig = make_subplots(rows=nr_plots, cols=1, shared_xaxes=True, subplot_titles=subplot_titles,
                        vertical_spacing=0.1, x_title=xaxis['title'])

    colors = ['green', 'orange', 'red', 'purple', 'royalblue']

    for i, zone in enumerate(zone_names):

        summer_data = data_dict[zone]
        key_names = list(summer_data.keys())
        names = [weather_dict[item] for item in key_names]
        hist_data = list(summer_data.values())

        for j in range(5):
            fig.add_trace(go.Violin(x=[names[j]]*len(hist_data[j]), y=hist_data[j], box_visible=False, name=names[j], points='all',line_color=colors[j]), row=i+1, col=1)

    fig.update_traces(meanline_visible=True)

    fig.update_layout(template='simple_white', width=1200, height=600, violinmode='group', yaxis=dict(range=xaxis['range']),
                      title=archetype + ': ' + 'Distribution of hourly summer temp archetypes and zones')
    fig.update_yaxes(gridcolor='lightgrey', showgrid=True)
    fig.write_image(output_folder + "/" + variable_name + "_distribution_" + ".png", scale=5)

    if show:
        fig.show()


#Identify most extreme (mean) week for the variable of interest
def find_most_extreme_week(housing_data):

    # Initialize variables for tracking the hottest week
    extreme_week = housing_data[0:7 * 24]
    mean_extreme_week = extreme_week.mean()  # Initialize with the mean of the first week
    current_week_start = 0  # Index of the first day in the current 7-day window

    for i in range(7 * 24, len(housing_data), 24):        # Calculate the mean temperature for the next 7 days
        current_week_mean = housing_data[i - 7 * 24:i].mean()

        # Check if the current mean is greater than the current hottest week mean
        if current_week_mean > mean_extreme_week:
            mean_extreme_week = current_week_mean
            current_week_start = i - 7 * 24  # Update the start index of the hottest week

    current_week_end =  current_week_start + 7 * 24

    #we want to visualize the hottest week with its previous and succeeding week
    time_start = current_week_start -7*24
    time_end=current_week_end + 7*24

    extreme_weeks = housing_data[time_start:time_end]

    return (time_start, time_end), extreme_weeks


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

#for testing
if __name__ == '__main__':

    '''
    fig = make_subplots(rows=1, cols=2, shared_xaxes=True, vertical_spacing=0.1)

    fig.update_layout(template='simple_white', width=1600, height=600)

    archetypes = [
                  ["Flat",
                  "Flat",
                  "Flat",
                  "Terraced",
                  "Terraced",
                  "Semi-detached",
                  "Semi-detached",
                  "Detached",
                  "Detached",
                  "Detached"],
                  ["Ground",
                   "Mid",
                    "Top",
                     "Solid",
                     "Cavity",
                     "Solid",
                     "Cavity",
                     "Bungalow",
                     "Solid",
                     "Cavity"]
    ]

    fig.add_trace(go.Bar(x=archetypes, y= [1,2,3,7,5,6,2,10,12,5]))

    range=[-2000, 2000]


    fig.update_xaxes(linecolor='lightgrey')

    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="black", opacity=1)

    # fig.add_hline(x0=0.5,x1=0.55,y=-0.07,annotation=dict(text="Flats"), line_color="black")

    # fig.add_annotation(text='Flats',yanchor="top", xanchor="center",showarrow=False,xref='paper',yref='paper',x=0.01,y=-0.07)
    fig.show()

    '''
    '''
    #do some testing for my maximum humidex conditions plot

    max_hum_cond_dict = {
        "KL:ZONE": {
            '/Haringey_2080': [('Ground floor flat', 50, 20, 30), ('Mid floor flat', 50, 20, 20)],
            '/Haringey_2080_Heatwave': [('Ground floor flat', 50, 40, 40), ('Mid floor flat', 50, 30, 30)]
        },
        "BD:ZONE": {
            '/Haringey_2080': [('Ground floor flat', 60, 30, 30), ('Mid floor flat', 60, 30, 30)],
            '/Haringey_2080_Heatwave': [('Ground floor flat', 50, 40, 40), ('Mid floor flat', 50, 30, 30)]

        },
        "OT:ZONE": {}
    }

    weather_folders = ['/Haringey_2080', '/Haringey_2080_Heatwave']
    zone_names = ['KL:ZONE', 'BD:ZONE']
    folder = ''
    create_max_hum_cond_plot(max_hum_cond_dict, zone_names, weather_folders, folder)

    '''


    temperature = 18.27
    v = 1.4
    rel_humidity = 36.77

    mrt = 42.9

    wbt = calculate_wbt(temperature + 273.15, rel_humidity) - 273.15
    gt = calculate_bgt(temperature + 273.15, mrt + 273.15, v) - 273.15

    wbgt = 0.7*wbt + 0.3*gt
    print(humidex(temperature, rel_humidity))