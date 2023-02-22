from wsgiref.util import request_uri
import pandas as pd
from geopy import distance
from datetime import datetime
from tqdm import tqdm


def impute_distance_preference(demand: pd.DataFrame, postulants: pd.DataFrame, vacancies: pd.DataFrame):
    
    demand["distancePriority"] = False
    print('>>>              CALCULATING DISTANCES              <<<')     
    for index, row in tqdm(postulants.iterrows(), total=postulants.shape[0]):

        ##Extracting info for each postulant
        postulant_id = row["postulantId"]
        postulating_level = demand[demand["postulantId"]==postulant_id].levelId.values[0]
        postulating_grade = demand[demand["postulantId"]==postulant_id].gradeId.values[0]

        postulant_latitude = row["latitude"]
        postulant_longitude = row["longitude"]
        postulant_coordinates = (postulant_latitude, postulant_longitude)

        postulated_schools = demand[demand["postulantId"]==postulant_id].localId.values

        ##Getting all programs that meet the student's postulation grade and level
        possible_programs = vacancies.loc[(vacancies["levelId"]==postulating_level) & (vacancies["gradeId"]==postulating_grade)].copy(deep=True)


        ##Calculating the distance from student's place to each possible school
        possible_programs["distance"] = [distance.distance(postulant_coordinates, (row["latitude"], row["longitude"])).km for index, row in possible_programs.iterrows()]


        ##Sorting by distance
        possible_programs = possible_programs.sort_values(by=["distance"])
        possible_programs["postulantId"] = postulant_id

        ##Removing the programs that the student had already chosen
        programs_already_chosen = possible_programs["localId"].isin(postulated_schools)
        possible_remaining_programs = possible_programs[~programs_already_chosen].copy(deep=True)
        possible_remaining_programs = possible_remaining_programs.drop_duplicates(subset=["localId"])

        ##Adding additional fields that will be necessary to append these schools to the demand table
        possible_remaining_programs["order"] = range(len(postulated_schools)+1, len(postulated_schools)+len(possible_remaining_programs["localId"])+1)  ##the student had already selected some schools. The distance preference order starts after that ones
        possible_remaining_programs["distancePriority"] = True   ##All new schools are imputed by distance
        possible_remaining_programs["priority"] = False  ##None of them has a different type of priority
        possible_remaining_programs["roundNumber"] = 1
        possible_remaining_programs["roundTypeId"] = "R"
        possible_remaining_programs["sendDate"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        
        instant_demand = possible_remaining_programs[["postulantId", "levelId", "gradeId", "order", "serviceId", "annex", "localId", "latitude", "longitude", "priority", "roundNumber", "roundTypeId", "sendDate", "distancePriority"]]

        demand = pd.concat([demand, instant_demand])
        

    demand = demand.sort_values(by=["postulantId","order"])
    return demand
