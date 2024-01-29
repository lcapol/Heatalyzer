import streamlit as st

# Set page configuration
st.set_page_config(page_title='Heatalyzer')

# Page Title
st.markdown("# Heatalyzer")
st.markdown("""
Welcome to the Heatalyzer! This application is designed to assist in analyzing building 
and weather data to understand thermal comfort and survivability during extreme weather conditions. 
There are two main sections in this application:
""")

# File Upload Section Description
st.markdown("## 1. File Upload")
st.markdown("""
In the **File Upload** section, you can upload your building data files (in IDF format, version 23.1.0) and 
weather data files (in EPW format). The application currently supports a maximum of 5 weather files. 
This section is where you start your journey by providing the necessary data for analysis. One weather file can then be selected as the baseline for distribution shift calculations.
You can further specify the summer months and starting month for the EnergyPlus simulations based on the location of your study. Finally, the 
thresholds to use for thermal comfort evaluations can be tailored. 
""")

# Results Section Description
st.markdown("## 2. Results")
st.markdown("""
After uploading the data files and running the simulation, you can navigate to the **Results** section. 
Here, you can view and analyze the simulation outcomes. The results are categorized into several types:
""")

st.markdown("""
For each individual building:
- **Thermal Comfort During Hottest Weeks**: Understand building thermal comfort during the hottest weeks of the year.
- **Distribution Shifts compared to Baseline**: Compare the distribution of the differences of thermal comfort metrics of different weather scenarios to the selected baseline.
- **Survivability and Liveability During Hottest Weeks**: Examine conditions against survivability thresholds for two age groups (18-45 and over 65) and a Wet Bulb Temperature of 35°C during extreme heat.

Comparisons across buildings:
- **Comparison of Degree hours (Dh) and Exceedance hours (Eh)**: Compare the Dh and Eh for different weather files and building zones, which can represent annual or worst-case observed values over the hottest summer week. Selection options for zones, buildings, and weather scenarios are provided.
- **Peak Humidex Value**: Display the peak Humidex values on a temperature and relative humidity grid against established comfort ranges for Humidex. Selection options for zones, buildings, and weather scenarios are included.
""")

st.markdown("""
Note: The application reports five different models for thermal comfort analysis (Temperature, Humidex, SET, WBGT, and PMV), focusing on Temperature, Humidex and SET for summer hourly differences and survivability due to the high correlation between model predictions.
""")

st.markdown("""
To begin, navigate to the **File Upload** page to upload your data files and start the simulation. Once the data is uploaded and processed, 
you can explore the different types of results to gain insights into building performance and occupant comfort.
""")
