import requests
import discord
from discord.ext import commands
from typing import Final
import os
from dotenv import load_dotenv
import re

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
APITOKEN: Final[str] = os.getenv('API_KEY')

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


# @bot.command()
# async def event(ctx, arg1, arg2):

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
async def info(interaction: discord.Interaction, team: str):
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
        await bot.tree.sync(guild=discord.Object(id=1219707473410396273))
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
        await bot.tree.sync(guild=discord.Object(id=1219707473410396273))
        await interaction.response.send_message('Command tree synced.')
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

bot.run(TOKEN)