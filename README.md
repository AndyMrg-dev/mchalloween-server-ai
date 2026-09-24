 Nosferatu Engine

I wanted to build a Halloween-themed Minecraft server for me and my friends using a custom map, a unique texture pack, and an AI-powered NPC. At the center is Count 
Nosferatu — a vampire who reads the server log, decides what he thinks of you, and acts on it — usually badly.

The map isn't stored in the repository itself. Download `world.zip` from the [Releases page](https://github.com/YOUR_USERNAME/nosferatu-engine/releases) 
and unzip it into your server directory, so you end up with a `world` folder next to `paper.jar`. The folder name has to match `level-name` in `server.properties` (the default is `world`).

The map is a port of the old PS3 Edition Halloween map and was not made for this project. Use it for your own server, but please don't re-upload it elsewhere.

The texture pack isn't bundled either. It's a community-made port called "Halloween Mash-up". Point the server at it via `server.properties`:

```properties
require-resource-pack=true
resource-pack=https://www.dropbox.com/scl/fi/7yvy0oikfrof73fa3y8yj/Halloween-Mash-up.zip?rlkey=c4mw9x9jl10a4q97xxgimzgqi&st=6tygr75c&dl=1
resource-pack-prompt=Install the halloween texture pack!
```
Under the hood it's a Python process sitting between PaperMC and the Gemini API. It tails the server log, sends context to the model, gets a 
structured JSON decision back, and executes it over RCON.

 What it does

Every player has a reputation score, -300 to +100, that persists between sessions. It moves in two ways:

- **Talking to Nosferatu.** Each message gets sent to Gemini along with the player's current reputation. The model 
replies with a line of dialogue, a reputation change (-15 to +10), and an optional action.
- **Quests.** Nosferatu will ask for specific items — bones, spider eyes, feathers, and so on. Completing the
 tasks gives a fixed reputation bump and a reward. The full list of quests and their rewards is in `config.json`.

Reputation resets to 0 whenever a player dies.

| Reputation | Tier | Behavior |
| --- | --- | --- |
| +50 to +100 | Friendly (in denial) | Gifts, buffs, quest rewards |
| 0 to +49 | Neutral | Dialogue, roasts |
| -1 to -49 | Annoyed | More cutting dialogue |
| -50 to -200 | Toxic | Curses, minor hostile actions |
| -201 to -300 | Sadistic | Lightning, mob ambushes, traps |

On top of the conversation-driven behavior, Nosferatu also does something on his own every 10 minutes — a 
fake eclipse (night + thunder), a bat swarm, or just a voice line, picked at random.

 Requirements

- Java 17+
- PaperMC 1.20 or newer
- Python 3.10+
- A Gemini API key

 Setup

 1. Resource pack and world

Extract the world template archive:
Unzip `world.zip` so that you have a local `world` directory in your main folder.
Copy the `world` folder from this repository into your server directory (matching whatever `level-name` is set to in `server.properties`).

The texture pack itself isn't bundled in this repository — it's a community-made pack called "Halloween Mash-up",
 not something created for this project. Point the server at it via `server.properties`:

```properties
require-resource-pack=true
resource-pack=https://www.dropbox.com/scl/fi/7yvy0oikfrof73fa3y8yj/Halloween-Mash-up.zip?rlkey=c4mw9x9jl10a4q97xxgimzgqi&st=6tygr75c&dl=1
resource-pack-prompt=Install the halloween texture pack!
```

If that Dropbox link ever stops working, you'll need to re-host the pack yourself and swap in the new URL.

 2. Server and RCON

Start the server once so it generates `eula.txt`, accept it, then enable RCON in `server.properties`:

```properties
enable-rcon=true
rcon.port=25575
rcon.password=YOUR_RCON_PASSWORD
```

Restart the server so the change takes effect.

This repository includes `run.bat` as a starting point for launching the server:

```batchfile
java -Xms2G -Xmx4G -jar paper.jar nogui
pause
```

It allocates 2–4 GB of RAM to the server — adjust those numbers if your machine has more or less to spare, and make sure the jar filename matches whatever you actually downloaded from papermc.io.

 3. Letting people from outside your network join

The server itself only listens locally. To let players from other networks connect, this setup runs [playit.gg](https://playit.gg), which tunnels the Minecraft port (25565) out to a public address without opening ports on your router.

RCON is not part of that tunnel and shouldn't be. Keep `rcon.port` bound to `127.0.0.1` — the bot runs on the same machine as the server, so it only needs local access, and only the game port needs to be public.

 4. Bot

```bash
git clone https://github.com/YOUR_USERNAME/nosferatu-engine.git
cd nosferatu-engine
pip install google-genai mcrcon
cp config.example.json config.json
cp server.properties.example server.properties
```

Fill in `config.json`:

```json
{
  "gemini_key": "YOUR_API_KEY",
  "log_path": "logs/latest.log",
  "spam_cooldown": 5.0,
  "rcon": {
    "host": "127.0.0.1",
    "port": 25575,
    "password": "YOUR_RCON_PASSWORD"
  }
}
```

`gemini_key` can also be left out and set via the `GEMINI_API_KEY` environment variable instead. `log_path` needs to point at the server's actual `latest.log`, and `rcon.password` has to match `server.properties`. `spam_cooldown` is how many seconds a player has to wait between messages before Nosferatu responds again.

`config.json` also carries the vampire's personality (`system_prompt`), his fallback insults (`voicelines`), and the full `quests` list — those are already filled in and don't need editing unless you want to change how he talks or what he asks for.

### 5. Starting everything

Two things need to run at the same time, in two separate terminal windows:

1. Start the Minecraft server first — double-click `run.bat` in your server directory. Wait until it's fully loaded; you'll see `Done` in the console.
2. Then, in a second terminal, from the bot's directory, start the bot:

   ```bash
   python nosferatu_bot.py
   ```

The bot reads the server's log file as it grows, so it needs the server already running and writing to `logs/latest.log` before it has anything to react to.

## Don't commit your config

`config.json` holds a live API key and your RCON password. Put it in `.gitignore` before the first commit:

```gitignore
config.json
*.log
__pycache__/
```

 If something isn't working

The bot starts but never reacts: `log_path` is probably wrong — it needs to point at the server's log file, not the bot's own directory.

ConnectionRefusedError on startup: RCON isn't running. Either it's still disabled in `server.properties`, or the server wasn't restarted after the edit.

Empty replies, or Nosferatu just says one of the generic insults every time: That's the API-error fallback — check the console for a `[Gemini Error]` line, usually a bad key or exhausted quota.

Noticeable delay before he responds: That's the API round trip, normal especially with several players talking at once.

 License

MIT.
