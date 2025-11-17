import os
import logging
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Force local imports to resolve correctly
import sys
import importlib
sys.path.append(os.path.dirname(__file__))
importlib.invalidate_caches()

from cogs.controller import handle_buildcore_request

load_dotenv()
TOKEN = os.getenv("DISCORD_TEST_TOKEN")
print(f"TOKEN loaded? {'Yes' if TOKEN else 'No'}")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

logger = logging.getLogger("professor_sequoia")
logging.basicConfig(level=logging.INFO)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("Ready to accept build requests.")
    print(f"✅ Logged in as {bot.user}")

#ADDED TEMPORARILY FOR DEBUGGING PURPOSES
#-------------------------------------------------------------------------------
@bot.event
async def on_message(message):
    # Debug: log every message the bot sees
    if message.author != bot.user:
        print(f"📨 Message from {message.author}: {message.content}")
    
    # IMPORTANT: Must call this to process commands
    await bot.process_commands(message)
#-------------------------------------------------------------------------------

@bot.command(name="buildcore", help="Build a VGC team around a core. Example: !buildcore Charizard, Rotom-Wash hyper-offense reg-h")
async def buildcore(ctx, *, args: str):
    # args is raw message after command
    # call controller
    async with ctx.typing():  # Fixed: changed from ctx.trigger_typing()
        result = await handle_buildcore_request(args, user_id=str(ctx.author.id))
        if result['status'] == 'clarify':
            await ctx.send(result['message'])
        elif result['status'] == 'error':
            await ctx.send(f"Error: {result['message']}")
        elif result['status'] == 'ok':
            await ctx.send(result['message'])
            # optionally, attach a pretty embed with team details
            await send_team_embed(ctx, result['team'])

async def send_team_embed(ctx, team):
    # create a simple embed
    embed = discord.Embed(title="Professor Sequoia — Team Recommendation", color=0x2ecc71)
    for member in team:
        name = member.get('name', 'Unknown').title()
        moves = ", ".join(member.get('suggested_moves', []))
        item = member.get('suggested_item', 'None')
        ev = member.get('suggested_ev', '')
        field_value = f"Moves: {moves}\nItem: {item}\nEVs: {ev}"
        embed.add_field(name=name, value=field_value, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="refine", help="Refine the last built team. Example: !refine more balanced")
async def refine(ctx, *, args: str):
    # For MVP: route to controller.refine_team (not yet implemented) – we can call handle_buildcore_request again with extra constraints
    await ctx.send("Refinement feature not implemented in MVP. Try `!buildcore` again with clarifying options (e.g., `!buildcore Charizard, balance`).")

@bot.command(name="explain", help="Explain a recommended decision. Example: !explain Charizard EVs")
async def explain(ctx, *, args: str):
    # Basic placeholder: in full product controller should have explanation engine
    await ctx.send("Explanation feature is coming soon — for now check moves & items in the embed.")

@bot.command(name="evaluate", help="Evaluate and optimize a given team. Paste your full team in Pokepaste format after the command.")
async def evaluate(ctx, *, team_text: str):
    async with ctx.typing():
        try:
            from cogs.controller import handle_team_evaluation
            result = await handle_team_evaluation(team_text, user_id=str(ctx.author.id))
            if result['status'] == 'error':
                await ctx.send(f"Error: {result['message']}")
            else:
                await ctx.send(embed=result['embed'])
        except Exception as e:
            await ctx.send(f"⚠️ Unexpected error during evaluation: {str(e)}")

if __name__ == "__main__":
    bot.run(TOKEN)