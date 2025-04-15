# Training_Request_Manager
A Discord bot designed to handle training session requests (Z-01 to Z-05) using buttons and JSON-based storage. This bot helps instructors and trainees manage requests smoothly and efficiently.

## Features

- Request training sessions from Z-01 to Z-05
- Interactive buttons for instructors to **Accept**, **Complete**, or **Reject** sessions
- Automatically updates user status and stores progress in JSON files
- Supports multiple simultaneous users

## How to Use

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- `discord.py` and required dependencies

### Installation

```bash
git clone https://github.com/YourUsername/discord-training-bot.git
cd discord-training-bot
pip install -r requirements.txt
```
Create a .env file in the root directory and add your bot token like this:
```
DISCORD_TOKEN=your_discord_bot_token
```
Example Workflow
A user starts a request (Z-01 to Z-05).

A message is sent in the training-request channel.

The instructor uses the buttons below the request:

✅ Accept: Confirms the session.

🟢 Complete: Marks the session as completed.

❌ Reject: Cancels the session.

All progress is logged in corresponding Z01.json to Z05.json files.

#Notes

Only instructors with the specified role ID can accept or complete sessions.

Each user can only request a session once at a time.

If needed, you can reset progress manually from the JSON files.