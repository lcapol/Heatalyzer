##EnergyPlus Simulations
import os
import os.path
import streamlit as st

#Specify path to EnergyPlus executable
eplus_path = '/Applications/EnergyPlus-23-1-0/energyplus'

#Receives an array of output locations where each location contains an in.idf and weather.epw file and runs them all
def BEM_simulation(simulation_folders):

    #Total number of simulations to run
    total_simulations = len(simulation_folders)
    completed_simulations = 0

    #Initialize Streamlit progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    for path in simulation_folders:

        #Update the progress bar
        progress_bar.progress(completed_simulations / total_simulations)
        status_text.text(f'Running simulation {completed_simulations + 1} of {total_simulations}...')

        #Only run EnergyPlus for this configuration if it has not been run before
        if os.path.exists(path + '/eplusout.csv') and not st.session_state.rerun_all:
            completed_simulations += 1
            continue

        weather_path = path + '/weather.epw'
        building_path = path + '/in.idf'

        #Specify and execute command for EnergyPlus simulation
        path = eplus_path + ' -d ' + path.replace(" ", "\ ") + ' -w ' + weather_path.replace(" ", "\ ") + ' -r ' + building_path.replace(" ", "\ ")
        os.system(path)

        completed_simulations += 1

    #Complete the progress bar
    progress_bar.progress(1.0)
    status_text.text(f'Simulation complete. {total_simulations} simulations run.')