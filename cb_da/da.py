'''
File: da.py
Created Date: Saturday April 3rd 2021 12:38
Author: Benjamín Madariaga
Company: Consilium Bots Inc.
Modified By:  Benjamín Madariaga at b.madariaga.e@gmail.com
'''

from cb_da.entities.policymaker import PolicyMaker


def da(vacancies, applicants, applications, priority_profiles, quota_order, 
        siblings=None,
        links=None,
        order= 'descending',
        sibling_priority_activation= False,
        linked_postulation_activation= False,
        secured_enrollment_assignment= False,
        forced_secured_enrollment_assignment= False,
        transfer_capacity_activation= False):
    '''
    Main method for the application of Deferred Acceptance Algorithm
    '''
    config_file = {'order': order,# Orden en el que se corre el algoritmo
                    'sibling_priority_activation': sibling_priority_activation, # Para activar prioridad de hermano entre niveles y tipos de asignación (NEE y Regular.)
                    'linked_postulation_activation': linked_postulation_activation, # Para activar postulación en bloque
                    'secured_enrollment_assignment': secured_enrollment_assignment, # Para activar el uso de secured enrollment
                    'forced_secured_enrollment_assignment': forced_secured_enrollment_assignment, # Para forzar la asignación SE en caso de no haber cupos
                    'transfer_capacity_activation': transfer_capacity_activation}
    print('*******************************************************')
    print('*******************************************************')
    print('>>> SCHOOL MATCHING ALGORITHM  <<<')
    print('>>> CONSILIUM BOTS INC.  <<<')
    print('*******************************************************')
    print('*******************************************************')

    print('*******************************************************')
    print('*******************************************************')
    print('>>> CONFIGURATION DETAILS <<<')
    print('Order: ', config_file['order'])
    print('Dynamic Sibling Priority: ',
        config_file['sibling_priority_activation'])
    print('Family Application: ',
        config_file['linked_postulation_activation'])
    print('Students with Secured Enrollment: ',
        config_file['secured_enrollment_assignment'])
    print('Forced Secured Enrollment: ',
        config_file['forced_secured_enrollment_assignment'])
    print('Transfer Capacity: ',
        config_file['transfer_capacity_activation'])
    print('*******************************************************')
    print('*******************************************************')

    print('>> Loading and preparing data')

    policy_maker = PolicyMaker(vacancies = vacancies,
                                applicants = applicants,
                                applications = applications,
                                priority_profiles = priority_profiles,
                                quota_order = quota_order,
                                siblings = siblings,
                                links = links,
                                config = config_file)

    print('>> Starting matching algorithm')
    policy_maker.match_applicants_and_programs()
    print('>> Getting results')

    output = policy_maker.get_results()

    print('*******************************************************')
    print('*******************************************************')
    print('>>> SCHOOL MATCHING ALGORITHM   <<<')
    print('>>> CONSILIUM BOTS INC.  <<<')
    print('*******************************************************')
    print('*******************************************************')
    return output
