import streamlit as st

# Set page configuration
st.set_page_config(page_title='Heatalyzer')

# Page Title
st.title("Heatalyzer")
st.write("""
Welcome to the Heatalyzer! This application is designed to assist in analyzing building 
and weather data to understand indoor thermal comfort, liveability and survivability during extreme weather conditions. 
More information on the methodology used can be found in the Heatalyzer paper [here](https://www.cambridge.org/engage/coe/article-details/65ccc858e9ebbb4db958f3e9).
There are three main sections in this application:
""")

# File Upload Section Description
st.subheader("1. File Upload")
st.write("""
In the **File Upload** section, start your analysis by uploading building data files (EnergyPlus Input Data File (IDF) format, version 23.1.0) and 
weather data files (EnergyPlus Weather File (EPW) format). The application currently supports up to 10 building files and 5 weather files. 
""")
st.write("""
There are additional specifications you can make for the simulation:
- **Baseline weather scenario:** Select a file as the baseline weather conditions for calculating distribution shifts of indoor conditions.
- **Summer months and start month:** Define the months to be considered summer for your study location and the start month for the EnergyPlus simulations. Selecting the start month enables you to ensure the
simulations fully capture the hottest periods of the weather scenarios. 
- **Thermal comfort thresholds:** Customize the thresholds for the different thermal comfort models. These thresholds are used for the Degree hours and Exceedance hours calculations. 

*Note:* By default, simulations with previously analyzed building-weather file combinations won't rerun unless you select the "Re-run simulations" feature.
""")

# Results Section Description
st.subheader("2. Results")
st.write("""
After running the simulations, navigate to the **Results** section to view and analyze the results. This section provides different output types relevant for 
assessing the indoor conditions within buildings during extreme heat scenarios. 
""")

st.markdown("##### Individual buildings")
st.write("""
- **Thermal Comfort During Hottest Weeks**: Examine the building thermal comfort during the hottest weeks of the year. The hourly thermal comfort values for the 
hottest summer week are shown, with its preceding and following week. We report five thermal comfort indices: Temperature, Humidex, Standard Effective Temperature (SET), Predicted Mean Vote (PMV), and Wet Bulb Globe Temperature (WBGT).
- **Summer Distribution Shifts**: Assess how the indoor thermal comfort during the summer months deviates from the baseline weather conditions. The distribution of the differences in hourly thermal comfort values over the summer months are reported for Temperature, Humidex, SET, PMV, and WBGT. 
- **Liveability and Survivability During Hottest Weeks**: Examine hourly temperature and relative humidity values during the hottest summer week against liveability ranges and survivability limits for two age groups (18-40 and over 65 years), the Wet Bulb Temperature (WBT) of 35°C, and Humidex ranges. For the liveability ranges, the Activity hours are displayed,
indicating the number of hours that occupants can still perform different levels of physical activities safely. 
""")

st.markdown("##### Comparisons across buildings")
st.write("""
- **Degree hours (Dh) and Exceedance hours (Eh)**: Analyze the Dh and Eh across the different building and weather scenarios. Both the annual and worst-case values over one week are provided for Temperature, SET, and Humidex. 
- **Activity hours (Ah)**: Analyze the number of hours of possible physical activities over the hottest summer week for four activity ranges ('Moderate to vigorous activites', 'Light activities', 'No activites', 'Not survivable') and two age groups (18-40 and over 65 years) across different scenarios.
- **Peak Humidex Value**: Display the peak Humidex values observed on a temperature and relative humidity grid with established comfort ranges for Humidex. In case multiple conditions result in the same maximum Humidex value, the conditions for the first peak are reported. Selection options for specific zones, buildings, and weather scenarios to show are included. 
""")


# Results Section Description
st.subheader("3. Extreme Weather Generation")
st.write("""
Use Heatalyzer to create custom extreme weather scenarios, including prolonged heatwaves, future heatwaves, and incorporating the Urban Heat Island (UHI) effect. For this, upload the necessary information for the scenario of interest. Once the inputs are provided, the customized weather files can be generated and downloaded.
""")
