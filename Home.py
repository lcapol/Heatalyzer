import streamlit as st

# Set page configuration
st.set_page_config(page_title='Heatalyzer')

# Page Title
st.title("Heatalyzer")
st.write("""
Welcome to the Heatalyzer! This application is designed to assist in analyzing building 
and weather data to understand thermal comfort, liveability and survivability during extreme weather conditions. 
There are three main sections in this application:
""")

# File Upload Section Description
st.header("1. File Upload")
st.write("""
In the **File Upload** section, start your analysis by uploading building data files (IDF format, version 23.1.0) and 
weather data files (EPW format). The application currently supports up to 10 building files and 5 weather files. 
Here are additional specifications you can make:
- **Select a baseline weather file** for distribution shift calculations.
- **Define summer months** and the **starting month** for EnergyPlus simulations based on your study location. 
- **Customize thermal comfort thresholds** for a tailored analysis.

*Note:* By default, simulations with previously analyzed building-weather file combinations won't rerun unless you select the "Re-run simulations" feature.
""")

# Results Section Description
st.header("2. Results")
st.write("""
After running the simulations, navigate to the **Results** section to view and analyze the results. The outputs are categorized into several types.
""")

st.write("""
For individual buildings:
- **Thermal Comfort During Hottest Weeks**: Examine building thermal comfort during the hottest weeks of the year. For this, the hourly thermal comfort values are shown for the 
hottest summer week, with its preceding and following week. 
- **Summer Distribution Shifts**: Compare how the hourly thermal comfort metrics during the summer months deviate from your chosen baseline weather scenario.
- **Survivability and Liveability During Hottest Weeks**: Assess hourly temperature and relative humidity values during the hottest summer week against survivability and liveability limits for two age groups (18-45 and over 65), the Wet Bulb Temperature (WBT) of 35°C, and Humidex ranges.

For comparisons across buildings:
- **Comparison of Degree hours (Dh) and Exceedance hours (Eh)**: Analyze the Dh and Eh for across different scenarios, for both annual or worst-case values over one week. Selection options for zones, buildings, and weather scenarios to observe are provided.
- **Peak Humidex Value**: Display the peak Humidex values on a temperature and relative humidity grid with established comfort ranges for Humidex. Selection options for specific zones, buildings, and weather scenarios to show are included.
""")

st.write("""
*Note:* Our tool reports five indices for assessing indoor conditions (Temperature, Humidex, SET, WBGT, and PMV), focusing on Temperature, Humidex and SET for distribution shifts and liveability and survivablity analyses.
""")


# Results Section Description
st.header("3. Extreme Weather Generation")
st.write("""
Use Heatalyzer to create custom extreme weather scenarios, including prolonged heatwaves, future heat conditions, and incorporating the Urban Heat Island (UHI) effect. For this, upload the necessary information for the scenario of interest. Once the inputs are provided, the customized weather files can be generated and downloaded.
""")
