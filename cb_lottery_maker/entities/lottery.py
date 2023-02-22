'''
File: lottery_maker.py
Created Date: Wednesday July 28th 2021 15:48
Author: Benjamín Madariaga
Company: Consilium Bots Inc.
Modified By: Benjamín Madariaga at b.madariaga.e@gmail.com
'''


import sys
from typing import Dict, List

import numpy as np
import pandas as pd

global epsilon
# Python solo representa hasta 15 decimales de forma confiable.
epsilon = sys.float_info.epsilon


class Lottery():
    def __init__(self,
                applicants:pd.DataFrame,
                applications:pd.DataFrame,
                siblings:pd.DataFrame,
                config:Dict) -> None:
        '''
        Init a Lottery instance. Its the main instance with methods for reading
        applicants, applications and siblings, run the lottery and getting
        outputs.

        Args:
            applicants (pd.DataFrame): Dataframe of applicants according to
            readme indications.
            applications (pd.DataFrame): Dataframe of applications according to
            readme indications.
            siblings (pd.DataFrame): Dataframe of siblings according to
            readme indications.
            config (Dict): Config rules
        '''
        self.config = config
        self._set_rules()
        self._read_applications_data(applicants=applicants,
                                    applications=applications)
        self._read_siblings_data(siblings = siblings)

    def run(self)-> None:
        '''
        Searches the appropriate lottery method an executes it.
        '''
        self.tie_break_function = self.get_tie_break_function()
        for applicant_id,application in self.applications_dict.items():
            self.tie_break_function(applicant_id,application)

    def get_output(self) -> pd.DataFrame:
        '''
        Generates a DataFrame similar to applications, but with the
        corresponding lottery number.

        Returns:
            output (pd.DataFrame): Dataframe with lottery
        '''
        new_dict = {(applicant_id,program_id):program_application
                for applicant_id,application in self.applications_dict.items()
                for (program_id,_),program_application in application.items() }
        output = pd.DataFrame.from_dict(new_dict,'index')
        output.index = output.index.set_names(['applicant_id','program_id'])
        output = output.set_index(['institution_id','ranking_program'],
                                    append=True) \
                                    .apply(pd.Series.explode) \
                                    .reset_index()
        output = output.merge(self.applications)
        output = output.astype(self.applications_dtypes)
        output['lottery_number_quota'] = output['lottery_number_quota'].astype(float)
        return output

    def _set_rules(self) -> None:
        '''
        Set rules of the school assignment according to config
        '''
        self._tie_break_method = self.config['tie_break_method']
        self._tie_break_level = self.config['tie_break_level']
        self._sibling_lottery = self.config['sibling_lottery']
        self._seed = self.config['seed']

        np.random.seed(self._seed)
        self._assert_rules()

    def _assert_rules(self) -> None:
        '''
        Make sure the rules make sense
        '''
        if self._tie_break_method not in ['single','multiple']:
            raise ValueError(f'Tie break method "{self._tie_break_method}"\
             is not supported. Please enter "single" or "multiple".')
        if self._tie_break_method=='multiple':
            if self._tie_break_level not in ['program','quota']:
                raise ValueError(f'Tie break level "{self._tie_break_level}"\
                 is not supported. Please enter "program" or "quota".')
        if type(self._sibling_lottery)!= bool:
            raise ValueError(f'Sibling Lottery parameter must be bool')

    def _read_siblings_data(
            self,
            siblings: pd.DataFrame) -> None:
        '''
        Group siblings by applicant_id in lists. Creates siblings dict
        with siblings of each applicant.

        Args:
            siblings(pd.DataFrame): Siblings df
        '''
        if self._sibling_lottery:
            if not isinstance(siblings,pd.DataFrame):
                raise ValueError('Expected siblings DataFrame when sibling_lottery is on. Turn it off or provide a siblings DataFrame.')
            if not (('applicant_id' in siblings.columns) and ('sibling_id' in siblings.columns) and (len(siblings.columns)==2)):
                raise ValueError('Unexpected column in siblings DataFrame. Expected "applicant_id" and "sibling_id".')

            siblings_gb = siblings.groupby('applicant_id')['sibling_id'].apply(list)

            self.siblings_dict = siblings_gb.to_dict()
            self.siblings_dict.update({id:[] for id in self.applications_dict.keys()
                                        if id not in self.siblings_dict.keys()})
        else:
            self.siblings_dict = None

    def _read_applications_data(
            self,
            applicants: pd.DataFrame,
            applications: pd.DataFrame) -> None:
        '''
        Group applications by applicant_id. Creates applications dict with
        applications of each applicant. It assumes that each quota appears once
        per program.

        Args:
            applicants (pd.DataFrame): Applicants df
            applications (pd.DataFrame): Applications df
        '''
        self.applications = applications.copy()
        self.applications_dtypes = applications.dtypes
        quotas = list(applications.quota_id.unique())
        quotas.sort()
        aux_applications = applications[['applicant_id',
                                            'institution_id',
                                            'program_id',
                                            'ranking_program']]
        aux_applications = aux_applications.drop_duplicates() \
                                    .set_index(['applicant_id','program_id']) \
                                    .sort_index()
        aux_applicants = applicants[['applicant_id',
                                        'grade_id']].set_index('applicant_id')
        aux_applications = aux_applications.join(aux_applicants,how='inner') \
                                            .set_index('grade_id',append=True)

        applications_dict = {ind:{} for ind in aux_applicants.index}
        aux_dict = aux_applications.to_dict('index')

        for (applicant_id,program_id,grade_id),program_application in \
                                                        aux_dict.items():
            program_application.update({'lottery_number_quota':[0]*len(quotas),
                                                    'quota_id':quotas})
            applications_dict[applicant_id].update(
                                {(program_id,grade_id):program_application})

        self.applications_dict = applications_dict



    def get_tie_break_function(self):
        '''
        Depending on the rules set, returns the suitable method to
        generate lottery numbers.

        Returns:
            Lottery method
        '''
        if self._tie_break_method=='single':
            return self._get_single_tie_break_lottery
        elif self._tie_break_method=='multiple':
            if self._tie_break_level=='program':
                return self._get_program_multiple_tie_break_lottery
            elif self._tie_break_level=='quota':
                return self._get_quota_multiple_tie_break_lottery
            else:
                raise ValueError(f'Tie break level "{self._tie_break_level}"\
                 is not supported.')
        else:
            raise ValueError(f'Tie break method "{self._tie_break_method}"\
             is not supported.')


    def _get_quota_multiple_tie_break_lottery(
            self,
            applicant_id,
            application: Dict) -> None:
        '''
        Description: Creates a random Lottery number (0 to 1)
        for each quota in each program in the application.
        If sibling lottery is true,
        propagates the lottery number through the siblings

        Args:
            applicant_id : Hashable
            application (Dict): Item of application dict
        '''
        siblings_list = self.siblings_dict[applicant_id] if \
                            self._sibling_lottery else []
        for (program_id,grade_id),program_application in application.items():
            if (0 in program_application['lottery_number_quota']):
                lotterynumbers = list(np.random.random(
                                        len(program_application['quota_id'])))
                program_application['lottery_number_quota'] = lotterynumbers
                if len(siblings_list) > 0:
                    for sibling_id in siblings_list:
                        self.propagate_multiple_lottery(sibling_id,
                                                        program_id,
                                                        grade_id,
                                                        lotterynumbers)


    def _get_program_multiple_tie_break_lottery(
            self,
            applicant_id,
            application: Dict) -> None:
        '''
        Description: Creates a random Lottery number (0 to 1)
        for each program in the application.
        If sibling lottery is true,
        propagates the lottery number through the siblings

        Args:
            applicant_id : Hashable
            application (Dict): Item of application dict
        '''
        siblings_list = self.siblings_dict[applicant_id] if \
                            self._sibling_lottery else []
        for (program_id,grade_id),program_application in application.items():
            if (0 in program_application['lottery_number_quota']):
                lotterynumbers = [np.random.random()]* \
                                        len(program_application['quota_id'])
                program_application['lottery_number_quota'] = lotterynumbers
                if len(siblings_list) > 0:
                    for sibling_id in siblings_list:
                        self.propagate_multiple_lottery(sibling_id,
                                                        program_id,
                                                        grade_id,
                                                        lotterynumbers)


    def _get_single_tie_break_lottery(
            self,
            applicant_id,
            application: Dict) -> None:
        '''
        Description: Creates a random Lottery number (0 to 1)
        for each applicant.
        If sibling lottery is true,
        propagates the lottery number through the siblings

        Args:
            applicant_id : Hashable
            application (Dict): Item of application dict
        '''
        siblings_list = self.siblings_dict[applicant_id] if \
                            self._sibling_lottery else []
        if self.zero_in_lottery(application):
            lotterynumber = np.random.random()
            for (_,grade_id),program_application in application.items():
                program_application['lottery_number_quota'] = [lotterynumber]* \
                                            len(program_application['quota_id'])
            if len(siblings_list) > 0:
                for sibling_id in siblings_list:
                    self.propagate_single_lottery(sibling_id,
                                                    grade_id,
                                                    lotterynumber)

    def zero_in_lottery(self,
            application: Dict) -> bool:
        '''
        True if there is a program_id which has no lottey number, else False.

        Returns:
            Bool
        '''
        for (program_id,grade_id),program_application in application.items():
            if (0 in program_application['lottery_number_quota']):
                return True
        return False

    def propagate_multiple_lottery(self,
            sibling_id,
            program_id,
            grade_id,
            lotterynumbers: List) -> None:
        '''
        If the sibling's grade is same as grade_id, the program_id is in the
        sibling's application and such application has no lottery numbers, then
        sets such lottery as lotterynumbers and continues on to the next
        sibling. If any of the conditions is not met, the propagation stops.

        Args:
            sibling_id: Hashable.
            program_id: Hashable.
            grade_id: Numeric.
            lotterynumbers (List): List of lottery numbers
        '''
        sib_application = self.applications_dict[sibling_id]
        if (program_id,grade_id) in sib_application.keys():

            sib_program_application = sib_application[(program_id,grade_id)]
            if (0 in sib_program_application['lottery_number_quota']):
                # Epsilon times a random number from uniform [-10,10] dist
                sibling_tiebreak = round((np.random.rand()-0.5)*20,2)*epsilon
                # sibling_tiebreak = np.random.choice([-1,1])*epsilon
                sib_program_application['lottery_number_quota'] = \
                                    [l+sibling_tiebreak for l in lotterynumbers]
                for new_sibling_id in self.siblings_dict[sibling_id]:
                    self.propagate_multiple_lottery(new_sibling_id,
                                                    program_id,
                                                    grade_id,
                                                    lotterynumbers)


    def propagate_single_lottery(self,
            sibling_id,
            grade_id,
            lotterynumber: List) -> None:
        '''
        If the sibling's grade is same as grade_id and there is any program
        application without lotter lotterynumbers, then sets all lottery as
        lotterynumbers and continues on to the next sibling. If any of the
        conditions is not met, the propagation stops.

        Args:
            sibling_id: Hashable.
            grade_id: Numeric.
            lotterynumbers (List): List of lottery numbers
        '''
        sib_application = self.applications_dict[sibling_id]
        _,sib_grade_id = next(iter(sib_application.keys()))
        if sib_grade_id==grade_id:
            if self.zero_in_lottery(sib_application):
                # Epsilon times a random number from uniform [-1,1] dist
                sibling_tiebreak = (np.random.rand()-0.5)*2*epsilon
                for (sib_program_id,sib_grade_id),sib_program_application in \
                                                        sib_application.items():
                    sib_program_application['lottery_number_quota'] = \
                                    [lotterynumber+sibling_tiebreak]* \
                                    len(sib_program_application['quota_id'])
                for new_sibling_id in self.siblings_dict[sibling_id]:
                    self.propagate_single_lottery(new_sibling_id,
                                                    grade_id,
                                                    lotterynumber)
    def reset_lottery_numbers(self):
        '''
        Sets all lottery numbers to 0.
        '''
        for applicant_id,application in self.applications_dict.items():
            for (program_id,grade_id),program_application in application.items():
                program_application['lottery_number_quota'] = [0]* \
                                        len(program_application['quota_id'])
