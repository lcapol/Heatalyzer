import pandas as pd
from .epw import epw

epw_cols = names=['Year','Month','Day','Hour','Minute','Data Source and Uncertainty Flags','Dry Bulb Temperature','Dew Point Temperature','Relative Humidity',
'Atmospheric Station Pressure','Extraterrestrial Horizontal Radiation','Extraterrestrial Direct Normal Radiation','Horizontal Infrared Radiation Intensity',
'Global Horizontal Radiation','Direct Normal Radiation','Diffuse Horizontal Radiation','Global Horizontal Illuminance','Direct Normal Illuminance',
'Diffuse Horizontal Illuminance','Zenith Luminance','Wind Direction','Wind Speed','Total Sky Cover','Opaque Sky Cover (used if Horizontal IR Intensity missing)',
'Visibility','Ceiling Height','Present Weather Observation','Present Weather Codes','Precipitable Water','Aerosol Optical Depth','Snow Depth','Days Since Last Snowfall',
'Albedo','Liquid Precipitation Depth','Liquid Precipitation Quantity']

from datetime import datetime, timedelta

#Function that provides the dates (month and day) of the following and previous day given some date (year, month ,day)
def get_previous_and_next_dates(input_year, input_day, input_month, days_delta, include_previous=True, include_next=True):
    # Create a datetime object with the given day and month
    input_date = datetime(year=input_year, month=input_month, day=input_day)

    previous_date = next_date = input_date

    if include_previous:
        #Calculate the previous day
        previous_date = input_date - timedelta(days=days_delta)

    if include_next:
        #Calculate the next day
        next_date = input_date + timedelta(days=days_delta)

    #Extract the month and day for the previous and next dates
    previous_month, previous_day = previous_date.month, previous_date.day
    next_month, next_day = next_date.month, next_date.day

    return previous_month, previous_day, next_month, next_day


#Function that provides the dates (year, month and day) of the following day given some date (year, month and day)
def get_next_date(input_year, input_day, input_month, days_delta):
    # Create a datetime object with the given day and month
    input_date = datetime(year=input_year, month=input_month, day=input_day)

    #Calculate the next day
    next_date = input_date + timedelta(days=days_delta)

    #Extract the month and day for the previous and next dates
    next_year, next_month, next_day = next_date.year, next_date.month, next_date.day

    return next_year, next_month, next_day


# Function to find the hottest day in summer
def find_hottest_summer_day(epw_data):
    # Extract the temperature data
    temperature_data = epw_data['Dry Bulb Temperature']

    # Extract the month and day columns
    month = epw_data['Month']
    day = epw_data['Day']

    # Define summer months (customizable based on location)
    summer_months = [6, 7, 8]

    # Filter data for summer months
    summer_data = temperature_data[(month.isin(summer_months))]

    # Find the index of the hottest hour in summer
    hottest_hour_index = summer_data.idxmax()

    # Extract the date of the hottest day
    hottest_month = month[hottest_hour_index]
    hottest_day = day[hottest_hour_index]

    return hottest_month, hottest_day

##Take a weather file, determine the hottest day of the year and prolong its length to last heat_length days.
#Hearby the day with peak temperature is replicated and replaces the data in the following days
def extend_heatwave(input_file, output_file, heat_length):

    #How many times we replicate the hottest day is one less than the desired heatwave length
    len = heat_length - 1

    #Load the EPW file

    file = epw()
    file.read(input_file)
    epw_data = file.dataframe

    #Find the hottest day in summer (hottest in terms of highest temperature peak)
    hottest_month, hottest_day = find_hottest_summer_day(epw_data)
    hottest_data = epw_data[(epw_data['Month'] == hottest_month) & (epw_data['Day'] == hottest_day)]
    #Find the index of the hottest day
    hottest_day_index = hottest_data.index[0]

    #Select data before and after the hottest day that we do not replace
    before_hottest_data = epw_data.iloc[:hottest_day_index]
    after_hottest_data = epw_data.iloc[hottest_day_index + 24*(len+1):]

    heatwave = hottest_data.copy()
    #Create heatwave, which is heat_length * the data of the hottest day
    for i in range(len):
        next_year, next_month, next_day = get_next_date(2022, hottest_day, hottest_month, i+1)

        new_next_hot_day = hottest_data.copy()
        new_next_hot_day['Month'] = next_month
        new_next_hot_day['Day'] = next_day

        heatwave = pd.concat([heatwave]+[new_next_hot_day])

    #Concatenate the data
    file.dataframe = pd.concat([before_hottest_data] + [heatwave] + [after_hottest_data], ignore_index=True)

    #Save the new EPW file
    file.write(output_file)

    return file

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

    #the first 5 columns stay the same and for the remaining ones we always add the difference of the heatwave-TMY to the typical future data

    #in our heat data the following columns have missing data, so they will remain the same as for the 2080 TMY
    miss_data_idx = [5, 10, 11, 16, 17, 18, 19, 24, 25, 26, 27, 28, 29, 31, 32, 34]
    date_idx = [0, 1, 2, 3, 4]

    nr_cols = tmy_data.shape[1]

    for i in range(nr_cols):
        #we do not change the year, month, day, hour, minute data
        if i in date_idx:
            continue

        if i in miss_data_idx:
            continue

        col= epw_cols[i]
        diff= (heat_data.iloc[:, i] - tmy_data.iloc[:, i])
        fut_heat_data.iloc[:, i] += (heat_data.iloc[:, i] - tmy_data.iloc[:, i])

        #clip the RH to [0,100]
        if epw_cols[i] == 'Relative Humidity':
            fut_heat_data['Relative Humidity'] = fut_heat_data['Relative Humidity'].clip(lower=0, upper=100)

        #clip the cloud coverage to [0,10]
        elif epw_cols[i] == 'Total Sky Cover':
            fut_heat_data['Total Sky Cover'] = fut_heat_data['Total Sky Cover'].clip(lower=0, upper=10)

        elif epw_cols[i] == 'Opaque Sky Cover (used if Horizontal IR Intensity missing)':
            fut_heat_data['Opaque Sky Cover (used if Horizontal IR Intensity missing)'] = fut_heat_data['Opaque Sky Cover (used if Horizontal IR Intensity missing)'].clip(lower=0, upper=10)

    fut_heat_df.write(output_file)


def main():

    ##Code for prolonging heatwave peak day to last longer
    '''
    #Specify desired lengths of heatwave (in days)
    heat_length = [3, 5, 7]

    #Specify the output folder
    output_folder = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Haringey/Weather Data/Extended Heatwave/'

    #Specify the EPW file and name for file
    epw_file_path = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Haringey/Weather Data/Historical Data/2022-lat=51.58155_lng=-0.09965_period=2022.epw'
    file_name = 'extended_' + '2022-lat=51.58155_lng=-0.09965_period=2022.epw'

    for len in heat_length:
        extend_heatwave(epw_file_path, output_folder, file_name, len)
    '''

    ##Code for creating a 2080 heatwave scenario based on a TMY, current heatwave, and 2080 typical year
    tmy_file = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Haringey/Weather Data/Meteonorm/Historical/Haringey-hour.epw'
    #tmy_file = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Haringey/Weather Data/Meteonorm/Contemporary/Haringey-hour.epw'
    heatwave_file = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Haringey/Weather Data/Historical Data/2022-lat=51.58155_lng=-0.09965_period=2022.epw'
    future_file = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Haringey/Weather Data/Meteonorm/2030/Haringey-hour.epw'
    output_folder = '/Users/Livia/Library/Mobile Documents/com~apple~CloudDocs/Cambridge University/Thesis/Model/Input Data/Haringey/Weather Data/Future Heatwave/'
    file_name = '2030_heatwave.epw'
    #file_name = '2080_heatwave_contemp.epw'

    create_future_heatwave(tmy_file, heatwave_file, future_file, output_folder, file_name)


if __name__ == "__main__":
    main()
