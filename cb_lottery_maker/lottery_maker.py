'''
File: lottery_maker.py
Created Date: Wednesday July 28th 2021 15:48
Author: Benjamín Madariaga
Company: Consilium Bots Inc.
Modified By:  Benjamín Madariaga at b.madariaga.e@gmail.com
'''

from cb_lottery_maker.entities.lottery import Lottery


def lottery_maker(applicants, applications,
        siblings = None,
        tie_break_method:str = 'single',
        tie_break_level:str = '',
        sibling_lottery:bool = False,
        seed:float = 0):
    '''
    Main method for the generation of Lottery numbers.
    '''
    config_file = {'tie_break_method': tie_break_method,
                    # Takes values 'single' or 'multiple'
                    'tie_break_level': tie_break_level,
                    # Takes values 'program' or 'quota'.
                    # Necessary only if tie_break_method='multiple'
                    'sibling_lottery': sibling_lottery,
                    # If true siblings in same grade will be assigned (almost)
                    # same lottery
                    'seed': seed
                    # Seed for replication
                    }
    print('*******************************************************')
    print('*******************************************************')
    print('>>> LOTTERY MAKER <<<')
    print('>>> CONSILIUM BOTS INC.  <<<')
    print('*******************************************************')
    print('*******************************************************')

    print('*******************************************************')
    print('*******************************************************')
    print('>>> CONFIGURATION DETAILS <<<')
    print('Tie Break method: ', config_file['tie_break_method'])
    print('Tie Break level: ', config_file['tie_break_level'])
    print('Sibling lottery: ', config_file['sibling_lottery'])
    print('Seed: ', config_file['seed'])
    print('*******************************************************')
    print('*******************************************************')

    print('>> Loading and preparing data')

    lottery = Lottery(applicants = applicants,
                        applications = applications,
                        siblings = siblings,
                        config = config_file)

    print('>> Running Lottery')
    lottery.run()

    print('>> Get Output')
    output = lottery.get_output()

    print('*******************************************************')
    print('*******************************************************')
    print('>>> LOTTERY MAKER <<<')
    print('>>> CONSILIUM BOTS INC.  <<<')
    print('*******************************************************')
    print('*******************************************************')
    return output
