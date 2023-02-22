'''
File: Applicant.py
Created Date: Thursday May 13th 2021
Author: Benjamín Madariaga
Company: Consilium Bots Inc.
'''
from typing import Any, List, Dict
import numpy as np
import pandas as pd
import operator

eval_dict={'<':operator.lt,
            '<=':operator.le,
            '>':operator.gt,
            '>=':operator.ge,
            '=':operator.eq,
            '!=':operator.ne,
            '==':operator.eq,
            'le':operator.lt,
            'leq':operator.le,
            'ge':operator.gt,
            'geq':operator.ge,
            'eq':operator.eq,
            'neq':operator.ne}


class Applicant():
    def __init__(self,
                 applicant_id: Any,
                 special_assignment: int,
                 grade: int,
                 links: List[Any],
                 siblings: List[Any],
                 vpostulation: List[Any],
                 vpostulation_scores: List[float],
                 vinstitution_id: List[Any],
                 vpriorities: List[int],
                 vquota_id: List[int],
                 vpriority_profile: List[int],
                 vdistance: List[int],
                 se_program_id: int = 0,
                 se_quota_id: int = 0,
                 applicant_characteristics ={}):
        '''
        Init a Applicant instance.

        Args:
            applicant_id (Any): Hashable
            special_assignment (int): Indicate the applicants type of assignment
            grade (int):
            links (List[Any]): List of applicant_id
            siblings (List[Any]): List of applicant_id
            vpostulation (List[Any]): List of program_id where to apply
            vpostulation_scores (List[float]): List of scores
            vinstitution_id (List[Any]): List of institution_id
            vpriorities (List[int]): List of priorities
            vquota_id (List[int]): List of quotas associated with vpostulation
            vpriority_profile (List[int]): List of priorities associated with
                vpostulation
            se_program_id (int): 0 or program_id
            se_quota_id (int): 0 or quota_id
            applicant_characteristics (dict, optional): Dictionary with
                aditional characteristics needed for the assignment
        '''
        self.__id = applicant_id
        self.__special_assignment = special_assignment
        self.__grade = grade
        self.__vsiblings = siblings
        self.__vlinks = links
        self.__vdistance = vdistance
        self.__original_vpostulation = vpostulation
        self.__original_vinstitution_id = vinstitution_id
        self.__original_vquota_id = vquota_id
        # self.__original_vpostulation_scores = {(program_id,quota_id):postulation_score for program_id,quota_id,postulation_score in zip(vpostulation,vquota_id,vpostulation_scores)}
        # self.__original_vpriorities = {(program_id,quota_id):priority for program_id,quota_id,priority in zip(vpostulation,vquota_id,vpriorities)}
        aux_dict_1 = {program_id:{} for program_id in vpostulation}
        for program_id,quota_id,postulation_score in zip(vpostulation,vquota_id,vpostulation_scores):
            aux_dict_1[program_id].update({quota_id:postulation_score})
        self.__original_vpostulation_scores = aux_dict_1
        aux_dict_2 = {program_id:{} for program_id in vpostulation}
        for program_id,quota_id,priority in zip(vpostulation,vquota_id,vpriorities):
            aux_dict_2[program_id].update({quota_id:priority})
        self.__original_vpriorities = aux_dict_2
        self.__original_vpriority_profile = {program_id:priority_profiles for program_id,priority_profiles in zip(vpostulation,vpriority_profile)}
        self.__se_program_id = se_program_id if (se_program_id!=0) else None
        self.__se_quota_id = se_quota_id if (se_program_id!=0) else None

        if len(applicant_characteristics)>0:
            self._unpack_applicant_characteristics(applicant_characteristics)

        self._reset_matching_attributes()
        # self._init_priority_and_score_method()


    @property
    def id(self):
        return self.__id

    @property
    def special_assignment(self):
        return self.__special_assignment

    @property
    def grade(self):
        return self.__grade

    @property
    def vsiblings(self):
        return self.__vsiblings

    @property
    def vlinks(self):
        return self.__vlinks

    @property
    def se_program_id(self):
        return self.__se_program_id

    @property
    def vdistance(self):
        return self.__vdistance

    @property
    def se_quota_id(self):
        return self.__se_quota_id


    def modify_original_vpostulation_scores(
            self,
            program_id,quota_id,lottery) -> None:
        '''
        Modifies the original_vpostulation_scores and sets new_vpostulation_scores as score

        Args:
            original_vpostulation_scores_to_be_transfered (int): Capacity to be added
        '''
        # self.__original_vpostulation_scores[(program_id,quota_id)] = lottery
        self.__original_vpostulation_scores[program_id][quota_id] = lottery


    def _unpack_applicant_characteristics(
            self,
            applicant_characteristics) -> None:
        '''
        Description: Set all applicant_characteristics as attributes

        Args:
            applicant_characteristics (dict): Each key,value pair represents a
                applicant characteristic
        '''
        # for columns,value in applicant_characteristics.iteritems():
        #     setattr(self, columns, value)
        for key,value in applicant_characteristics.items():
            setattr(self, key, value)

    def _reset_matching_attributes(self) -> None:
        '''
        Reset all attributes related to matching algorithm.
        '''
        self.vpostulation = self.__original_vpostulation.copy()
        self.vinstitution_id = self.__original_vinstitution_id.copy()
        self.vquota_id = self.__original_vquota_id.copy()
        self.vpostulation_scores = self.__original_vpostulation_scores.copy()
        self.vpriorities = self.__original_vpriorities.copy()
        self.vpriority_profile = self.__original_vpriority_profile.copy()
        self.option_n = 0
        self.match = False
        self.dynamic_priority = [False]*len(self.vpostulation)
        self.linked_postulation = False
        self.assigned_vacancy = None
        self.linked_postulation_bool = False
        self.cut_postulation = False
        self.reassign_quota_order = False


    def reasign_priority_profile(
            self,
            index: int,
            transition: Dict) -> None:
        '''
        Modifies the priority profile in the index position using transition.

        Args:
            index (int): Index to modify
            transition (Dict): Dictionary with transitions according to
                priority profiles. This transition comes from priority_profiles
                DataFrame.
        '''
        program_id = self.vpostulation[index]
        quota_id = self.vquota_id[index]
        priority_profile = self.vpriority_profile[program_id]
        new_priority_profile = \
            transition['priority_profile_sibling_transition'][priority_profile]
        self.vpriority_profile[program_id] = new_priority_profile
        # self.vpriorities[(program_id,quota_id)] = \
        #     transition[f'priority_q{quota_id}'][new_priority_profile]
        self.vpriorities[program_id][quota_id] = \
            transition[f'priority_q{quota_id}'][new_priority_profile]
        self.dynamic_priority[index] = True

    def reorder_postulation(
            self,
            linked_grades: List,
            new_postulation_arrays_order: List) -> None:
        '''
        Description: Save the linked_grades in self, save the original
        postulation arrays and reorder them.

        Args:
            linked_grades (List): List with all the linked grades
            new_postulation_arrays_order (List): List with indexes to
            reorder postulation arrays.
        '''
        self.linked_postulation_bool = True
        # Keep a register of the linked levels
        self.linked_grades = linked_grades

        # Reorder postulation arrays
        self.vpostulation = \
            self.vpostulation[new_postulation_arrays_order]
        self.vinstitution_id = \
            self.vinstitution_id[new_postulation_arrays_order]
        self.vquota_id = \
            self.vquota_id[new_postulation_arrays_order]

    def set_secured_place_as_last_postulation(self) -> None:
        '''
        Drop the postulation arrays elements that are after secured enrollment.
        '''
        self.cut_postulation = True
        try:
            last_post_index = \
                np.where(self.vpostulation == self.__se_program_id)[0][-1]
        except:
            raise ValueError(f'Applicant {self.id} does not have the SE program {self.__se_program_id} in vpostulation.')
        #The +1 ensures that [:last_index] includes the SE program
        last_index = last_post_index+1
        # Keep only the postulation that are at the left of the
        # last secured program index
        self.vpostulation = self.vpostulation[:last_index]
        self.vinstitution_id = self.vinstitution_id[:last_index]
        self.vquota_id = self.vquota_id[:last_index]

    def check_se_quota_id_criteria(self,
            criteria: str,
            value) -> bool:
        '''
        Evaluates the criteria string and compares self.se_quota_id
        with value.

        Returns:
            bool: True if criteria is met.
        '''
        return eval_dict[criteria](self.se_quota_id,value)

    def check_attribute_criteria(self,
            attribute:str,
            criteria:str,
            value) -> bool:
        '''
        Evaluates the criteria string and compares self.atrribute
        with value.

        Returns:
            bool: True if criteria is met.
        '''
        attr = getattr(self, attribute)
        return eval_dict[criteria](attr,value)

    def reorder_postulation_by_quota(self,
            program_id: Any,
            ordered_quotas: List):
        '''
        Reorders the postulation to program_id using the order_df dataframe.
        Modifies vpriorities, vpostulation_scores and vquota_id.

        Args:
            program_id (Any): Hashable present in vpostulation
            ordered_quotas (List): List containing the proper quota order.
        '''
        indexes_to_modify = np.where(self.vpostulation==program_id)[0]
        if len(indexes_to_modify)!=len(ordered_quotas):
            postulation_quotas = self.vquota_id[indexes_to_modify]
            self.vquota_id[indexes_to_modify]=[q for q in ordered_quotas if q in postulation_quotas]
        else:
            self.vquota_id[indexes_to_modify]=ordered_quotas


    def _init_priority_and_score_method(self):
        '''
        '''
        unique_scores = list(set(self.__original_vpostulation_scores.values()))
        if len(unique_scores)==1:
            def get_vpostulation_scores(*args):
                return unique_scores[0]
            self.get_vpostulation_scores = get_vpostulation_scores
            return
        unique_vpostulation = np.unique(self.__original_vpostulation)
        if len(unique_scores)==len(unique_vpostulation):
            aux_dict = {program_id:postulation_score for (program_id,quota_id),postulation_score in self.__original_vpostulation_scores.items()}
            def get_vpostulation_scores(pointer):
                return aux_dict[pointer[0]]
            self.get_vpostulation_scores = get_vpostulation_scores
            return
        else:
            def get_vpostulation_scores(pointer):
                return self.__original_vpostulation_scores[pointer]
            self.get_vpostulation_scores = get_vpostulation_scores
        return
