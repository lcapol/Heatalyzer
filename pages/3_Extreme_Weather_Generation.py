import streamlit as st
import os
from pathlib import Path
import sys
import io

script_dir = Path(__file__).parent
sys.path.append(str(script_dir))

from utils.app_preprocessing import preprocess
from utils.app_BEM import BEM_simulation
from utils.app_postprocessing import postprocess
from utils.app_heatwave_creation import create_future_heatwave, extend_heatwave, include_uhi_effect

st.set_page_config(page_title='Extreme Weather Generation')
st.markdown("# Extreme Weather Generation")

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
           Please upload your weather data files for the desired extreme weather scenarios to create.
           """)

    st.subheader('Prolonged Heatwave Scenario')
    st.markdown("""
              Please upload a heatwave scenario and select the number of days the peak conditions should last for (2 to 7 days). 
              This will create a prolonged heatwave scenario. 
              """)
    heatwave_file = st.file_uploader('Upload a Heatwave Data File', accept_multiple_files=False, type='epw')
    days = st.slider('Select number of days peak condition should last', 2, 7, value=2)

    if heatwave_file and validate_files([heatwave_file], 'epw'):
        if st.button('Create Prolonged Heatwave Scenario'):
            input_file = 'Extreme Weather/Input/' + heatwave_file.name
            file_name = os.path.splitext(heatwave_file.name)[0] + '_' + str(days) + os.path.splitext(heatwave_file.name)[1]
            output_file = 'Extreme Weather/Prolonged Heatwave/' + file_name

            with open(input_file, "wb") as f:
                f.write(heatwave_file.getbuffer())

            extend_heatwave(input_file, output_file, days)
            st.session_state['created_prolonged_heatwave'] = True
            st.session_state['prolonged_heatwave_output_file'] = output_file
            st.session_state['prolonged_heatwave_file_name'] = file_name

        if st.session_state.created_prolonged_heatwave:
            buffer = get_file_buffer(st.session_state.prolonged_heatwave_output_file)
            st.download_button(
                label="Download EPW file",
                data=buffer,
                file_name=st.session_state.prolonged_heatwave_file_name,
                mime="text/plain"
            )

    st.subheader('Future Heatwave Scenario')
    st.markdown("""
                 Please upload exactly three files: a scenario representing a typical year, a heatwave scenario for that climate, and a projected future typical year. This algorithm will create a future heatwave scenario.
                 """)
    weather_files = st.file_uploader('Uplaod Weather Data Files', accept_multiple_files=True, type='epw', key='weather')


    # Process the uploaded files for the Future Heatwave Scenario
    if weather_files and len(weather_files) == 3 and validate_files(weather_files, 'epw'):
        st.markdown('---')
        file_options = [file.name for file in weather_files]

        baseline_weather_file = st.selectbox("Select the Baseline TMY File:", file_options, key='baseline_weather')
        heatwave_scenario_file = st.selectbox("Select the Heatwave Scenario File:", file_options,
                                              key='heatwave_scenario')
        future_tmy_file = st.selectbox("Select the Projected Future TMY File:", file_options, key='future_tmy')

        if st.button('Create Future Heatwave Scenario'):
            # Call a function to process the files and display results
            input_folder = 'Extreme Weather/Input/'

            for file in weather_files:
                input_file = input_folder + file.name
                with open(input_file, "wb") as f:
                    f.write(file.getbuffer())

            file_name = 'Future_Heatwave.epw'
            output_file = 'Extreme Weather/Future Heatwave/' + file_name

            create_future_heatwave(input_folder + baseline_weather_file, input_folder + heatwave_scenario_file, input_folder + future_tmy_file, output_file)

            st.session_state['created_future_heatwave'] = True
            st.session_state['future_heatwave_output_file'] = output_file
            st.session_state['future_heatwave_file_name'] = file_name

        if st.session_state.created_future_heatwave:
            buffer = get_file_buffer(st.session_state.future_heatwave_output_file)
            st.download_button(
                label="Download EPW file",
                data=buffer,
                file_name=st.session_state.future_heatwave_file_name,
                mime="text/plain"
            )

    st.subheader('Urban Heat Island Effect Integration')
    st.markdown("""
                This section allows you to incorporate the Urban Heat Island (UHI) effect. 
                Please upload a weather file and input a value representing the intensity of the UHI effect.
                The output will reflect the weather conditions with the temperature values shifted by the UHI intensity.
                """)

    # File uploader for the UHI scenario
    uhi_file = st.file_uploader('Choose a Weather File for UHI Simulation', accept_multiple_files=False, type='epw',
                                key='uhi')

    # Input for UHI intensity value
    uhi_intensity = st.number_input('Enter the UHI Intensity Value', min_value=0.0, step=0.001, key='uhi_intensity')

    # Process the UHI scenario
    if uhi_file and uhi_intensity is not None:
        if st.button('Create UHI Effect Scenario'):
            input_file = 'Extreme Weather/Input/' + uhi_file.name
            file_name = os.path.splitext(uhi_file.name)[0] + '_UHI_' + str(uhi_intensity) + \
                        os.path.splitext(uhi_file.name)[1]
            output_file = 'Extreme Weather/UHI Effect/' + file_name

            with open(input_file, "wb") as f:
                f.write(uhi_file.getbuffer())

            # Assuming create_uhi_effect is a function you will implement
            include_uhi_effect(input_file, uhi_intensity, output_file)

            st.session_state['created_uhi_scenario'] = True
            st.session_state['uhi_output_file'] = output_file
            st.session_state['uhi_file_name'] = file_name

        if 'created_uhi_scenario' in st.session_state and st.session_state.created_uhi_scenario:
            buffer = get_file_buffer(st.session_state.uhi_output_file)
            st.download_button(
                label="Download EPW File",
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