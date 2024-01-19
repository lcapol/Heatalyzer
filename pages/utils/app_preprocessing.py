##Preprocess Building Data for EnergyPlus simulation

from eppy import idf_helpers
from eppy.modeleditor import IDF
import sys


#IDD file to use
iddfile = '/Applications/EnergyPlus-23-1-0/Energy+.idd'

def preprocess(simulation_folders):

    nr_simulations = len(simulation_folders)

    IDF.setiddname(iddfile)

    for i in range(nr_simulations):

        simulation_folder = simulation_folders[i]

        ##Preprocess Building Data

        #Explore/Modify the given idf file
        idf_file = IDF(simulation_folder + '/in.idf')

        define_runperiod(idf_file)

        #Remove all variables that are output and only insert the ones I am interested in for my simulations
        define_output(idf_file)

        #Add specifications to enable thermal comfort calculation (PMV, SET, WBGT)
        add_thermal_comfort(idf_file)

        #Replace the current idf file with the updated one
        idf_file.save(simulation_folder + "/in.idf")


def define_runperiod(idf_file):

    # Get all RUNPERIOD objects
    runperiods = idf_file.idfobjects['RUNPERIOD']

    # Keep only the first RUNPERIOD object and set its dates
    if runperiods:
        first_runperiod = runperiods[0]
        first_runperiod.Begin_Month = 1
        first_runperiod.Begin_Day_of_Month = 1
        first_runperiod.End_Month = 12
        first_runperiod.End_Day_of_Month = 31

        # Delete all other RUNPERIOD objects
        for runperiod in runperiods[1:]:
            idf_file.removeidfobject(runperiod)

#Define thermal comfort model outputs to report and include assumptions for the models
def define_output(idf_file):

    #Clear all Output:Tables, Output:Variables, and Output:Meter
    prefixes_to_remove = ['OUTPUT:TABLE', 'OUTPUT:VARIABLE', 'OUTPUT:METER']
    for prefix_to_remove in prefixes_to_remove:
        idf_obj = idf_helpers.getidfobjectlist(idf_file)
        objects_to_remove = [obj.key.upper() for obj in idf_obj if obj.key.upper().startswith(prefix_to_remove)]

        for obj in objects_to_remove:
            idf_file.popidfobject(obj, 0)

    #Specify the output values EnergyPlus should report for our thermal comfort models

    idf_file.newidfobject('OUTPUT:VARIABLE', Key_Value="*",
                          Variable_Name="Zone Mean Air Temperature",
                          Reporting_Frequency="Hourly")

    idf_file.newidfobject('OUTPUT:VARIABLE', Key_Value="*",
                          Variable_Name="Zone Air Relative Humidity",
                          Reporting_Frequency="Hourly")

    idf_file.newidfobject('OUTPUT:VARIABLE', Key_Value="*",
                          Variable_Name='Zone Thermal Comfort Fanger Model PMV',
                          Reporting_Frequency="Hourly")

    idf_file.newidfobject('OUTPUT:VARIABLE', Key_Value="*",
                          Variable_Name='Zone Thermal Comfort Fanger Model PPD',
                          Reporting_Frequency="Hourly")

    idf_file.newidfobject('OUTPUT:VARIABLE', Key_Value="*",
                          Variable_Name='Zone Thermal Comfort Pierce Model Standard Effective Temperature',
                          Reporting_Frequency="Hourly")

    idf_file.newidfobject('OUTPUT:VARIABLE', Key_Value="*",
                          Variable_Name='Zone Thermal Comfort Mean Radiant Temperature',
                          Reporting_Frequency="Hourly")


#Add necessary assumtions for SET and PMV thermal comfort models
def add_thermal_comfort(idf_file):

    people = idf_file.idfobjects['People']

    # Names of schedules to be added or replaced
    schedule_names = ['WORK_EFF_SCH', 'CLOTHING_SCH', 'AIR_VELO_SCH']

    # Remove existing schedules with the same names
    for schedule_name in schedule_names:
        schedules = idf_file.idfobjects['SCHEDULE:COMPACT']
        for schedule in schedules:
            if schedule.Name == schedule_name:
                idf_file.removeidfobject(schedule)

    # Define working efficiency level schedule
    idf_file.newidfobject('Schedule:Compact',
                          Name='WORK_EFF_SCH',
                          Schedule_Type_Limits_Name="Any Number",
                          Field_1='Through: 12/31',
                          Field_2='For: AllDays',
                          Field_3='Until: 24:00',
                          Field_4=str(0.0))

    #Define clothing insulation schedule
    idf_file.newidfobject('Schedule:Compact',
                          Name='CLOTHING_SCH',
                          Schedule_Type_Limits_Name="Any Number",
                          Field_1='Through: 03/31',
                          Field_2='For: AllDays',
                          Field_3='Until: 24:00',
                          Field_4=str(1.0),
                          Field_5='Through: 09/30',
                          Field_6='For: AllDays',
                          Field_7='Until: 24:00',
                          Field_8=str(0.5),
                          Field_9='Through: 12/31',
                          Field_10='For: AllDays',
                          Field_11='Until: 24:00',
                          Field_12=str(1.0)
    )

    #define air velocity schedule
    idf_file.newidfobject('Schedule:Compact',
                          Name='AIR_VELO_SCH',
                          Schedule_Type_Limits_Name="Any Number",
                          Field_1='Through: 12/31',
                          Field_2='For: AllDays',
                          Field_3='Until: 24:00',
                          Field_4=str(0.15))

    #Adjust the People object for each zone
    for people_obj in people:
        people_obj.Name = people_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name
        people_obj.Work_Efficiency_Schedule_Name = 'WORK_EFF_SCH'
        people_obj.Mean_Radiant_Temperature_Calculation_Type = 'ZoneAveraged'
        people_obj.Clothing_Insulation_Calculation_Method = 'ClothingInsulationSchedule'
        people_obj.Clothing_Insulation_Schedule_Name = 'CLOTHING_SCH'
        people_obj.Air_Velocity_Schedule_Name = 'AIR_VELO_SCH'
        people_obj.Thermal_Comfort_Model_1_Type = 'FANGER'
        people_obj.Thermal_Comfort_Model_2_Type = 'PIERCE'


if __name__ == '__main__':

    simulation_folders = sys.argv[1]
    preprocess(simulation_folders)

