# Heatalyzer

Welcome to Heatalyzer, an open-source application designed for analyzing building and weather data to enhance thermal comfort and resilience during extreme weather conditions. 

## Features

### File Upload
Heatalyzer allows users to upload IDF-format building files compatible with EnergyPlus version 23.1.0, and EPW weather data files. Users can select a baseline weather file for distribution shift calculations and customize simulation settings based on their specific study location.

### Creation of Extreme Weather Files
This feature enables the creation of customized extreme weather scenarios. Users input necessary information following detailed guidelines to generate and download these scenarios, allowing for tailored analysis of various weather conditions.

### Results Analysis
The application includes a results section for analysis, focused on thermal comfort, liveability and survivability. It supports both individual building analysis and comparisons across different building types. With versatile selection options, users can customize their analysis by choosing specific buildings, zones, weather scenarios, and metrics.

## Installation

1. **Clone the Repository**: 
```bash
git clone https://github.com/lcapol/Heatalyzer
```
2. **Install Dependencies**: Navigate to the cloned reposiory directory and install the required dependencies using: 
```bash
pip install -r requirements.txt
```
3. **EnergyPlus Requirement**: Ensure that EnergyPlus version 23.1.0 is installed for compatibility with file formats.

## Usage

1. **Launch Heatalyzer**: Execute the following command to start the application:
```bash
streamlit run Home.py
``` 
2. **Data Upload**: Uploading your building and weather data files, tailor simulation and evaluation and start simulation. 
3. **Weather Scenario Generation**: Create and download your customized extreme weather files.
4. **Results**: Utilize the results section for in-depth analysis of the uploaded data.
