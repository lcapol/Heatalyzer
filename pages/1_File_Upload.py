import streamlit as st
import os
from pathlib import Path
import sys

script_dir = Path(__file__).parent
sys.path.append(str(script_dir))

from utils.app_preprocessing import preprocess
from utils.app_BEM import BEM_simulation
from utils.app_postprocessing import postprocess

st.set_page_config(page_title='File Upload')
st.markdown("# File Upload")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'selected_building' not in st.session_state:
    st.session_state['selected_building'] = None

if 'building_folders' not in st.session_state:
        st.session_state['building_folders'] = []

if 'building_names' not in st.session_state:
        st.session_state['building_names'] = []

if 'summer_months' not in st.session_state:
    st.session_state.summer_months = [6,7,8]

if 'metrics_thresholds' not in st.session_state:
    st.session_state.metrics_thresholds = {'Humidex': 35, 'SET': 30, 'Temperature': 30, 'PMV': 1.5, 'WBGT': 23}

if 'start_month' not in st.session_state:
    st.session_state.start_month = 1

if 'rerun_all' not in st.session_state:
    st.session_state.rerun_all = False


months = ['January', 'February', 'March', 'April', 'May', 'June','July', 'August', 'September', 'October', 'November', 'December']


def main():

    st.markdown("""
        Please upload your building and weather data files. 
        """)

    st.subheader('Upload Building Data Files (.idf)')
    building_files = st.file_uploader('Choose Building Data Files', accept_multiple_files=True, type='idf')
    st.markdown('**Note**: Only IDF files of version 23.1.0 are supported. Up to 10 building files are supported.')

    st.subheader('Upload Weather Data Files (.epw)')
    weather_files = st.file_uploader('Choose Weather Data Files', accept_multiple_files=True, type='epw',
                                     key='weather')
    st.markdown('**Note**: Up to 5 weather files are supported.')


    if weather_files:
        st.markdown('---')

        # Select the baseline weather file

        baseline_weather_file = st.radio("Select a Baseline Weather File:",
                                         [file.name for file in weather_files], key='baseline_weather')


    if weather_files and building_files:
        st.markdown('---')
        st.markdown('Select start month for simulation (simulations run for the whole year):')
        start_month = st.selectbox('Start Month', ['January', 'June'], index=0)
        st.session_state.start_month = months.index(start_month) + 1

        st.markdown('---')

        st.markdown('Select the months considered as summer:')
        start_month = st.selectbox('Start Month', months, index=5)  # Default to June
        end_month = st.selectbox('End Month', months, index=7)  # Default to September

        start_index = months.index(start_month) + 1
        end_index = months.index(end_month) + 1

        if end_index < start_index:
            summer_months_indices = list(range(start_index, 13)) + list(range(1, end_index + 1))
        else:
            summer_months_indices = list(range(start_index, end_index + 1))

        st.session_state.summer_months = summer_months_indices

        st.markdown('---')


        st.markdown('Set Thermal Comfort Thresholds:')
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.session_state.metrics_thresholds['Humidex'] = st.number_input('Humidex', value=35.0, format="%.1f")
        with col2:
            st.session_state.metrics_thresholds['SET'] = st.number_input('SET', value=30.0,format="%.1f")
        with col3:
            st.session_state.metrics_thresholds['Temperature'] = st.number_input('Temperature', value=30.0, format="%.1f")
        with col4:
            st.session_state.metrics_thresholds['PMV'] = st.number_input('PMV', value=1.5, format="%.1f")
        with col5:
            st.session_state.metrics_thresholds['WBGT'] = st.number_input('WBGT', value=23.0, format="%.1f")

        st.markdown('---')

        st.markdown('**Note**: Only scenarios not simulated before will be run. If you would like to run all simulations again, select the re-run option. If not selected, all scenarios with the same weather and building file names will not be simulated again.')

        rerun_all = st.checkbox('Re-run simulations', value=False)
        st.session_state.rerun_all = rerun_all

        # Simulate button
        if st.button('Simulate'):

            if len(weather_files) > 5 or len(building_files) > 10:
                st.error('Please upload no more than 10 building and 5 weather files.')
            elif validate_files(building_files, '.idf') and validate_files(weather_files, '.epw'):
                baseline_file = next((file for file in weather_files if file.name == baseline_weather_file), None).name
                st.session_state.baseline_file=os.path.splitext(baseline_file)[0]
                st.success('Files validated. Starting simulation...')
                create_folders_and_move_files(building_files, weather_files)
                run_simulation()
                st.session_state.current_page = 'results'
                st.success('Processing finished. You can view the results!')
            else:
                st.error('File validation failed. Please upload correct file types.')


def validate_files(files, extension):
    return all(file.name.endswith(extension) for file in files) if files else False

def create_folders_and_move_files(building_files, weather_files):

    #Define and create folder for outputs
    output_folder = 'Output'
    os.makedirs(output_folder, exist_ok=True)

    simulation_folders = []
    building_folders = []
    weather_folders = []
    building_names = []

    for building_file in building_files:
        building_name = os.path.splitext(building_file.name)[0]
        building_names.append(building_name)
        building_folder = os.path.join(output_folder, building_name)
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
    st.session_state.building_names = building_names



def run_simulation():

    #Preprocess building input files to configure variables for thermal comfort computations
    preprocess(st.session_state.simulation_folders)

    #Run EnergyPlus simulations for the input building and weather file combinations
    BEM_simulation(st.session_state.simulation_folders)

    st.success('Simulation finished. Starting processing results...')

    #Postprocess the output to extract data for the result visualizations
    postprocess(st.session_state.simulation_folders, st.session_state.building_folders, st.session_state.weather_folders)

if __name__ == "__main__":
    main()