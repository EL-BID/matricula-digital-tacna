'''
File: match.py
Created Date: Friday September 11th 2020 12:03:54
Author: Ignacio Riveros
Company: Consilium Bots Inc.
Modified By: Benjamín Madariaga at b.madariaga.e@gmail.com
'''

from typing import Any, Dict, Tuple
import math

from cb_da.entities.programs import Program
from cb_da.entities.applicants import Applicant


class DeferredAcceptanceAlgorithm:
    def __init__(self):
        pass

    def run(self,
            applicants: Dict[int, Applicant],
            programs: Dict[Tuple[int, int], Program]) -> None:
        '''
        Run Deferred Acceptance matching algorithm

        Args:
            applicants (dict): Applicants to be matched
            programs (dict): Programs to be matched
        '''
        remaining_proposals = list(applicants.values())
        while len(remaining_proposals)>0:
            # Get next proposing applicant
            # applicant = remaining_proposals.pop(0)
            applicant = remaining_proposals.pop()
            if not applicant.match:
                # We get program and quota id that uses position n
                program_id = applicant.vpostulation[applicant.option_n]
                quota_id = applicant.vquota_id[applicant.option_n]
                program_pointer = (program_id, quota_id)
                try:
                    rejected_applicant = (DeferredAcceptanceAlgorithm
                                        .match_applicant_to_program(
                                            applicant,
                                            programs,
                                            program_pointer))
                except:
                    raise ValueError(f'Error while assigning applicant\
                        :{applicant.id} to program:{program_pointer}')
                if rejected_applicant:
                    rejected_applicant.option_n += 1

                    if (rejected_applicant.option_n <
                            len(rejected_applicant.vpostulation)):
                        (DeferredAcceptanceAlgorithm.
                            unmatch_applicant_of_program(
                            rejected_applicant))
                        remaining_proposals.append(rejected_applicant)
                    else:
                        (DeferredAcceptanceAlgorithm
                            .applicant_match_with_None_program(
                            rejected_applicant))

    @staticmethod
    def match_applicant_to_program(
            applicant: Applicant,
            programs: Dict[Tuple[Any, int], Program],
            program_pointer: Tuple[Any, int]) -> Any:
        '''
        Match applicant to program and quota if he/she got the score to enter
        the Applicant_Queue, and reject another (or him(her)self) if
        requirements are not met.

        Args:
            applicant (Applicant): Applicant to be match.
            programs (Dict[Tuple[Any, int], Program]): All programs.
            program_pointer (Tuple[Any, int]): Program and quota where the
                applicant is applying.

        Returns:
            Any: Applicant or None
        '''
        # Sacamos el programa del diccionario de todos los programas.
        program = programs[program_pointer]
        rejected_applicant = None
        # Ocupar cupos que van quedando remanentes en el assignment.
        assigned_applicants = program.get_assignment_type_queue(
                                assignment_type=applicant.special_assignment)

        try:
            new_applicant_score = \
                program.get_applicant_score_in_program(applicant)
        except:
            raise ValueError(f'Error while getting score in vpostulation\
            :{applicant.vpostulation} and vquota:{applicant.vquota_id}')
        cut_off_score = assigned_applicants.get_cut_off_score()

        # Caso donde no se ha llegado al límite de capacidad.
        if (cut_off_score == 0):
            applicant.match = True
            applicant.assigned_vacancy = program
            assigned_applicants.add_applicant_to_program(applicant)
            assigned_applicants.add_score_to_program(new_applicant_score)

        # Caso de que el programa no tiene cupos (i.e. Capacidad 0)
        elif math.isinf(cut_off_score):
            rejected_applicant = applicant
            rejected_score = new_applicant_score

        # Caso donde se ha llegado al límite de capacidad.
        else:
            # El cutoff le gana a la propuesta
            if (cut_off_score <= new_applicant_score):
                rejected_applicant = applicant
                rejected_score = new_applicant_score

            # La propuesta le gana al cutoff
            elif (new_applicant_score < cut_off_score):
                # Estudiante con el mínimo numero de prioridad
                cut_off_applicant = assigned_applicants.get_cut_off_applicant(
                    cut_off_score)

                applicant.match = True
                applicant.assigned_vacancy = program
                assigned_applicants.reassign_applicants_and_scores(
                    applicant,
                    new_applicant_score,
                    cut_off_applicant)
                rejected_applicant = cut_off_applicant
                rejected_score = cut_off_score
        if rejected_applicant:
            program.add_applicant_to_waitlist(rejected_applicant,rejected_score//1)
        programs[program_pointer] = program
        return rejected_applicant

    @staticmethod
    def unmatch_applicant_of_program(applicant: Applicant) -> None:
        '''
        If applicant was rejected or removed from a prog,
        unmatch he/she of the program.

        Args:
            applicant (Applicant): rejected applicant
        '''
        applicant.match = False
        applicant.assigned_vacancy = None

    @staticmethod
    def applicant_match_with_None_program(applicant: Applicant) -> None:
        '''
        Applicants with no match are matched to None program.

        Args:
            applicant (Applicant): rejected applicant of all his/her proposals.
        '''
        applicant.match = True
        applicant.assigned_vacancy = None
