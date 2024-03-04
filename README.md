# Heatalyzer

Welcome to **Heatalyzer**, an open-source application designed for analyzing thermal comfort, liveability and survivability in buildings under extreme weather conditions. 

## Features

- **File Upload**: Heatalyzer allows users to upload IDF-format building files compatible with EnergyPlus version 23.1.0, and EPW weather data files. Users can select a baseline weather file for distribution shift calculations and tailor simulation settings to their study location.

- **Results Analysis**: The application includes a results section for analysis, focused on thermal comfort, liveability and survivability across various scenarios. It empowers users with the flexibility to conduct detailed comparisons and analyses, selecting from an array of buildings, zones, weather scenarios, and metrics.

- **Extreme Weather File Creation**: This feature enables users to create customized extreme weather scenarios, including prolonged and future heatwaves, and incorporating the Urban Heat Island (UHI) effect. Users input necessary information following guidelines to generate and download these scenarios.


## Getting Started

### Installation

1. **Clone the Repository**: Begin by cloning the Heatalyzer repository to your local machine using the command:
```bash
git clone https://github.com/lcapol/Heatalyzer
```
2. **Install Dependencies**: Navigate to the Heatalyzer directory and install the required dependencies using: 
```bash
pip install -r requirements.txt
```
3. **Install EnergyPlus**: Ensure that EnergyPlus version [23.1.0](https://github.com/NREL/EnergyPlus/releases/tag/v23.1.0) is installed for compatibility with file formats. Adjust the application paths in `app_BEM`, `app_preprocessing`, and `app_postprocessing` source code files as needed to match your installation directory, or use the default path `'/Application/EnergyPlus-23-1-0'`.


### Usage

1. **Launch Application**: With the setup complete, start Heatalyzer by navigating to its directory and executing:
```bash
streamlit run Home.py
``` 
2. **Extreme Weather File Creation**: Create and download your customized extreme weather files.

3. **File Upload**: Begin by uploading your building and weather data files. Customize the simulation and evaluation parameters to fit your project's requirements, then initiate the simulation process. 
4. **Results Analysis**: Explore the results section after simulation completion to assess the thermal comfort, livability, and survivability of your buildings under various weather conditions.
