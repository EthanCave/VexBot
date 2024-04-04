import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error
import numpy as np
import matplotlib.pyplot as plt
from linear2 import get_team_data  # Assuming you have defined this function
import joblib
from dotenv import load_dotenv
import os

# Load data into DataFrame
load_dotenv()
API_KEY = [os.getenv('API_KEY')] 
data = pd.read_csv("training_data.csv")

# Select features (Average_AP, Average_SP, Average_Average_Points) and target variable (Winner)
X = data[['Average_AP', 'Average_SP', 'Average_Average_Points']]
y = data['Winner']

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

# Train a Gradient Boosting model
model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=1)
model.fit(X_train, y_train)
joblib.dump(model, 'gradient_boosting_model.pkl')

# Make predictions
y_pred = model.predict(X_test)

# Calculate mean squared error
mse = mean_squared_error(y_test, y_pred)
print("Mean Squared Error:", mse)

# Example prediction for a new set of VEX team data
team_data = [166511, 139407, 153257, 159215]
new_team_data = []
for team in team_data:
    team_data_inv = get_team_data(team)
    new_team_data.append(team_data_inv)

# Create DataFrame with feature names
feature_names = ['Average_AP', 'Average_SP', 'Average_Average_Points']
new_team_df = pd.DataFrame(new_team_data, columns=feature_names)

predicted_win_probability = model.predict(new_team_df)

# Aggregate probabilities for each alliance
blue_alliance_prob = np.mean(predicted_win_probability[:2])
red_alliance_prob = np.mean(predicted_win_probability[2:])

# Normalize probabilities
total_prob = blue_alliance_prob + red_alliance_prob
blue_alliance_prob_normalized = blue_alliance_prob / total_prob
red_alliance_prob_normalized = red_alliance_prob / total_prob

print("Predicted win probability for Blue Alliance (normalized):", blue_alliance_prob_normalized)
print("Predicted win probability for Red Alliance (normalized):", red_alliance_prob_normalized)

# Plot
alliances = ['Blue Alliance', 'Red Alliance']
win_probabilities = [blue_alliance_prob_normalized, red_alliance_prob_normalized]
plt.bar(alliances, win_probabilities, color=['blue', 'red'])
plt.xlabel('Alliance')
plt.ylabel('Win Probability')
plt.title('Predicted Win Probability for Each Alliance')
plt.ylim(0, 1)  # Set y-axis limit to 0-1 for probability interpretation
plt.show()
