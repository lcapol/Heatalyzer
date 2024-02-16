##Functions for creating extreme weather scenarios
import pandas as pd
from .epw import epw

epw_cols = ['Year','Month','Day','Hour','Minute','Data Source and Uncertainty Flags','Dry Bulb Temperature','Dew Point Temperature','Relative Humidity',
'Atmospheric Station Pressure','Extraterrestrial Horizontal Radiation','Extraterrestrial Direct Normal Radiation','Horizontal Infrared Radiation Intensity',
'Global Horizontal Radiation','Direct Normal Radiation','Diffuse Horizontal Radiation','Global Horizontal Illuminance','Direct Normal Illuminance',
'Diffuse Horizontal Illuminance','Zenith Luminance','Wind Direction','Wind Speed','Total Sky Cover','Opaque Sky Cover (used if Horizontal IR Intensity missing)',
'Visibility','Ceiling Height','Present Weather Observation','Present Weather Codes','Precipitable Water','Aerosol Optical Depth','Snow Depth','Days Since Last Snowfall',
'Albedo','Liquid Precipitation Depth','Liquid Precipitation Quantity']

# Function to find the hottest day in summer
def find_hottest_summer_day(epw_data):
    # Extract the temperature data
    temperature_data = epw_data['Dry Bulb Temperature']

    # Extract the month and day columns
    month = epw_data['Month']
    day = epw_data['Day']

    # Find the index of the hottest hour in summer
    hottest_hour_index = temperature_data.idxmax()

    # Extract the date of the hottest day
    hottest_month = month[hottest_hour_index]
    hottest_day = day[hottest_hour_index]

    return hottest_month, hottest_day

##Take a weather file, determine the hottest day of the year and prolong its length to last heat_length days.
#Hearby the day with peak temperature is replicated and replaces the data in the following days
def extend_heatwave(input_file, output_file, heat_length):

    #Load the EPW file

    file = epw()
    file.read(input_file)
    epw_data = file.dataframe
    file_len = len(epw_data)

    #Find the hottest day in summer (hottest in terms of highest temperature peak)
    hottest_month, hottest_day = find_hottest_summer_day(epw_data)
    hottest_data = epw_data[(epw_data['Month'] == hottest_month) & (epw_data['Day'] == hottest_day)]
    #Find the index of the hottest day
    hottest_day_index = hottest_data.index[0]

    heatwave = hottest_data.copy()

    #Create heatwave, which is heat_length * the data of the hottest day
    for i in range(heat_length-1):

        new_next_hot_day = hottest_data.copy()
        new_next_hot_day['Month'] = epw_data['Month'][(hottest_day_index + 24*(i+1)) % file_len]
        new_next_hot_day['Day'] = epw_data['Day'][(hottest_day_index + 24*(i+1)) % file_len]

        heatwave = pd.concat([heatwave]+[new_next_hot_day])

    #Select data before and after the hottest day that we do not replace
    before_hottest_data = epw_data.iloc[:hottest_day_index]

    if hottest_day_index + 24 * heat_length > file_len:
        hours_to_wrap = (hottest_day_index + 24 * heat_length) - file_len
        before_hottest_data = pd.concat([heatwave[-hours_to_wrap:]] + [before_hottest_data[hours_to_wrap:]], ignore_index=True)
        heatwave = heatwave[:-hours_to_wrap]
        after_hottest_data = pd.DataFrame([])
    else:
        after_hottest_data = epw_data.iloc[hottest_day_index + 24 * heat_length:]

    #Concatenate the data
    file.dataframe = pd.concat([before_hottest_data] + [heatwave] + [after_hottest_data], ignore_index=True)

    #Save the new EPW file
    file.write(output_file)

def create_future_heatwave(tmy_file, heatwave_file, future_file, output_file):

    #Read TMY data
    tmy_df = epw()
    tmy_df.read(tmy_file)
    tmy_data = tmy_df.dataframe

    #Read heatwave data
    heat_df = epw()
    heat_df.read(heatwave_file)
    heat_data = heat_df.dataframe

    #Read future data
    fut_heat_df = epw()
    fut_heat_df.read(future_file)
    fut_heat_data = fut_heat_df.dataframe.iloc[:8760,:]

    #The first 5 columns stay the same; for the remaining ones we always add the difference of the Heatwave-TMY to the typical future data
    #The heatwave data provided by shinyweatherdata has missing data in the following columns, so we set them to the same values as in the Future TMY
    miss_data_idx = [5, 10, 11, 16, 17, 18, 19, 24, 25, 26, 27, 28, 29, 31, 32, 34]
    date_idx = [0, 1, 2, 3, 4]

    nr_cols = tmy_data.shape[1]

    for i in range(nr_cols):
        #we do not change the year, month, day, hour, minute data
        if i in date_idx:
            continue

        if i in miss_data_idx:
            continue

        fut_heat_data.iloc[:, i] += (heat_data.iloc[:, i] - tmy_data.iloc[:, i])

        #clip the RH to [0,100]
        if epw_cols[i] == 'Relative Humidity':
            fut_heat_data['Relative Humidity'] = fut_heat_data['Relative Humidity'].clip(lower=0, upper=100)

        #clip the cloud coverage to [0,10]
        elif epw_cols[i] == 'Total Sky Cover':
            fut_heat_data['Total Sky Cover'] = fut_heat_data['Total Sky Cover'].clip(lower=0, upper=10)

        elif epw_cols[i] == 'Opaque Sky Cover (used if Horizontal IR Intensity missing)':
            fut_heat_data['Opaque Sky Cover (used if Horizontal IR Intensity missing)'] = fut_heat_data['Opaque Sky Cover (used if Horizontal IR Intensity missing)'].clip(lower=0, upper=10)

        elif epw_cols[i] == 'Wind Direction':
            fut_heat_data['Wind Direction'] = fut_heat_data['Wind Direction'] % 360

    fut_heat_df.dataframe = fut_heat_data
    fut_heat_df.write(output_file)


#Shift all temperature values up by the number of degrees specified
def include_uhi_effect(epw_file, uhi_degrees, output_file):

    #Read EPW data
    epw_df = epw()
    epw_df.read(epw_file)
    epw_df_data = epw_df.dataframe

    epw_df_data['Dry Bulb Temperature'] += uhi_degrees

    epw_df.write(output_file)