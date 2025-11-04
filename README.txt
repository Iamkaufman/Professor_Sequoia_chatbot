====================================================
README — Professor Sequoia Chatbot
====================================================

Author: [Your Name]
Course: [Course Name]
Project: Professor Sequoia — Competitive Pokémon VGC Assistant
Python Version: 3.10 or higher
====================================================

OVERVIEW
----------------------------------------------------
Professor Sequoia is an intelligent Discord chatbot that:
• Generates competitive Pokémon VGC teams based on user inputs.
• Updates and maintains a Pokémon usage database from online sources.
• Engages in natural language dialogue to refine team builds.

The project includes:
• NLP core logic for interpreting user messages.
• Database access for Pokémon stats and regulation data.
• Discord bot integration for conversational use.

----------------------------------------------------
PROJECT STRUCTURE
----------------------------------------------------

Professor_Sequoia/
│
├── cogs/
│   ├── controller.py        ← Handles user commands & message flow
│   ├── teambuilding.py      ← Logic for generating VGC teams
│
├── core/
│   ├── nlp.py               ← Natural Language Processing layer
│
├── database/
│   ├── db_setup.py          ← Creates or resets the SQLite database
│   ├── repository.py        ← Database access & queries
│   ├── scrape_vgc_data.py   ← Pulls Pokémon usage stats from Labmaus/Pikalytics
│   ├── professor_sequoia.db ← SQLite database file
│
├── bot.py                   ← Main Discord bot runner
├── test_bot.py              ← Local testing entrypoint
├── requirements.txt         ← Python dependencies
├── vgc_usage_data.json      ← Cached Pokémon usage data
├── .env                     ← Stores Discord bot token (see setup below)
└── README.txt               ← This file


----------------------------------------------------
INSTALLATION & SETUP
----------------------------------------------------

1. **Install Python**
   Ensure Python 3.10+ is installed on your system.
   To verify, run:
       python --version

   If not installed, download from:
       https://www.python.org/downloads/

2. **Open a terminal** (Windows PowerShell, macOS Terminal, or Linux shell)
   Navigate to the project directory:
       cd path/to/Professor_Sequoia

3. **Create a virtual environment**
       python -m venv venv

4. **Activate the virtual environment**
   On Windows:
       venv\Scripts\activate
   On macOS/Linux:
       source venv/bin/activate

5. **Install required dependencies**
       pip install -r requirements.txt

6. Invite the bot to the live Discord Server.

Use this invite link: https://discord.gg/2mR4bvMB

7. **Run the bot**
       python bot.py

   You should see output similar to:
TOKEN loaded? Yes
2025-11-03 14:47:20 INFO     discord.client logging in using static token
INFO:discord.client:logging in using static token
2025-11-03 14:47:20 INFO     discord.gateway Shard ID None has connected to Gateway (Session ID: ccc75d3340d05b89d822308181c51b64).
INFO:discord.gateway:Shard ID None has connected to Gateway (Session ID: ccc75d3340d05b89d822308181c51b64).
INFO:professor_sequoia:Logged in as Professor Sequoia#6894 (ID: 1430160395074801674)
INFO:professor_sequoia:Ready to accept build requests.
✅ Logged in as Professor Sequoia#6894

You should also see that Professor Sequoia's status is online in the right sidebar (indicated by a green dot)
   The bot is now running and listening for commands in your Discord server.


----------------------------------------------------
USAGE EXAMPLES
----------------------------------------------------

In Discord (after inviting your bot to a server):

Example 1:
    User: Build me a team with Sneasler and Indeedee for Regulation H
    Bot:  Here's a balanced Regulation H team built around Sneasler + Indeedee...

Example 2:
    User: Make it more offensive.
    Bot:  Adjusting the EV spreads and adding faster sweepers...

Example 3:
    User: Update database from Pikalytics.
    Bot:  Fetching current Regulation data... database updated!

----------------------------------------------------
TROUBLESHOOTING
----------------------------------------------------

• **SSL Error when scraping data**
  If you encounter an SSL certificate error while fetching data:
      - Ensure your certifi package is updated:
          pip install --upgrade certifi
      - If needed, disable certificate verification temporarily (for local testing only).

• **Bot not connecting**
  - Double-check the Discord token in `.env`
  - Ensure the bot has permission to read and send messages in your server.

• **Missing dependencies**
  - Run: pip install -r requirements.txt again.

----------------------------------------------------
NOTES FOR EVALUATORS / INSTRUCTORS
----------------------------------------------------
This project does NOT require any IDE (e.g., VSCode, PyCharm).
It can be fully executed via standard Python commands in the terminal.

All dependencies are installed via pip, and configuration is handled through `.env`.
No external database servers or services are required — SQLite is self-contained.

----------------------------------------------------
END OF README
====================================================
