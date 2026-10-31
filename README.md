# Telegram Auto-Approve & PM Bot

A simple, robust, and asynchronous Telegram bot that automatically approves user join requests for your channels or groups and sends them a private confirmation/welcome message.

## How It Works
1. A user requests to join your Telegram channel or group via an approval-required invite link.
2. The bot receives a `ChatJoinRequest` update.
3. The bot attempts to send a private welcome message to the user.
4. The bot automatically approves the user's join request, adding them to the channel/group instantly.

---

## Prerequisites
- **Python 3.8+** must be installed on your system.
- The Python dependencies `aiogram` and `python-dotenv` (which are already pre-installed on this system, but listed in `requirements.txt`).

---

## Setup Instructions

### Step 1: Create a Telegram Bot
1. Open Telegram and search for the official **@BotFather** bot.
2. Send the `/newbot` command to create a new bot.
3. Enter a name for your bot, followed by a unique username (must end in `bot`, e.g., `MyAutoJoinApproverBot`).
4. `@BotFather` will provide you with an **HTTP API Token** (e.g., `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`). Copy this token.

### Step 2: Configure the Bot Environment
1. In the `botnew` folder, locate the file named `.env`.
2. Open it in a text editor (like Notepad, VS Code, etc.).
3. Paste your HTTP API token next to `BOT_TOKEN`:
   ```env
   BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```
4. (Optional) Customize the welcome message in `WELCOME_MESSAGE` and save the file.

### Step 3: Configure Channel/Group and Invite Link
For the bot to capture and approve requests, it must be added as an administrator and users must join through a special invite link.

#### A. Add the Bot as an Admin:
1. Open your Telegram Channel or Group.
2. Go to **Settings** -> **Administrators** -> **Add Administrator**.
3. Search for your bot using its username (e.g., `@MyAutoJoinApproverBot`).
4. Select it and ensure it has the following permission enabled:
   - **Invite Users via Link** (or **Manage Join Requests** / **Add Members**).
5. Save the administrator settings.

#### B. Create an Approval Invite Link:
1. Go to Channel/Group Settings -> **Invite Links**.
2. Click **Create a New Link**.
3. Under the **Request Admin Approval** option, turn it **ON**.
4. Click **Create** to generate the link.
5. Copy this link. Anyone who tries to join through this link will trigger the bot's auto-approval.

---

## Running the Bot

1. Open your Command Prompt (CMD) or PowerShell.
2. Navigate to this directory (if you're not already there):
   ```powershell
   cd "c:\Users\HP\OneDrive\Desktop\botnew"
   ```
3. Install the dependencies (if needed):
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```powershell
   python bot.py
   ```

You will see logs confirming the bot has started:
```text
2026-06-17 20:25:00 - INFO - Bot initialized successfully!
2026-06-17 20:25:00 - INFO - Username: @MyAutoJoinApproverBot
2026-06-17 20:25:00 - INFO - Name: Auto Approver Bot
2026-06-17 20:25:00 - INFO - Auto-Approve: True
2026-06-17 20:25:00 - INFO - Listening for join requests... Press Ctrl+C to stop.
```

---

## Important Notes & Troubleshooting

### Privacy Limits (Why a Private Message might fail)
Telegram has strict privacy policies to prevent spam. 
- The bot can send a private message to a user who submits a join request, **even if the user hasn't started the bot before**.
- However, if the user has strict privacy settings configured (e.g., **"Who can add a link to my account when forwarding my messages"** or **"Who can send me messages"** set to "My Contacts" or "Nobody"), Telegram will block the bot's private message.
- If this occurs, the bot will log a warning (`Could not send private message... Reason: Forbidden: bot can't initiate conversation with a user`), but **it will still successfully approve their request to join the channel**.

### Recommendations:
To ensure all users can receive your private messages:
1. **Pin a message** in your channel advising users to first click "Start" on your bot (e.g., `@MyAutoJoinApproverBot`) before trying to join.
2. Or, mention it in the welcome description of your invite links.
