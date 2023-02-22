# Este codigo tiene que correrse en el repositorio de cb-da
from cb_da import da
from cb_lottery_maker import lottery_maker
from entities.data_processing import data_preparation, output_preparation
import pandas as pd
import os

##------------------------------------------------------------------------------------##
# Seleccionar directorio que contiene los archivos: demand.csv, vacancies.csv, postulants.csv, postulation.csv
##------------------------------------------------------------------------------------##

dir = '/Users/oscar/OneDrive/Escritorio/ensayis_verificacion_DA/calculando_distancia/'

##------------------------------------------------------------------------------------##

processed_dir = data_preparation(dir, type="calculated_distance")

applicants = pd.read_csv(processed_dir+'applicants.csv',dtype={'secured_enrollment_program_id':int,'secured_enrollment_quota_id':int})
vacancies = pd.read_csv(processed_dir+'vacancies.csv')
applications = pd.read_csv(processed_dir+'applications.csv')
priority_profiles = pd.read_csv(processed_dir+'priority_profiles.csv')
quota_order = pd.read_csv(processed_dir+'quota_order.csv')
siblings = pd.read_csv(processed_dir+'siblings.csv')
links = pd.read_csv(processed_dir+'links.csv')


# In case lotteries don't come with the data
if not  'lottery_number_quota' in applications.columns:

    ##Considering that the application necessarily brings distance column
    applications_with_distance = applications.loc[applications.distance]
    applications_without_distance = applications.loc[~applications.distance]
    # Here goes the lottery maker
    applications_with_distance = lottery_maker(applicants = applicants, applications = applications_with_distance, siblings = siblings,
                tie_break_method = 'single',
                sibling_lottery = False,
                seed = 2021)
    applications_without_distance = lottery_maker(applicants = applicants, applications = applications_without_distance, siblings = siblings,
                tie_break_method = 'multiple',
                tie_break_level = 'program',
                sibling_lottery = True,
                seed = 2021)
    applications = pd.concat((applications_with_distance,applications_without_distance))

results = da(vacancies=vacancies,
            applicants=applicants,
            applications=applications,
            priority_profiles=priority_profiles,
            quota_order=quota_order,
            siblings=siblings,
            links=links,
            #order='descending', (This is commented because descendent is the default. Options are 'ascending' or 'descending')
            sibling_priority_activation= False,
            linked_postulation_activation= True,
            secured_enrollment_assignment= False,
            forced_secured_enrollment_assignment= False,
            transfer_capacity_activation= True)

asignaciones, applications_with_lottery = output_preparation(results, applications, dir)

asignaciones.to_csv(dir+'asignaciones.csv',index=False)
applications_with_lottery.to_csv(dir+'lottery_numbers.csv',index=False)

os.remove(processed_dir+'applicants.csv')
os.remove(processed_dir+'vacancies.csv')
os.remove(processed_dir+'applications.csv')
os.remove(processed_dir+'priority_profiles.csv')
os.remove(processed_dir+'quota_order.csv')
os.remove(processed_dir+'siblings.csv')
os.remove(processed_dir+'links.csv')
os.rmdir(processed_dir)