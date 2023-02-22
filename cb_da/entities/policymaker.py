'''
File: policymaker.py
Created Date: Sunday September 13th 2020 5:06:11
Author: Ignacio Riveros
Company: Consilium Bots Inc.
Modified By:  Benjamín Madariaga at b.madariaga.e@gmail.com
'''

from typing import Any, Dict, Tuple, List
import pandas as pd
import numpy as np

from cb_da.entities.programs import Program
from cb_da.entities.applicants import Applicant
from cb_da.entities.match import DeferredAcceptanceAlgorithm


class PolicyMaker:
    '''
    Prepare applicants and programs to be matched under a set of rules.
    '''
    def __init__(
            self,
            vacancies: pd.DataFrame,
            applicants: pd.DataFrame,
            applications: pd.DataFrame,
            priority_profiles: pd.DataFrame,
            quota_order: pd.DataFrame,
            siblings: pd.DataFrame,
            links: pd.DataFrame,
            config: Dict[str, Any]
            ) -> None:
        '''
        Args:
            vacancies (pd.DataFrame): DataFrame with vacancies info.
            applicants (pd.DataFrame): DataFrame with postulants info.
            applications (pd.DataFrame): DataFrame with applications info.
            priority_profiles (pd.DataFrame): DataFrame with priority_profiles
                info.
            quota_order (pd.DataFrame): DataFrame with quota_order info.
            siblings (pd.DataFrame): DataFrame with siblings info.
            links (pd.DataFrame): DataFrame with links info.
            config (Dict): Dict with the set of rules fro the match
        '''
        self.config = config
        self._unpack_priority_profiles(priority_profiles)
        self._unpack_quota_order(quota_order)
        self._set_rules()
        self.algorithm = DeferredAcceptanceAlgorithm()
        applicants = self._add_sibling_and_linked_data(applicants=applicants,
                                                        siblings=siblings,
                                                        links=links)
        applicants = self._add_postulation_data(applicants=applicants,
                                                applications=applications)
        self.applicants_df = self._init_applicants(applicants=applicants)
        self.programs_df = self._init_programs(programs=vacancies)

        self.applicants = self._get_applicants_dict()
        self.programs = self._get_programs_dict()

        self.ordered_grades = self._get_ordered_grades()
        self.assignment_types = self._get_assignment_types()
        self.first_round = self.ordered_grades[0]
        self.last_round = self.ordered_grades[-1]
        self.results: Dict[str, pd.DataFrame] = {}


    def match_applicants_and_programs(self) -> None:
        '''
        Match applicants and program objects, adjusting sibling priority,
        postulation order, linked postulation and secured enrollment between
        rounds according to the rules in config.
        '''
        for grade in self.ordered_grades:
            for assignment_type in self.assignment_types:

                applicants_to_be_assigned = \
                    self._prep_applicants_for_matching(
                        grade=grade,
                        assignment_type=assignment_type)

                try:
                    self.algorithm.run(applicants=applicants_to_be_assigned,
                                   programs=self.programs)
                except:
                    raise ValueError(f'Error while assigning grade:{grade} and \
                    assignment_type:{assignment_type}')

                self._after_round_adjustments(
                    applicants_to_be_assigned=applicants_to_be_assigned,
                    grade=grade,
                    assignment_type=assignment_type)



    def get_results(self) -> pd.DataFrame:
        '''
        Return a DataFrame with the assignation results
        '''
        def yield_applicants():
            for applicant in self.applicants.values():
                dict={'applicant_id':applicant.id}
                dict['grade_id'] = applicant.grade
                prog = applicant.assigned_vacancy
                if prog is None:
                    dict['program_id'] = None
                    dict['institution_id'] = None
                    dict['quota_id'] = None
                    dict['assigned_score'] = None
                    dict['priority_profile'] = None
                else:
                    dict['program_id'] = prog.program_id
                    dict['institution_id'] = prog.institution_id
                    dict['quota_id'] = prog.quota_id
                    dict['assigned_score'] = prog.get_applicant_score_in_program(applicant)
                    dict['priority_profile'] = applicant.vpriority_profile[prog.program_id]
                yield dict
        results = pd.DataFrame(yield_applicants())
        return results

    def _init_applicants(
            self,
            applicants: pd.DataFrame) -> pd.DataFrame:
        '''
        Init all applicants objects in a df

        Args:
            applicants (pd.DataFrame): raw applicants dataframe

        Returns:
            pd.DataFrame: applicants df ready to used in matching
        '''
        self.applicant_characteristics = [col for col in applicants.columns \
            if 'applicant_characteristic' in col]
        applicants['secured_enrollment_program_id'] = applicants['secured_enrollment_program_id'].fillna(0)
        if not 'vdistance' in applicants.columns:
            applicants["vdistance"] = ""
        applicants['applicant_object'] = \
            applicants.apply(self._init_applicant_object, axis=1)
        return applicants

    def _init_programs(
            self,
            programs: pd.DataFrame) -> pd.DataFrame:
        '''
        Init all program objects in a df

        Args:
            programs (pd.DataFrame): raw programs dataframe

        Returns:
            pd.DataFrame: programs df ready to used in matching
        '''
        self.special_assignment_cols = [col for col in programs.columns \
            if 'special' in col]
        programs['program_object'] = \
            programs.apply(self._init_program_object, axis=1)
        return programs

    def _get_applicants_dict(
            self,
            query: str = '') -> Dict[int, Applicant]:
        '''
        Returns the applicants as dict according to a query.

        Returns:
            Dict[int, Applicant]: {Applicant_id: Applicant_object}
        '''

        applicants_df = self.applicants_df
        if len(query) > 0:
            applicants_df = applicants_df.query(query)
        return (applicants_df[['applicant_id', 'applicant_object']]
                .set_index('applicant_id')
                .to_dict(orient='dict'))['applicant_object']

    def _get_programs_dict(self) -> Dict[Tuple[int, int], Program]:
        '''
        Returns the applicants as dict according to a query.

        Returns:
            Dict[Tuple[int, int], Program]: {(Program_id,Program_Quota_id): \
            Program_object}
        '''
        return (self.programs_df[['program_id', 'quota_id','program_object']]
                .set_index(['program_id', 'quota_id'])
                .to_dict()['program_object'])

    def _set_rules(self):
        '''
        Set rules of the school assignment according to config
        '''
        self._order = self.config['order']

        self._sibling_priority_activation = \
            self.config['sibling_priority_activation']
        self._linked_postulation_activation = \
            self.config['linked_postulation_activation']
        self._transfer_capacity_activation = \
            self.config['transfer_capacity_activation']
        self._secured_enrollment_activation = \
            self.config['secured_enrollment_assignment']
        self._forced_secured_enrollment_activation = \
            self.config['forced_secured_enrollment_assignment']

    def _get_ordered_grades(self) -> List:
        '''
        Get the set of grades ordered dependign on the rules

        Returns:
            List: ordered grades
        '''
        grades = list(set(self.applicants_df.grade_id))
        if self._order == 'descending':
            grades.sort(reverse=True)
        else:
            grades.sort()
        return grades

    def _get_assignment_types(self) -> List[int]:
        '''
        Get the types of assignment for run the algorithm. The order to process
        special assignment is 1 to n, and then 0.

        Returns:
            List[int]: assignment_types
        '''
        assignment_types = [int(column.split('_')[1])
            for column in self.special_assignment_cols]
        assignment_types.sort()
        return assignment_types+[0]

    def _prep_applicants_for_matching(
            self,
            grade: int,
            assignment_type: int) -> Dict[int, Applicant]:
        '''
        Considering what happen in last rounds, prepare the subset of
        applicants to be matched.

        Args:
            grade (int)
            assignment_type (int)
        '''
        q1 = (f'((grade_id == {grade}) &'
              f' (special_assignment == {assignment_type}))')
        stus_to_be_assigned_df = self.applicants_df.query(q1)
        stus_to_be_assigned_se_df = stus_to_be_assigned_df[
                stus_to_be_assigned_df.secured_enrollment_program_id!=0]
        if grade != self.first_round:
            # Dynamic sibling priority
            if (self._sibling_priority_activation):
                stus_to_be_assigned_df.loc[:, 'applicant_object'].apply(
                  self._apply_sib_priority)
        if grade != self.first_round:
            # reorder postulation
            if (self._linked_postulation_activation):
                stus_to_be_assigned_df.loc[:, 'applicant_object'].apply(
                    self._apply_linked_reorder)
        # #Get the right quota postulation order
        stus_to_be_assigned_df.loc[:, 'applicant_object'].apply(
        self._check_quota_postulation_order)
        if (self._secured_enrollment_activation):
            stus_to_be_assigned_se_df.loc[:, 'applicant_object'].apply(
                lambda applicant: \
                applicant.set_secured_place_as_last_postulation())
        return self._get_applicants_dict(query=q1)

    def _after_round_adjustments(
            self,
            applicants_to_be_assigned: Dict[int, Applicant],
            grade: int,
            assignment_type: int) -> None:
        '''
        Considering what happen in the last round, transfer capacities
        and force secured enrollment

        Args:
            applicants_to_be_assigned (Dict[int, Applicant])
            grade (int)
            assignment_type (int)
        '''
        if (assignment_type != 0) and (self._transfer_capacity_activation):
            self._reasign_programs_capacity(current_grade=grade,
                                            assignment_type=assignment_type)

        if (self._forced_secured_enrollment_activation):
            subset = applicants_to_be_assigned.keys()
            applicants_with_se = \
                (self.applicants_df
                [self.applicants_df.applicant_id.isin(subset)])
            applicants_with_se = applicants_with_se[
                applicants_with_se.secured_enrollment_program_id!=0]

            (applicants_with_se.loc[:, 'applicant_object']
             .apply(self._match_secured_enrollment_applicant))

    def _apply_sib_priority(
            self,
            applicant: Applicant) -> None:
        '''
        Search all the siblings of a applicant. If they are matched in schools
        that are inside the postulation of the applicant, change vpriorities.

        Args:
            applicant (Applicant)
        '''
        if len(applicant.vsiblings) > 0:
            schools_with_sib = set()
            for sibling_id in applicant.vsiblings:  # Check all the siblings
                # Get the sibling from applicants graph
                sibling = self.applicants[sibling_id]
                # Check if the sibling is alredy matched to some program.
                if (sibling.match) and (sibling.assigned_vacancy is not None):
                    # Give me the school where the sibling was accepted and
                    # append it to the array.
                    schools_with_sib.add(
                        sibling.assigned_vacancy.institution_id)

            applicant_schools_ids = applicant.vinstitution_id
            # Return the indexes of applicant_schools_ids where there is
            # coincidence with schools_with_sib
            indexes_to_change_sibling_priority = [i for i, id in
                enumerate(applicant_schools_ids) if id in schools_with_sib]

            # We loop over all the indexes to change priority
            for index in indexes_to_change_sibling_priority:
                applicant.reasign_priority_profile(index,
                    self.priority_profile_transition)


    def _apply_linked_reorder(
            self,
            applicant: Applicant) -> None:
        '''
        Check if a applicant has linked applicants that were match to
        a program, and reorder the postulation of the applicant, considering
        his/her preferences and the schools that coincide with their
        assigned linked applicants.

        Args:
            applicant (Applicant)
        '''
        if len(applicant.vlinks) > 0:
            schools_with_linked = set()
            linked_grades = set()
            # Check all the linked postulations
            for link_applicant_id in applicant.vlinks:
                # Get the linked applicant from applicants graph
                linked = self.applicants[link_applicant_id]
                # Check if the linked is alredy matched to some program.
                if (linked.match) and (linked.assigned_vacancy is not None):
                    # Give me the school where the linked was accepted and
                    # append it to the array.
                    schools_with_linked.add(
                                linked.assigned_vacancy.institution_id)
                    linked_grades.add(
                                linked.assigned_vacancy.grade_id)

            #Translate the array vpostulation from program_id to institution_id
            imputed_applications = applicant.vdistance
            applicant_schools_ids = applicant.vinstitution_id
            linked_grades = list(linked_grades)

            # Indexes of applicant_schools_ids where there is coincidence
            # with schools_with_linked, ordered from more to least preferred
            if len(imputed_applications) > 0:     
                indexes_to_put_in_first_place = [i for i, id in \
                    enumerate(applicant_schools_ids) if id in schools_with_linked and imputed_applications[i] == 0]
            else:
                indexes_to_put_in_first_place = [i for i, id in \
                    enumerate(applicant_schools_ids) if id in schools_with_linked]

            # Indexes of applicant_schools_ids where there is NO coincidence
            # with schools_with_linked, ordered from more to least preferred
            indexes_to_put_after_first_place = [i for i in \
                range(len(applicant_schools_ids)) if i \
                not in indexes_to_put_in_first_place]

            new_postulation_arrays_order = indexes_to_put_in_first_place + \
                                            indexes_to_put_after_first_place
            # Reorder postulation in applicant object
            applicant.reorder_postulation(linked_grades,
                                        new_postulation_arrays_order)


    def _check_quota_postulation_order(
            self,
            applicant: Applicant) -> None:
        '''
        Check the postulation order of student and correct it following the
        info from self.quota_order_dict. This modifies the quota postulation
        order, but not the program postulation order

        Args:
            applicant (Applicant)
        '''
        # If the applicant has a priority that needs reorder
        if not set(applicant.vpriority_profile.values()).isdisjoint(self.quota_order_dict_keys):
            #Get the programs where the student has such priority
            programs_to_modify = [program_id for program_id,priority_profiles in applicant.vpriority_profile.items() if priority_profiles in self.quota_order_dict_keys]

            for program_id in programs_to_modify:
                # Loop over all programs that need reorder
                priority_profile = applicant.vpriority_profile[program_id]
                pp_quota_order = self.quota_order_dict[priority_profile].copy()
                secured_enrollment_indicator = \
                    (applicant.se_program_id==program_id)
                # Check criteria
                for _,pp_dict in pp_quota_order.items():
                    # Check SE criteria
                    if pp_dict['secured_enrollment_indicator'] \
                        !=secured_enrollment_indicator:
                        continue
                    if secured_enrollment_indicator:
                        if not applicant.check_se_quota_id_criteria(
                            criteria=
                                pp_dict['secured_enrollment_quota_id_criteria'],
                            value=pp_dict['secured_enrollment_quota_id_value']):
                            continue
                    # Check other characteristics criteria
                    aux_attribute_criteria=True
                    for applicant_characteristic in \
                        self.quota_order_characteristics:
                        if not applicant.check_attribute_criteria(
                            attribute=applicant_characteristic,
                            criteria=
                                pp_dict[f'{applicant_characteristic}_criteria'],
                            value=pp_dict[f'{applicant_characteristic}_value']):
                            aux_attribute_criteria=False
                            break
                    if not aux_attribute_criteria:
                        continue
                    # If satisfies all criterias, reorder the quotas
                    applicant.reorder_postulation_by_quota(
                        program_id=program_id,
                        ordered_quotas=pp_dict['ordered_quotas'])


    def _reasign_programs_capacity(
            self,
            current_grade: int,
            assignment_type: int) -> None:
        '''
        Transfer capacity from assignment type n to regular assignment.

        Args:
            current_grade (int): int
        '''
        for program in self.programs.values():
            if (program.grade_id != current_grade):
                continue

            capacity_to_transfer = \
                program.get_capacity_to_transfer(
                                from_assignment_type=assignment_type)
            if (capacity_to_transfer == 0):
                continue
            program.transfer_capacity(capacity_to_transfer=capacity_to_transfer)

    def _match_secured_enrollment_applicant(
            self,
            applicant: Applicant) -> None:
        '''
        Description: match a applicant with secure enrollment to his/her
        secured option in case he/she didn't match any program.
        This method changes atributtes of Applicant and Program Object.

        Args:
            applicant (Applicant)
        '''
        # Applicant match to None program
        if (applicant.match) & (applicant.assigned_vacancy is None):
            secured_program = self.programs[(applicant.se_program_id,
                                             applicant.se_quota_id)]

            secured_program._force_secured_enrollment_match(
                applicant)
            applicant.match = True
            applicant.assigned_vacancy = secured_program


    def _init_applicant_object(self, row: pd.DataFrame) -> Applicant:
        '''
        From applicants dataframe row, init an applicant object.

        Args:
            row (pd.DataFrame): Row of applicants dataframe

        Returns:
            Applicant: applicant object
        '''
        aux_dict = row.to_dict()
        applicant_characteristics= {key:aux_dict[key] for key in self.applicant_characteristics}
        applicant = Applicant(applicant_id=aux_dict['applicant_id'],
                      grade=aux_dict['grade_id'],
                      se_program_id=aux_dict['secured_enrollment_program_id'],
                      se_quota_id=aux_dict['secured_enrollment_quota_id'],
                      links=aux_dict['links'],
                      siblings=aux_dict['siblings'],
                      vpostulation=aux_dict['vpostulation'],
                      vpostulation_scores=aux_dict['vpostulation_scores'],
                      vinstitution_id=aux_dict['vinstitution_id'],
                      vpriorities=aux_dict['vpriorities'],
                      vquota_id=aux_dict['vquota_id'],
                      vdistance=aux_dict['vdistance'],
                      vpriority_profile=aux_dict['vpriority_profile'],
                      special_assignment=aux_dict['special_assignment'],
                      applicant_characteristics=applicant_characteristics)
        return applicant


    def _init_program_object(self, row: pd.DataFrame) -> Program:
        '''
        From vacancies dataframe row, init a program object.

        Args:
            row (pd.DataFrame): Row of programs dataframe

        Returns:
            Program: program object
        '''
        aux_dict = row.to_dict()
        special_vacancies= {key:aux_dict[key] for key in self.special_assignment_cols}
        prog = Program(program_id=aux_dict['program_id'],
                       institution_id=aux_dict['institution_id'],
                       grade_id=aux_dict['grade_id'],
                       quota_id=aux_dict['quota_id'],
                       regular_capacity=aux_dict['regular_vacancies'],
                       special_vacancies=special_vacancies)
        return prog

    def _add_sibling_and_linked_data(
            self,
            applicants: pd.DataFrame,
            siblings: pd.DataFrame,
            links: pd.DataFrame) -> pd.DataFrame:
        '''
        Group by applicant_id, siblings and linked data
        in list to merge it with applicants data

        Args:
            applicants(pd.DataFrame): Applicants df
            siblings(pd.DataFrame): Siblings df
            links(pd.DataFrame): Links df

        Returns:
            applicants(pd.DataFrame): Updated version of the DataFrame
        '''
        #We use a numpy level groupby.agg(list)
        def gb_list(df,col_a,col_b):
            keys, values = df.sort_values(col_a).values.T
            ukeys, index = np.unique(keys, True)
            arrays = np.split(values, index[1:])
            df2 = pd.DataFrame({col_a:ukeys, col_b:[list(a) for a in arrays]}).set_index(col_a)
            return df2

        if self._linked_postulation_activation:
            assert isinstance(links,pd.DataFrame), 'Expected links dataframe when linked_postulation_activation is on. Turn it off or provide a links dataframe.'
        else:
            if not isinstance(links,pd.DataFrame):
                links = pd.DataFrame({'applicant_id':[],'linked_id':[]})
        if len(links)==0:
            links_gb = links.rename(columns={'linked_id': 'links'}).set_index('applicant_id')
        else:
            assert (('applicant_id' in links.columns) and ('linked_id' in links.columns) and (len(links.columns)==2)), 'Unexpected columns in links dataframe. Expected ¨applicant_id¨ and ¨linked_id¨.'
            links_gb = gb_list(links,'applicant_id','links')


        if self._sibling_priority_activation:
            assert isinstance(siblings,pd.DataFrame), 'Expected siblings dataframe when sibling_priority_activation is on. Turn it off or provide a siblings dataframe.'
        else:
            if not isinstance(siblings,pd.DataFrame):
                siblings = pd.DataFrame({'applicant_id':[],'sibling_id':[]})
        if len(siblings)==0:
            siblings_gb = siblings.rename(columns={'sibling_id': 'siblings'}).set_index('applicant_id')
        else:
            assert (('applicant_id' in siblings.columns) and ('sibling_id' in siblings.columns) and (len(siblings.columns)==2)), 'Unexpected columns in siblings dataframe. Expected ¨applicant_id¨ and ¨sibling_id¨.'
            siblings_gb = gb_list(siblings,'applicant_id','siblings')

        applicants = applicants.join(links_gb,on='applicant_id')
        applicants = applicants.join(siblings_gb,on='applicant_id')


        for col_label in ['links', 'siblings']:
            applicants[col_label] = applicants[col_label].apply(lambda d: \
                d if isinstance(d, list) else [])

        return applicants

    def _add_postulation_data(
            self,
            applicants: pd.DataFrame,
            applications: pd.DataFrame) -> pd.DataFrame:
        '''
        Transform and groupby applications data to merge it with
        applicants data


        Args:
            applicants(pd.DataFrame): Applicants df
            applications(pd.DataFrame): Applications df

        Returns:
            applicants(pd.DataFrame): Updated version of the DataFrame
        '''
        #We use a numpy level groupby.agg(list)
        def gb_list(df):
            aux_values = df.values.T
            other_col_names = df.columns[1:]
            keys = aux_values[0,:]
            values = aux_values[1:,:]
            ukeys, index = np.unique(keys, return_index=True, axis=0)
            # split data columns according to those indices
            arrays = np.split(values, index[1:], axis=1)
            idx = pd.Index(ukeys.T,name='applicant_id')
            list_agg_vals = dict()
            for tup in zip(*arrays, other_col_names):
                col_vals = tup[:-1] # first entries are the subarrays from above
                col_name = tup[-1]  # last entry is data-column name

                list_agg_vals[col_name] = col_vals

            df2 = pd.DataFrame(data=list_agg_vals,index=idx)
            return df2

        #Postulations for same program are ordered by quota id. This is then
        # modified by _prep_applicants_for_matching()
        applications = applications.sort_values(['applicant_id',
                                                    'ranking_program',
                                                    'quota_id'])

        applications = applications.rename(\
            columns={'program_id':'vpostulation',
                        'lottery_number_quota':'vpostulation_scores',
                        'priority_number_quota':'vpriorities',
                        'institution_id':'vinstitution_id',
                        'quota_id':'vquota_id',
                        'priority_profile_program':'vpriority_profile'})

        assert applications.vpostulation.isna().sum()==0, 'There are Nan program ids in applications dataframe'
        assert applications.vpostulation_scores.isna().sum()==0, 'There are Nan lottery numbers in applications dataframe'

        int_vcolumns = ['vpostulation',
                    'vinstitution_id',
                    'vpriorities',
                    'vquota_id',
                    'vpriority_profile']
        if 'distance' in applications.columns:
            applications["vdistance"] = applications["distance"].astype(int)
            int_vcolumns.append('vdistance')
        float_vcolumns = ['vpostulation_scores']
        applications = applications[['applicant_id']+float_vcolumns+int_vcolumns]
        grouped_int = gb_list(applications[['applicant_id']+int_vcolumns])
        grouped_float = gb_list(applications[['applicant_id']+float_vcolumns])

        applicants = applicants.join(grouped_int,on='applicant_id')
        applicants = applicants.join(grouped_float,on='applicant_id')

        return applicants


    def _unpack_priority_profiles(
            self,
            priority_profiles: pd.DataFrame) -> None:
        '''
        Save the number of quotas and priority transitions from the
        priority profiles dataframe.

        Args:
            priority_profiles(pd.DataFrame): Priority_profiles df
        '''
        self.n_quotas = len([col for col in priority_profiles.columns \
            if 'priority_q' in col])
        self.priority_profile_transition = \
            priority_profiles.set_index(['priority_profile']).to_dict()

    # CHANGE=True
    def _unpack_quota_order(
            self,
            quota_order: pd.DataFrame) -> None:
        '''
        Save the rules for reordering the quota postulation from the
        quota order dataframe.

        Args:
            quota_order(pd.DataFrame): Quota_order df
        '''
        aux_quota_order = quota_order.set_index(['priority_profile'],append=True)
        self.quota_order_dict = {pp:aux_quota_order.xs(pp, level=1).to_dict('index')
                                    for pp in list(set(aux_quota_order.index.get_level_values(1)))}
        self.quota_order_dict_keys = set(self.quota_order_dict.keys())

        #
        self.quota_order_characteristics=list(set(col.rsplit('_', 1)[0]
            for col in quota_order if 'applicant_characteristic' in col))
        self.quota_order_ordercolumns=list(set(col
            for col in quota_order if 'order' in col))
        #
        for pp,pp_quota_order in self.quota_order_dict.items():
            for _,pp_dict in pp_quota_order.items():
                aux_dict = {int(key[-1]):pp_dict[key] for key in self.quota_order_ordercolumns}
                sorted_quotas = [key for (key,value) in sorted(aux_dict.items(), key=lambda x: x[1])]
                pp_dict.update({'ordered_quotas':sorted_quotas})
                for key in self.quota_order_ordercolumns:
                    pp_dict.pop(key)


    def reset_matching(self):
        '''
        Resets both programs and applicants
        '''
        for program in self.programs.values():
            program._reset_matching_attributes()
        for applicant in self.applicants.values():
            applicant._reset_matching_attributes()
