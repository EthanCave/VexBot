from sklearn.linear_model import LogisticRegression
import numpy as np
from dotenv import load_dotenv
from typing import Final
import os
import requests
import random as rand
load_dotenv()
APITOKEN: Final[str] = os.getenv('API_KEY')
def train_model(training_data):
    # Training data: [avg_points, autonomous_points, strength_points]
    X = np.array(training_data[:, :-1])
    y = np.array(training_data[:, -1])

    # Create and train logistic regression model
    model = LogisticRegression()
    model.fit(X, y)
    return model

def calculate_odds(model, team1_avg_points, team1_autonomous_points, team1_strength_points,
                   team2_avg_points, team2_autonomous_points, team2_strength_points):
    # Input data: [avg_points, autonomous_points, strength_points]
    X = np.array([[team1_avg_points, team1_autonomous_points, team1_strength_points],
                  [team2_avg_points, team2_autonomous_points, team2_strength_points]])

    # Predict probabilities of winning for each alliance
    alliance1_odds = model.predict_proba([X[0]])[0][0]
    alliance2_odds = model.predict_proba([X[1]])[0][1]
    return alliance1_odds, alliance2_odds

# Function to input training data
def input_training_data():
    
    training_data = []
    winner = 0
    headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {APITOKEN}",
    }
    search_url = f"https://www.robotevents.com/api/v2/events/54751/divisions/1/matches?per_page=250"
    response = requests.get(search_url, headers=headers)
    response.raise_for_status()
    data = response.json()["data"]
    for match in data['data']:
        blue_teams = [team['team']['id'] for team in match['alliances'][0]['teams']]
        red_teams = [team['team']['id'] for team in match['alliances'][1]['teams']]
        blue_score = match['alliances'][0]['score']
        red_score = match['alliances'][1]['score']
        winner = 0 if blue_score > red_score else 1 if red_score > blue_score else rand.randint(0,1)
        average_average_points_red = []
        average_average_points_blue = []
        average_sp_blue = []
        average_sp_red = []
        average_ap_red = []
        average_ap_blue = []
        for team in blue_teams:
            headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {APITOKEN}",
            }
            search_url = f"https://www.robotevents.com/api/v2/teams/{team}/rankings"
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            total_ap = 0
            total_sp = 0
            total_average_points = 0
            total_entries = len(data['data'])

            # Calculate total AP, SP, and average points
            for entry in data['data']:
                total_ap += entry['ap']
                total_sp += entry['sp']
                total_average_points += entry['average_points']

            # Calculate averages
            average_ap_blue.append(total_ap / total_entries)
            average_sp_blue.append(total_sp / total_entries)
            average_average_points_blue.append(total_average_points / total_entries)

        for team in red_teams:
            total_ap = 0
            total_sp = 0
            total_average_points = 0
            total_entries = len(data['data'])

            # Calculate total AP, SP, and average points
            for entry in data['data']:
                total_ap += entry['ap']
                total_sp += entry['sp']
                total_average_points += entry['average_points']

            # Calculate averages
            average_ap_red.append(total_ap / total_entries)
            average_sp_red.append(total_sp / total_entries)
            average_average_points_red.append(total_average_points / total_entries)
        

        
    training_data.append([(average_average_points_blue/2), (average_ap_blue/2), (average_sp_blue/2), team2_avg_points, team2_autonomous_points, team2_strength_points,winner])
    return np.array(training_data)

# Input training data from user
training_data = input_training_data()

# Train the model
model = train_model(training_data)

# Example usage
team1_avg_points = float(input("Enter team 1 average points: "))
team1_autonomous_points = float(input("Enter team 1 autonomous points: "))
team1_strength_points = float(input("Enter team 1 strength points: "))

team2_avg_points = float(input("Enter team 2 average points: "))
team2_autonomous_points = float(input("Enter team 2 autonomous points: "))
team2_strength_points = float(input("Enter team 2 strength points: "))

alliance1_odds, alliance2_odds = calculate_odds(model, team1_avg_points, team1_autonomous_points, team1_strength_points,
                                                team2_avg_points, team2_autonomous_points, team2_strength_points)

print("Alliance 1 Odds:", alliance1_odds)
print("Alliance 2 Odds:", alliance2_odds)
