from sklearn import linear_model
from dotenv import load_dotenv
import requests
import random as rand
import os
import pandas as pd
import time
load_dotenv()

API_KEYS = [os.getenv('API_KEY_1'), os.getenv('API_KEY_2')]
API_KEY = os.getenv('API_KEY')  # List of API keys

def input_training_data(event_ids):
    # Initialize lists to store data
    data = []
    match_numbers = []
    team_ids = []
    winners = []

    for event_id in event_ids:
        # Switch between API keys for each event
        for idx, api_key in enumerate(API_KEYS):
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            search_url = f"https://www.robotevents.com/api/v2/events/{event_id}/divisions/1/matches?per_page=250"
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            matches_data = response.json()['data']

            # Dictionary to store team data
            team_data_cache = {}

            # Process matches
            for i, match in enumerate(matches_data, start=1):
                blue_teams = [team['team']['id'] for team in match['alliances'][0]['teams']]
                red_teams = [team['team']['id'] for team in match['alliances'][1]['teams']]
                blue_score = match['alliances'][0]['score']
                red_score = match['alliances'][1]['score']
                winner = 0 if blue_score > red_score else 1 if red_score > blue_score else rand.randint(0, 1)

                for team_id in blue_teams + red_teams:
                    if team_id not in team_data_cache:
                        team_data_cache[team_id] = get_team_data(team_id, api_key)

                    data.append(team_data_cache[team_id])
                    match_numbers.append(i)
                    team_ids.append(team_id)
                    winners.append(0 if (winner == 0 and team_id in blue_teams) or (winner == 1 and team_id in red_teams) else 1)

            # Introduce a delay between events
            if idx < len(API_KEYS) - 1:
                print(f"Switching API keys. Waiting for 30 seconds...")
                time.sleep(30)  # Wait for 30 seconds
    # Create DataFrame from collected data
    df = pd.DataFrame(data)

    # Add match number, team IDs, and winner columns
    df['Match_Number'] = match_numbers
    df['Team_ID'] = team_ids
    df['Winner'] = winners

    # Save DataFrame to CSV
    df.to_csv('training_data.csv', index=False)
def get_team_data(team_id,):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    search_url = f"https://www.robotevents.com/api/v2/teams/{team_id}/rankings"
    response = requests.get(search_url, headers=headers)
    response.raise_for_status()
    team_data = response.json()['data']

    # Initialize variables to store data
    total_ap = 0
    total_sp = 0
    total_average_points = 0
    total_entries = 0

    # Calculate total AP, SP, and average points
    for entry in team_data:
        if 'ap' in entry and 'sp' in entry and entry.get('average_points') is not None:
            total_ap += entry['ap']
            total_sp += entry['sp']
            total_average_points += entry['average_points']
            total_entries += 1

    # Calculate averages
    average_ap = total_ap / total_entries if total_entries > 0 else 0
    average_sp = total_sp / total_entries if total_entries > 0 else 0
    average_average_points = total_average_points / total_entries if total_entries > 0 else 0

    return {'Average_AP': average_ap, 'Average_SP': average_sp, 'Average_Average_Points': average_average_points}


# input_training_data([54751, 51498,54176])  # Pass a list of event IDs to process
