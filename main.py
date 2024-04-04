import requests
import discord
from discord.ext import commands
from typing import Final
import os
from dotenv import load_dotenv
import re
import asyncio
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from test import *
import numpy as np
import joblib

def get_team_data(team_id):
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {APITOKEN}",
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


model = joblib.load('linear_regression_model.pkl')
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
APITOKEN: Final[str] = os.getenv('API_KEY')

DatabaseURL: Final[str] = os.getenv('DB_URL')
cred = credentials.Certificate(KEY)
databaseApp = firebase_admin.initialize_app(cred, {
    'databaseURL' : DatabaseURL
})
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".",intents=intents)

def get_team_id(team_number):
    headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {APITOKEN}",
    }
    search_url = f"https://www.robotevents.com/api/v2/teams?number%5B%5D={team_number}&myTeams=false"
    response = requests.get(search_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if data and data["data"]:
        return data["data"][0]["id"]
    else:
        return None

def calculate_overall_win_rate(data, team_name):
    wins = 0
    losses = 0
    
    for match in data:
        for alliance in match['alliances']:
            for team_data in alliance['teams']:
                if team_data['team']['name'] == team_name:
                    team_score = alliance['score']
                    opponent_score = match['alliances'][1 if alliance['color'] == 'blue' else 0]['score']
                    if team_score > opponent_score:
                        wins += 1
                    else:
                        losses += 1
        
    total_matches = wins + losses
    if total_matches > 0:
        overall_win_rate = round((wins / total_matches) * 100, 2)
    else:
        overall_win_rate = None
    
    return {'wins': wins, 'losses': losses, 'win_rate': overall_win_rate}

def calculate_event_win_rates(data, team_name):
    win_rates = {}
    
    for match in data:
        event_name = match['event']['name']
        wins = 0
        losses = 0
        found_team = False
        
        for alliance in match['alliances']:
            for team_data in alliance['teams']:
                if team_data['team']['name'] == team_name:
                    found_team = True
                    team_score = alliance['score']
                    opponent_score = match['alliances'][1 if alliance['color'] == 'blue' else 0]['score']
                    
                    if team_score > opponent_score:
                        wins += 1
                    else:
                        losses += 1
        
        if found_team:
            if event_name not in win_rates:
                win_rates[event_name] = {'wins': 0, 'losses': 0}
            
            win_rates[event_name]['wins'] += wins
            win_rates[event_name]['losses'] += losses
    
    # Calculate win rates for each event
    for event_name, stats in win_rates.items():
        total_matches = stats['wins'] + stats['losses']
        if total_matches > 0:
            win_rate = round((stats['wins'] / total_matches) * 100, 2)
            win_rates[event_name]['win_rate'] = win_rate
    
    return win_rates

async def remove_reactions(message):
    await asyncio.sleep(60)  # Set timeout to 60 seconds
    try:
        await message.clear_reactions()
    except discord.Forbidden:
        pass

@bot.tree.command(name='winloss', description='Shows the Win Loss rates of a team at every event')
async def winloss(interaction: discord.Interaction, team: str):
    try:
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {APITOKEN}",
        }
        team_name = team.upper()
        team_id = get_team_id(team_name)
        winLossUrl = f"https://www.robotevents.com/api/v2/teams/{team_id}/matches?season%5B%5D=181&per_page=250"
        response = requests.get(winLossUrl, headers=headers)
        data = response.json()['data']
        
        overall_win_rate = calculate_overall_win_rate(data, team_name)
        event_win_rates = calculate_event_win_rates(data, team_name)
        
        if not overall_win_rate or not event_win_rates:
            await interaction.response.send_message(f"No win-loss data found for team {team_name}.")
            return
        
        # Create embed with overall win rate
        embed = discord.Embed(title=f"Win-Loss Record for {team_name}")
        wins = overall_win_rate['wins']
        losses = overall_win_rate['losses']
        win_rate_percentage = overall_win_rate['win_rate']
        color = discord.Color.green() if win_rate_percentage > 50 else discord.Color.red() if win_rate_percentage < 50 else discord.Color.gold()
        embed.add_field(name="Overall", value=f"Wins: {wins}\nLosses: {losses}\nWin Rate: {win_rate_percentage:.2f}%", inline=False)
        embed.color = color
        await interaction.response.send_message(embed=embed) 
        message = await interaction.original_response()
        
        # Add reaction buttons for navigation if there are events
        event_names = list(event_win_rates.keys())
        if len(event_names) > 0:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
        
        async def update_embed(page):
            embed.clear_fields()
            if page == 0:
                # Display overall win rate
                if overall_win_rate:
                    wins = overall_win_rate['wins']
                    losses = overall_win_rate['losses']
                    win_rate_percentage = overall_win_rate['win_rate']
                    color = discord.Color.green() if win_rate_percentage > 50 else discord.Color.red() if win_rate_percentage < 50 else discord.Color.gold()
                    embed.add_field(name="Overall", value=f"Wins: {wins}\nLosses: {losses}\nWin Rate: {win_rate_percentage:.2f}%", inline=False)
                    embed.color = color
                else:
                    embed.add_field(name="Overall", value="No overall win-loss data found.", inline=False)
            else:
                # Display win rates for events
                event_name = event_names[page - 1]
                if event_name in event_win_rates:
                    wins = event_win_rates[event_name]['wins']
                    losses = event_win_rates[event_name]['losses']
                    win_rate_percentage = event_win_rates[event_name]['win_rate']
                    color = discord.Color.green() if win_rate_percentage > 50 else discord.Color.red() if win_rate_percentage < 50 else discord.Color.gold()
                    embed.add_field(name=event_name, value=f"Wins: {wins}\nLosses: {losses}\nWin Rate: {win_rate_percentage:.2f}%", inline=False)
                    embed.color = color
                else:
                    embed.add_field(name=event_name, value="No win-loss data found for this event.", inline=False)
            
            embed.set_footer(text=f"Page {page + 1}/{len(event_names) + 1}")
            await message.edit(embed=embed)
                
        page = 0
        await update_embed(page)
        
        # Start the timer to remove reactions after timeout
        task = asyncio.create_task(remove_reactions(message))
        
        # Reaction handling loop
        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60, check=lambda reaction, user: user == interaction.user and reaction.message.id == message.id)
                if str(reaction.emoji) == "➡️":
                    page = (page + 1) % (len(event_names) + 1)
                    await update_embed(page)
                    # Reset the timer
                    task.cancel()
                    task = asyncio.create_task(remove_reactions(message))
                elif str(reaction.emoji) == "⬅️":
                    page = (page - 1) % (len(event_names) + 1)
                    await update_embed(page)
                    # Reset the timer
                    task.cancel()
                    task = asyncio.create_task(remove_reactions(message))
                await message.remove_reaction(reaction, user)
            except asyncio.TimeoutError:
                break  # Exit the loop after timeout

        # Cancel the task if it's still running
        task.cancel()

    except Exception as e:
        await interaction.response.send_message(str(e))


# Function to fetch events and rankings for a team
def get_events_and_rankings(team_id):
    headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {APITOKEN}",
    }
    events_url = f"https://www.robotevents.com/api/v2/teams/{team_id}/rankings?season%5B%5D=181&season%5B%5D=182&season%5B%5D=180"
    response = requests.get(events_url, headers=headers)
    response.raise_for_status()
    events_data = response.json()

    awards_url = f"https://www.robotevents.com/api/v2/teams/{team_id}/awards?season%5B%5D=181&season%5B%5D=182&season%5B%5D=180"
    response = requests.get(awards_url, headers=headers)
    response.raise_for_status()
    awards_data = response.json()

    return events_data, awards_data
#Command to Shows that win loss record of a team, or if there is an event, the scores at that event

# Command to display events, rankings, and awards for a team
@bot.tree.command(name='events', description='Finds events and awards for a team')
async def events(interaction: discord.Interaction, team:str):
    try:
        team_id = get_team_id(team)
        if team_id:
            events_data, awards_data = get_events_and_rankings(team_id)
            if events_data["data"]:
                embed = discord.Embed(title=f"Events and Awards for Team {team}", color=0x00ff00)
                for event in events_data["data"]:
                    event_name = event["event"]["name"]
                    rank = event["rank"]
                    
                    # Initialize event awards list
                    event_awards = []
                    
                    # Check if there are any awards for the event
                    if awards_data and awards_data["data"]:
                        for award in awards_data["data"]:
                            if award["event"]["name"] == event_name:
                                # Remove anything inside parentheses from the award title
                                award_title = re.sub(r'\(.*?\)', '', award["title"]).strip()
                                event_awards.append(award_title)
                    # Check if there are any awards for the event
                    if event_awards:
                        embed.add_field(name=f"Event: {event_name}", 
                                        value=f"Rank: {rank}\nAwards: {', '.join(event_awards)}", 
                                        inline=False)
                    else:
                        embed.add_field(name=f"Event: {event_name}", 
                                        value = f"Rank: {rank}",
                                        inline=False)
                      
                
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(title=f"No Events Found for Team {team}", color=0xff0000)
                await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"Team {team} not found.")
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")

def format_rankings(data, team_number=None):
    if team_number:
        for idx, item in enumerate(data, start=1):
            if item['team']['team'] == team_number:
                team_name = item['team']['teamName']
                score = item['scores']['score']
                programming_score = item['scores']['programming']
                driver_score = item['scores']['driver']
                
                embed = discord.Embed(title=f"Ranking for Team {team_number}", color=0xffd700)  # Gold color
                embed.add_field(name=f"Team Name: {team_name}",
                                value=f"**Total Score:** {score}\n"
                                      f"**Driver Score:** {driver_score}\n"
                                      f"**Autonomous Score:** {programming_score}\n"
                                      f"**Ranking Place:** {idx}{'st' if idx == 1 else 'nd' if idx == 2 else 'rd' if idx == 3 else 'th'}",
                                inline=False)
                return embed
        return discord.Embed(title="Error", description=f"Team {team_number} not found.", color=0xff0000)  # Red color

    else:
        embed = discord.Embed(title="Top 10 Rankings", color=0xffd700)  # Gold color
        for idx, item in enumerate(data[:10], start=1):
            team_name = item['team']['teamName']
            score = item['scores']['score']
            programming_score = item['scores']['programming']
            driver_score = item['scores']['driver']
        
            embed.add_field(name=f"#{idx} {team_name}",
                            value=f"**Total Score:** {score}\n"
                                  f"**Driver Score:** {driver_score}\n"
                                  f"**Autonomous Score:** {programming_score}\n",
                                  
                            inline=False)
        return embed

def format_data(data):
    if data:
            for item in data:
                team_name = item['number']
                embed = discord.Embed(title=f"{team_name}'s info", color=0x00ff00)
                embed.add_field(name="Team Name", value=item['team_name'], inline=False)
                embed.add_field(name="Organization", value=item['organization'], inline=False)
                location = f"{item['location']['city']}, {item['location']['region']}, {item['location']['country']}"
                embed.add_field(name="Location", value=location, inline=False)
                embed.add_field(name="Registered", value='Yes' if item['registered'] else 'No', inline=False)
                embed.add_field(name="Program", value=item['program']['name'], inline=False)
                embed.add_field(name="Grade", value=item['grade'], inline=False)
                embed.add_field(name="ID", value=item['id'], inline=False)
    return embed

@bot.tree.command(name = 'ranking', description= 'Gives the top 10 skills rankings or a specified teams ranking.')
async def rankings(interaction: discord.Interaction, team : str = ''):
    team_number = team if team else None  # Extract team number from args if present
    searchurl = f"https://www.robotevents.com/api/seasons/181/skills?"
    headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {APITOKEN}",
    }
    response = requests.get(searchurl, headers=headers)
    response.raise_for_status()
    data = response.json()          
    embed = format_rankings(data, team_number)  # Pass team_number to the format_rankings function
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='info', description='Gives info on Vex Robotics Teams')
async def info(interaction: discord.Interaction, team: str = ''):
    team = team if team else db.reference(f"{interaction.user.id}/Team").get()
    try:
        searchurl = f"https://www.robotevents.com/api/v2/teams?number%5B%5D={team}&myTeams=false"
        headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {APITOKEN}",
        }
        response = requests.get(searchurl, headers=headers)
        response.raise_for_status()
        data = response.json()          
        embed = format_data(data["data"])
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(e)
        await interaction.response.send_message(f"{team} is not a valid team number.")
        
@bot.event
async def on_ready():
    print("Bot is up")
    try:
        await bot.tree.sync()
        print("synced")
    except Exception as e:
        print(e)
    
@bot.event
async def on_message(message):
    await bot.process_commands(message)
    print(message.content)

@bot.tree.command(name='sync', description='Owner only')
async def sync(interaction: discord.Interaction):
    if interaction.user.id == 485477939845005312:
        await bot.tree.sync()
        await interaction.response.send_message('Command tree synced.')
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

@bot.tree.command(name='help', description='Returns Usable Commands')
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Bot Commands", description="List of available commands", color=0x00ff00)

    embed.add_field(name=".winloss [team_number]", value="Shows the win-loss record of a team", inline=False)
    embed.add_field(name=".events [team_number]", value="Shows events and awards for a team", inline=False)
    embed.add_field(name=".rankings [team_number]", value="Shows rankings for a team or top 10 rankings if no team number provided", inline=False)
    embed.add_field(name=".info [team_number]", value="Shows information about a team", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='resources', description='Returns helpful Vex Resources')
async def resources(interaction: discord.Interaction):
    embed = discord.Embed(title="Vex Resources", color=0x00ff00)
    embed.add_field(name="Vex Forum Wiki", value="https://www.vexforum.com/t/wiki/67132")
    embed.add_field(name="Rulebook", value="https://www.vexrobotics.com/over-under-manual", inline=False)
    embed.add_field(name="Building Instructions", value="https://wiki.purduesigbots.com/", inline=False)
    embed.add_field(name="Programming Guides", value="C++:\nhttps://www.learncpp.com/\nIntro to PID:\nhttps://georgegillard.com/resources/documents\n Pure Pursuit: https://www.chiefdelphi.com/uploads/default/original/3X/b/e/be0e06de00e07db66f97686505c3f4dde2e332dc.pdf\nPROS Docs:\nhttps://pros.cs.purdue.edu/v5/index.html\nLemLib:\nhttps://lemlib.github.io/LemLib/index.html\nJAR Template:\nhttps://jacksonarearobotics.github.io/JAR-Template/", inline=False)
    embed.add_field(name="World Skills Rankings", value="https://www.robotevents.com/robot-competitions/vex-robotics-competition/standings/skills", inline=False)

    await interaction.response.send_message(embed=embed)
@bot.tree.command(name='matchup',description='Gives the odds of teams winning matches')
async def matchup(interaction: discord.Interaction, team1: str, team2: str, team3: str, team4: str):
    try:
        # Fetch data for the provided team numbers
        team_ids = []
        team_names = []
        team_data = [team1, team2, team3, team4]
        for team in team_data:
            team_ids.append(get_team_id(team))
            team_names.append(team)
            
        
        new_team_data = []
        for team in team_ids:
            team_data_inv = get_team_data(team)
            result = [team_data_inv['Average_AP'], team_data_inv['Average_SP'], team_data_inv['Average_Average_Points']]
            new_team_data.append(result)
            
        
        # Predict win probabilities using the linear regression model
        predicted_win_probability = model.predict(new_team_data)
        
        # Aggregate probabilities for each alliance
        blue_alliance_prob = np.mean(predicted_win_probability[:2])
        red_alliance_prob = np.mean(predicted_win_probability[2:])
        
        # Normalize probabilities
        total_prob = blue_alliance_prob + red_alliance_prob
        blue_alliance_prob_normalized = (blue_alliance_prob / total_prob) * 100
        if blue_alliance_prob_normalized > 100:
            blue_alliance_prob_normalized = 100
        if blue_alliance_prob_normalized < 0:
            blue_alliance_prob_normalized = 0
        red_alliance_prob_normalized = (red_alliance_prob / total_prob) * 100
        if red_alliance_prob_normalized > 100:
            red_alliance_prob_normalized = 100
        if red_alliance_prob_normalized < 0:
            red_alliance_prob_normalized = 0
        
        # Send the prediction as a message
        embed = discord.Embed(title="Matchup Prediction", color=discord.Color.blue())
        embed.add_field(name=f"{team_names[0]} & {team_names[1]}", value=f"Win%: {red_alliance_prob_normalized:.2f}", inline=True)
        embed.add_field(name=f"{team_names[2]} & {team_names[3]}", value=f"Win%: {blue_alliance_prob_normalized:.2f}", inline=True)
        
        # Send the embed as a message
        await interaction.response.send_message(embed=embed)
    
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")
@bot.tree.command(name='setteam', description='Sets your team name. Uses this team as default for commands')
async def setteam(interaction: discord.Interaction, team:str):
    Team = team
    user = interaction.user.id
    ref = db.reference(f"/")
    ref.update({
        user: {
            "Team": str(Team)
        }
    }
    )
    await interaction.response.send_message(f"You are now part of team {Team}")
@bot.tree.command(name='myteam', description='Shows which team you have set')
async def myteam(interaction: discord.Interaction):
    try:
        Team  = db.reference(f"{interaction.user.id}/Team").get()
        await interaction.response.send_message(f"You are part of team {Team}")
    except:
        await interaction.response.send_message("You have not given a Team previously!")

bot.run(TOKEN)