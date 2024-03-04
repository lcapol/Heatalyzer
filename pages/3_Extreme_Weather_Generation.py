import streamlit as st
import os
from pathlib import Path
import sys
import io

script_dir = Path(__file__).parent
sys.path.append(str(script_dir))

from utils.app_heatwave_creation import create_future_heatwave, extend_heatwave, include_uhi_effect

st.set_page_config(page_title='Extreme Weather Generation')

st.title("Extreme Weather Generation")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'home'

if 'selected_building' not in st.session_state:
    st.session_state['selected_building'] = None

if 'building_files' not in st.session_state:
        st.session_state['building_files'] = []

if 'created_future_heatwave' not in st.session_state:
    st.session_state['created_future_heatwave'] = False
    st.session_state['future_heatwave_output_file'] = None
    st.session_state['future_heatwave_file_name'] = None

if 'created_prolonged_heatwave' not in st.session_state:
    st.session_state['created_prolonged_heatwave'] = False
    st.session_state['prolonged_heatwave_output_file'] = None
    st.session_state['prolonged_heatwave_file_name'] = None

if 'created_uhi_scenario' not in st.session_state:
    st.session_state['created_uhi_scenario'] = False
    st.session_state['uhi_output_file'] = None
    st.session_state['uhi_file_name'] = None

os.makedirs('Extreme Weather', exist_ok=True)
os.makedirs('Extreme Weather/Input', exist_ok=True)
os.makedirs('Extreme Weather/Prolonged Heatwave', exist_ok=True)
os.makedirs('Extreme Weather/Future Heatwave', exist_ok=True)
os.makedirs('Extreme Weather/UHI Effect', exist_ok=True)

def main():
    st.markdown("""
                Generate weather files for extreme heat scenarios, including prolonged heatwaves and anticipated future heatwaves, and for incorporating the Urban Heat Island (UHI) effect.                
                """)

    st.subheader('Prolonged Heatwave Scenario')
    st.markdown("""
                Upload a heatwave scenario and specify how long the hottest heatwave day should last (2 to 7 days) to generate a prolonged heatwave. 
                """)
    heatwave_file = st.file_uploader('Upload Heatwave Data File', accept_multiple_files=False, type='epw')
    days = st.slider('Specify Duration', 2, 7, value=2)

    input_folder = 'Extreme Weather/Input/'

    if heatwave_file and validate_files([heatwave_file], 'epw'):
        if st.button('Create Prolonged Heatwave Scenario'):

            #Move provided input file into the "Input" folder
            input_file = input_folder + heatwave_file.name
            file_name = os.path.splitext(heatwave_file.name)[0] + '_' + str(days) + os.path.splitext(heatwave_file.name)[1]
            output_file = 'Extreme Weather/Prolonged Heatwave/' + file_name

            with open(input_file, "wb") as f:
                f.write(heatwave_file.getbuffer())

            #Create prolonged heatwave and save in output folder
            extend_heatwave(input_file, output_file, days)
            st.session_state['created_prolonged_heatwave'] = True
            st.session_state['prolonged_heatwave_output_file'] = output_file
            st.session_state['prolonged_heatwave_file_name'] = file_name

        if st.session_state.created_prolonged_heatwave:
            #Read prolonged heatwave data from output folder and allow for download
            buffer = get_file_buffer(st.session_state.prolonged_heatwave_output_file)
            st.download_button(
                label="Download File",
                data=buffer,
                file_name=st.session_state.prolonged_heatwave_file_name,
                mime="text/plain"
            )

    st.subheader('Future Heatwave Scenario')
    st.markdown("""
                Upload three files: weather data for a historically typical year, an observed heatwave, and a projected future typical year to create a future heatwave scenario.
                 """)
    weather_files = st.file_uploader('Upload Weather Data Files', accept_multiple_files=True, type='epw', key='weather')

    #Process the uploaded files for the Future Heatwave Scenario
    if weather_files and len(weather_files) >= 3 and validate_files(weather_files, 'epw'):
        st.markdown('---')
        file_options = [file.name for file in weather_files]

        #Assign the uploaded files to their respective category
        baseline_weather_file = st.selectbox("Select the Typical Year File:", file_options, key='baseline_weather')
        heatwave_scenario_file = st.selectbox("Select the Heatwave Scenario File:", file_options,
                                              key='heatwave_scenario')
        future_tmy_file = st.selectbox("Select the Future Typical Year File:", file_options, key='future_tmy')

        if st.button('Create Future Heatwave Scenario'):

            #Move provided input files into the "Input" folder
            for file in weather_files:
                input_file = input_folder + file.name
                with open(input_file, "wb") as f:
                    f.write(file.getbuffer())

            #Create future heatwave and save in output folder
            file_name = 'Future_Heatwave.epw'
            output_file = 'Extreme Weather/Future Heatwave/' + file_name

            create_future_heatwave(input_folder + baseline_weather_file, input_folder + heatwave_scenario_file, input_folder + future_tmy_file, output_file)

            st.session_state['created_future_heatwave'] = True
            st.session_state['future_heatwave_output_file'] = output_file
            st.session_state['future_heatwave_file_name'] = file_name

        if st.session_state.created_future_heatwave:
            #Read future heatwave data from output folder and allow for download
            buffer = get_file_buffer(st.session_state.future_heatwave_output_file)
            st.download_button(
                label="Download File",
                data=buffer,
                file_name=st.session_state.future_heatwave_file_name,
                mime="text/plain"
            )

    st.subheader('Urban Heat Island Effect Integration')
    st.markdown("""
                 Upload a weather file and specify the UHI intensity to integrate the Urban Heat Island effect into the temperature conditions.
                """)

    uhi_file = st.file_uploader('Upload Weather Data File', accept_multiple_files=False, type='epw',key='uhi')
    uhi_intensity = st.number_input('Specify UHI Intensity', min_value=0.0, step=0.001, key='uhi_intensity')

    #Process the UHI scenario
    if uhi_file and uhi_intensity is not None:
        if st.button('Create UHI Effect Scenario'):

            #Move provided input file into the "Input" folder
            input_file = input_folder + uhi_file.name
            file_name = os.path.splitext(uhi_file.name)[0] + '_UHI_' + str(uhi_intensity) + \
                        os.path.splitext(uhi_file.name)[1]

            with open(input_file, "wb") as f:
                f.write(uhi_file.getbuffer())

            #Integrate UHI effect and save in output folder
            output_file = 'Extreme Weather/UHI Effect/' + file_name
            include_uhi_effect(input_file, uhi_intensity, output_file)

            st.session_state['created_uhi_scenario'] = True
            st.session_state['uhi_output_file'] = output_file
            st.session_state['uhi_file_name'] = file_name

        if 'created_uhi_scenario' in st.session_state and st.session_state.created_uhi_scenario:
            #Read new weather data from output folder and allow for download
            buffer = get_file_buffer(st.session_state.uhi_output_file)
            st.download_button(
                label="Download File",
                data=buffer,
                file_name=st.session_state.uhi_file_name,
                mime="text/plain"
            )

def get_file_buffer(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        text_data = file.read()

    # Convert to binary
    binary_data = text_data.encode('utf-8')
    buffer = io.BytesIO(binary_data)
    return buffer

def validate_files(files, extension):
    return all(file.name.endswith(extension) for file in files) if files else False

if __name__ == "__main__":
    main()