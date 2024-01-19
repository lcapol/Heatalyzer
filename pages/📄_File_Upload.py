import streamlit as st
import os
from pathlib import Path
import sys

script_dir = Path(__file__).parent
sys.path.append(str(script_dir))

from utils.app_preprocessing import preprocess
from utils.app_BEM import BEM_simulation
from utils.app_postprocessing import postprocess

st.set_page_config(page_title='File Upload', page_icon="📄")
st.markdown("# File Upload")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'selected_building' not in st.session_state:
    st.session_state['selected_building'] = None

if 'building_folders' not in st.session_state:
        st.session_state['building_folders'] = []

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



    # Select the baseline weather file
    if weather_files:
        st.markdown('---')

        baseline_weather_file = st.radio("Select a Baseline Weather File:",
                                         [file.name for file in weather_files], key='baseline_weather')

        st.markdown('---')

    # Simulate button
    if st.button('Simulate'):
        if len(weather_files) > 5:
            st.error('Please upload no more than 5 weather files.')
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