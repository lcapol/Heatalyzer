import streamlit as st

# Set page configuration
st.set_page_config(page_title='Heatalyzer')

# Page Title
st.markdown("# Heatalyzer")
st.markdown("""
Welcome to the Heatalyzer! This application is designed to assist in analyzing building 
and weather data to understand thermal comfort, liveability and survivability during extreme weather conditions. 
There are three main sections in this application:
""")

# File Upload Section Description
st.markdown("## 1. File Upload")
st.markdown("""
In the **File Upload** section, you can upload your building data files (in IDF format, version 23.1.0) and 
weather data files (in EPW format). The application currently supports a maximum of 10 building and 5 weather files. 
This section is where you start your analysis by providing the necessary data. One weather file can be selected as the baseline for distribution shift calculations.
Please further specify the summer months and starting month for the EnergyPlus simulations based on the location of your study. Finally, the 
thresholds to use for thermal comfort evaluations can be tailored. 

Once all data is provided, you can run the simulations. By default any simulation with the same building and weather file combination is not 
run if the respective output has been generated before. However, there exists the option to re-run all simulations. 
""")

# Results Section Description
st.markdown("## 2. Results")
st.markdown("""
After uploading the data files and running the simulation, you can navigate to the **Results** section. 
Here, you can view and analyze the simulation outcomes. The results are categorized into several types:
""")

st.markdown("""
For each individual building:
- **Thermal Comfort During Hottest Weeks**: Understand building thermal comfort during the hottest weeks of the year. For this, the hourly thermal comfort values are shown for the 
hottest summer week, with its preceding and following week. 
- **Summer Distribution Shifts compared to Baseline**: Compare the distribution of the hourly thermal comfort differences during the summer months of the weather scenarios to the selected baseline.
- **Survivability and Liveability During Hottest Weeks**: Examine hourly temperature and relative humidity values during hottest summer week against survivability thresholds for two age groups (18-45 and over 65) and a Wet Bulb Temperature of 35°C.

Comparisons across buildings:
- **Comparison of Degree hours (Dh) and Exceedance hours (Eh)**: Compare the Dh and Eh for different weather files and building zones. Both annual or worst-case observed values over the hottest summer week are reported and selection options for zones, buildings, and weather scenarios are provided.
- **Peak Humidex Value**: Display the peak Humidex values on a temperature and relative humidity grid with established comfort ranges for Humidex. Selection options for specific zones, buildings, and weather scenarios to show are included.
""")

st.markdown("""
Note: The application reports five different models for thermal comfort (Temperature, Humidex, SET, WBGT, and PMV), focusing on Temperature, Humidex and SET for distribution shifts and liveability and survivablity analyses due to the high correlation between model predictions.
""")

# Results Section Description
st.markdown("## 3. Extreme Weather Generation")
st.markdown("""
Our tool integrates functionalities that allow creating two types of extreme weather files, e.g., prolonged heat scenarios and anticipated future heatwaves, and incorporating the UHI effect. 
To create the desired weather scenarios, please input the necessary information. Once the inputs are provided, the customized weather files can be generated and downloaded.
""")

st.markdown("""
To begin, navigate to the **File Upload** page to upload your data files and start the simulation. Once the data is uploaded and processed, 
you can explore the different types of results to gain insights into building performance and occupant comfort.
""")
