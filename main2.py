import requests
import discord
from discord.ext import commands
from typing import Final
import os
from dotenv import load_dotenv
import re
import asyncio

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
APITOKEN: Final[str] = os.getenv('API_KEY')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents = intents, help_command=None)

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
#Command to Shows that win loss record of a team, or if there is an event, the scores at that event
def calculate_overall_win_rate(data, team_name):
    wins = 0
    losses = 0
    
    for match in data:
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

@bot.command()
async def winloss(ctx, team_name: str):
    try:
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {APITOKEN}",
        }
        team_id = get_team_id(team_name)
        winLossUrl = f"https://www.robotevents.com/api/v2/teams/{team_id}/matches?season%5B%5D=181&per_page=250"
        response = requests.get(winLossUrl, headers=headers)
        data = response.json()['data']
        
        overall_win_rate = calculate_overall_win_rate(data, team_name)
        event_win_rates = calculate_event_win_rates(data, team_name)
        
        if not overall_win_rate or not event_win_rates:
            await ctx.send(f"No win-loss data found for team {team_name}.")
            return
        
        # Create embed with overall win rate
        embed = discord.Embed(title=f"Win-Loss Record for {team_name}")
        wins = overall_win_rate['wins']
        losses = overall_win_rate['losses']
        win_rate_percentage = overall_win_rate['win_rate']
        color = discord.Color.green() if win_rate_percentage > 50 else discord.Color.red() if win_rate_percentage < 50 else discord.Color.gold()
        embed.add_field(name="Overall", value=f"Wins: {wins}\nLosses: {losses}\nWin Rate: {win_rate_percentage:.2f}%", inline=False)
        embed.color = color
        
        message = await ctx.send(embed=embed)
        
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
            
            async def remove_reactions():
                await asyncio.sleep(60)  # Set timeout to 60 seconds
                try:
                    await message.clear_reactions()
                except discord.Forbidden:
                    pass
            
            # Start the timer to remove reactions after timeout
            task = asyncio.create_task(remove_reactions())
            
            while True:
                try:
                    reaction, user = await bot.wait_for("reaction_add", timeout=60, check=lambda reaction, user: user == ctx.author and reaction.message.id == message.id)
                    if str(reaction.emoji) == "➡️":
                        page = (page + 1) % (len(event_names) + 1)
                        await update_embed(page)
                        # Reset the timer
                        task.cancel()
                        task = asyncio.create_task(remove_reactions())
                    elif str(reaction.emoji) == "⬅️":
                        page = (page - 1) % (len(event_names) + 1)
                        await update_embed(page)
                        # Reset the timer
                        task.cancel()
                        task = asyncio.create_task(remove_reactions())
                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    break  # Exit the loop after timeout
            
            # Cancel the task if it's still running
            task.cancel()
            
    except Exception as e:
        await ctx.send(str(e))
@bot.command()
async def events(ctx, args):
    try:
        team_id = get_team_id(args)
        if team_id:
            events_data, awards_data = get_events_and_rankings(team_id)
            if events_data["data"]:
                embed = discord.Embed(title=f"Events and Awards for Team {args}", color=0x00ff00)
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
                      
                
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title=f"No Events Found for Team {args}", color=0xff0000)
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"Team {args} not found.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")


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

@bot.command()
async def rankings(ctx, *args):
    team_number = args[0] if args else None  # Extract team number from args if present
    searchurl = f"https://www.robotevents.com/api/seasons/181/skills?"
    headers = {
    "accept": "application/json",
    "Authorization": f"Bearer {APITOKEN}",
    }
    response = requests.get(searchurl, headers=headers)
    response.raise_for_status()
    data = response.json()          
    embed = format_rankings(data, team_number)  # Pass team_number to the format_rankings function
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx, arg):
    try:
        searchurl = f"https://www.robotevents.com/api/v2/teams?number%5B%5D={arg.upper()}&myTeams=false"
        headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {APITOKEN}",
        }
        response = requests.get(searchurl, headers=headers)
        response.raise_for_status()
        data = response.json()          
        embed = format_data(data["data"])
        await ctx.send(embed=embed)
    except Exception as e:
        print(e)
        await ctx.send(f"{arg} is not a valid team number.")
        
    


@bot.event
async def on_ready():
    print("Bot is up")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
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

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Bot Commands", description="List of available commands", color=0x00ff00)

    embed.add_field(name=".winloss [team_name]", value="Shows the win-loss record of a team", inline=False)
    embed.add_field(name=".events [team_number]", value="Shows events and awards for a team", inline=False)
    embed.add_field(name=".rankings [team_number]", value="Shows rankings for a team or top 10 rankings if no team number provided", inline=False)
    embed.add_field(name=".info [team_number]", value="Shows information about a team", inline=False)

    await ctx.send(embed=embed)

bot.run(TOKEN)