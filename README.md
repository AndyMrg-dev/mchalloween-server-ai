# Nosferatu Engine

I wanted to build a Halloween-themed Minecraft server for me and my friends, with a custom map, a unique texture pack and an AI-powered NPC. At the center is Count Nosferatu, a vampire who reads the server log, decides what he thinks of you, and acts on it, usually badly.

Under the hood it's a Python process sitting between PaperMC and the Gemini API. It tails the server log, sends context to the model, gets a structured JSON decision back, and executes it over RCON.

 What it does

Every player has a reputation score from -300 to +100. It's kept in memory while the bot is running, so it survives players logging out and back in, but it resets when you restart the bot. It moves in two ways:

- Talking to Nosferatu: Each chat message goes to Gemini together with the player's current reputation. The model answers with a line of dialogue, a reputation change (-15 to +10), and an optional action.
- Quests: Nosferatu asks for specific items such as bones, spider eyes or feathers. Each quest has a fixed reputation bump and a reward, all defined in `config.json`. The bot doesn't inspect inventories: the reward is handed out as soon as the quest is triggered, so handing over the items is on the honor system.

Reputation also resets to 0 when a player dies. This only covers the common death messages (slain, drowned, blew up, fell, burned, lava, froze).

| Reputation   | Tier                 | Behavior                       |
| ------------ | -------------------- | ------------------------------ |
| +50 to +100  | Friendly (in denial) | Gifts, buffs, quest rewards    |
| 0 to +49     | Neutral              | Dialogue, roasts               |
| -1 to -49    | Annoyed              | More cutting dialogue          |
| -50 to -200  | Toxic                | Curses, minor hostile actions  |
| -201 to -300 | Sadistic             | Lightning, mob ambushes, traps |

Besides reacting to chat, Nosferatu does something on his own every 10 minutes: a fake eclipse (night and thunder), a bat swarm, or just a voice line, picked at random.

 Requirements

You need a Gemini API key, Python 3.10 or newer, and PaperMC 1.20 or newer. Java 21 is required for Paper 1.20.5 and later; older versions run on Java 17. Check the requirement for the Paper version you download.

 Setup

The simplest layout is to keep everything in one folder, the clone of this repository, so that `run.bat`, `paper.jar` and `logs/latest.log` sit next to the bot. If your server lives somewhere else, point `log_path` in `config.json` at its `latest.log`.

 1. Get the code

```bash
git clone https://github.com/AndyMrg-dev/mchalloween-server-ai.git
cd mchalloween-server-ai
pip install -r requirements.txt
```

 2. World and resource pack

The map isn't stored in the repository. Download `world.zip` from the [Releases page](https://github.com/AndyMrg-dev/mchalloween-server-ai/releases) and unzip it into the repository folder, so that you end up with a `world` folder next to `run.bat`. The folder name has to match `level-name` in `server.properties`, which is `world` by default.

The map is a port of the old PS3 Edition Halloween map and was not made for this project. It's meant for your own server, so please don't re-upload it elsewhere. The archive contains the map only; player data gets created when someone joins.

The texture pack isn't bundled either. It's a community-made port called "Halloween Mash-up", and the server downloads it from Dropbox when a player joins. The link is already set in `server.example.properties`:

```properties
require-resource-pack=true
resource-pack=https://www.dropbox.com/scl/fi/7yvy0oikfrof73fa3y8yj/Halloween-Mash-up.zip?rlkey=c4mw9x9jl10a4q97xxgimzgqi&st=6tygr75c&dl=1
resource-pack-prompt=Install the halloween texture pack!
```

If that link ever stops working, you'll have to re-host the pack yourself and swap in the new URL.

 3. Server and RCON

Download the Paper jar from [papermc.io](https://papermc.io), put it in the folder and rename it to `paper.jar` (or adjust the name in `run.bat`). Then create your server settings from the example:

```bash
cp server.example.properties server.properties
```

Open `server.properties` and set `rcon.password` to a password of your own. RCON is already enabled in the example file; the relevant lines are:

```properties
enable-rcon=true
rcon.port=25575
rcon.password=YOUR_RCON_PASSWORD
```

`run.bat` is a starting point for launching the server:

```batchfile
java -Xms2G -Xmx4G -jar paper.jar nogui
pause
```

It gives the server 2 to 4 GB of RAM, so adjust the numbers to what your machine can spare. The first launch stops with a message about `eula.txt`. Open that file, set `eula=true`, and start the server again.

 4. Letting people from outside your network join

The server only listens locally by default. To let friends connect from elsewhere, this setup uses [playit.gg](https://playit.gg), which tunnels the Minecraft port (25565) to a public address without touching your router.

RCON is not part of that tunnel and shouldn't be. Minecraft has no separate bind address for RCON: it listens on whatever `server-ip` is set to, which means all interfaces when it's empty. That's fine as long as you don't forward port 25575 on your router and use a proper password, since only 25565 needs to be reachable from outside.

 5. Configure the bot

```bash
cp config.example.json config.json
```

Then fill in `config.json`:

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

`gemini_key` can be left out if you set the `GEMINI_API_KEY` environment variable instead. `rcon.password` has to match `server.properties`, and `spam_cooldown` is the number of seconds a player has to wait between messages before Nosferatu answers again.

The same file holds the vampire's personality (`system_prompt`), his fallback insults (`voicelines`) and the `quests` list. Those are already filled in; edit them if you want him to talk differently or ask for other things.

`config.json` and `server.properties` are listed in `.gitignore` because they contain your API key and RCON password. Keep them out of your commits.

 6. Starting everything

Two things have to run at the same time, in two terminal windows. Start the Minecraft server first by double-clicking `run.bat` and wait until the console shows `Done`. Then start the bot in a second terminal:

```bash
python nosferatu_bot.py
```

The bot follows the server's log file as it grows, so the server has to be running and writing to `logs/latest.log` before there is anything for him to react to.

 If something isn't working

The bot starts but never reacts: `log_path` is probably wrong. It has to point at the server's `latest.log`, not at a file in the bot's own folder.

ConnectionRefusedError on startup: RCON isn't reachable. Either it's still disabled in `server.properties`, or the server wasn't restarted after you changed it.

Empty replies, or Nosferatu keeps answering with the same generic insults: That's the fallback for API errors. Look for a `[Gemini Error]` line in the console. Usual causes are a wrong key, used-up quota, or a model name your key can't access (it's set in `nosferatu_bot.py`).

A noticeable delay before he answers: That's the API round trip. It's normal, especially when several players are talking at once.

 License

See [LICENSE](LICENSE). It covers the code in this repository, not the map or the texture pack.
