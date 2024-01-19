import streamlit as st
import os
from pathlib import Path
import sys

script_dir = Path(__file__).parent
sys.path.append(str(script_dir))

from utils.app_preprocessing import preprocess
from utils.app_BEM import BEM_simulation
from utils.app_postprocessing import postprocess
from utils.app_heatwave_creation import create_future_heatwave, extend_heatwave

st.set_page_config(page_title='Extreme Weather Creation', page_icon="🔥")
st.markdown("# Extreme Weather Creation")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'selected_building' not in st.session_state:
    st.session_state['selected_building'] = None

if 'building_files' not in st.session_state:
        st.session_state['building_files'] = []

os.makedirs('Extreme Weather', exist_ok=True)
os.makedirs('Extreme Weather/Input', exist_ok=True)
os.makedirs('Extreme Weather/Prolonged Heatwave', exist_ok=True)
os.makedirs('Extreme Weather/Future Heatwave', exist_ok=True)

def main():
    st.markdown("""
           Please upload your weather data files for the desired extreme weather scenarios to create.
           """)

    st.subheader('Prolonged Heatwave Scenario')
    st.markdown("""
              Please upload a heatwave scenario and select the number of days the peak conditions should last for (2 to 7 days). 
              This will create a prolonged heatwave scenario. 
              """)
    heatwave_file = st.file_uploader('Choose a Heatwave Data File', accept_multiple_files=False, type='epw')
    days = st.slider('Select number of days for peak conditions', 2, 7, value=2)

    if heatwave_file and validate_files([heatwave_file], 'epw'):
        if st.button('Create Prolonged Heatwave Scenario'):
            input_file = 'Extreme Weather/Input/' + heatwave_file.name
            file_name = os.path.splitext(heatwave_file.name)[0] + '_' + str(days) + os.path.splitext(heatwave_file.name)[1]
            output_file = 'Extreme Weather/Prolonged Heatwave/' + file_name

            with open(input_file, "wb") as f:
                f.write(heatwave_file.getbuffer())

            extend_heatwave(input_file, output_file, days)

            st.success("File available in Extreme Weather/Prolonged Heatwave folder: " + file_name)

    st.subheader('Future Heatwave Scenario')
    st.markdown("""
                 Please upload exactly three files: a baseline TMY scenario, a heatwave scenario for that climate, and a projected future TMY. This will create a future heatwave scenario.
                 """)
    weather_files = st.file_uploader('Choose Weather Data Files', accept_multiple_files=True, type='epw', key='weather')


    # Process the uploaded files for the Future Heatwave Scenario
    if weather_files and len(weather_files) == 3 and validate_files(weather_files, 'epw'):
        st.markdown('---')
        file_options = [file.name for file in weather_files]

        baseline_weather_file = st.selectbox("Select the Baseline TMY File:", file_options, key='baseline_weather')
        heatwave_scenario_file = st.selectbox("Select the Heatwave Scenario File:", file_options,
                                              key='heatwave_scenario')
        future_tmy_file = st.selectbox("Select the Projected Future TMY File:", file_options, key='future_tmy')

        if st.button('Create Future Heatwave Scenario'):
            print('hi')
            # Call a function to process the files and display results
            input_folder = 'Extreme Weather/Input/'

            for file in weather_files:
                input_file = input_folder + file.name
                with open(input_file, "wb") as f:
                    f.write(file.getbuffer())

            file_name = 'Future_Heatwave.epw'
            output_file = 'Extreme Weather/Future Heatwave/' + file_name

            create_future_heatwave(input_folder + baseline_weather_file, input_folder + heatwave_scenario_file, input_folder + future_tmy_file, output_file)

            st.success("File available in Extreme Weather/Future Heatwave folder: " + file_name)


def results_page(building_folders):
    st.title("Simulation Results")

    for building in building_folders:
        if st.button(f"View results for {building}"):
            st.session_state.selected_building = building
            st.session_state.current_page = 'building_details'

    if st.button("Back to Home"):
        st.session_state.current_page = 'home'

def building_details_page(building_name):
    st.title(f"Results for {building_name}")
    # Display the results for the selected building
    # ...

    if st.button("Back to Results"):
        st.session_state.current_page = 'results'

def validate_files(files, extension):
    return all(file.name.endswith(extension) for file in files) if files else False

def create_folders_and_move_files(building_files, weather_files):
    simulation_folders = []
    building_folders = []
    weather_folders = []

    for building_file in building_files:
        building_folder = os.path.splitext(building_file.name)[0]
        building_folders.append(building_folder)
        os.makedirs(building_folder, exist_ok=True)

        for weather_file in weather_files:
            weather_folder = os.path.splitext(weather_file.name)[0]
            final_dir = os.path.join(building_folder, weather_folder)
            simulation_folders.append(final_dir)
            os.makedirs(final_dir, exist_ok=True)

            # Copy building file
            building_file_path = os.path.join(final_dir, 'in.idf')
            with open(building_file_path, "wb") as f:
                f.write(building_file.getbuffer())

            # Copy weather file
            weather_file_path = os.path.join(final_dir, 'weather.epw')
            with open(weather_file_path, "wb") as f:
                f.write(weather_file.getbuffer())

    for weather_file in weather_files:
        weather_folder = os.path.splitext(weather_file.name)[0]
        weather_folders.append(weather_folder)

    st.session_state.weather_folders = weather_folders
    st.session_state.building_folders = building_folders
    st.session_state.simulation_folders = simulation_folders


def run_simulation():

    #Preprocess building input files to produce output variables for thermal comfort computations
    preprocess(st.session_state.simulation_folders)

    # Run BEM Simulation for the specified folders
    BEM_simulation(st.session_state.simulation_folders)

    st.success('Simulation finished. Starting processing results...')

    #Create output visualizations and store them

    postprocess(st.session_state.simulation_folders, st.session_state.building_folders, st.session_state.weather_folders)

if __name__ == "__main__":
    main()