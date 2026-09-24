import os
import re
import json
import time
import random
import warnings
from threading import Thread
from google import genai
from google.genai import types
from google.genai.errors import APIError
from mcrcon import MCRcon

# Suppress non-critical user warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Load configuration file
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

api_key = cfg.get("gemini_key") or os.environ.get("GEMINI_API_KEY")
if not api_key or api_key in ["YOUR_API_KEY_HERE", "YOUR_API_KEY_HERE"]:
    raise RuntimeError("Gemini API key in config.json is missing or invalid!")

ai_client = genai.Client(api_key=api_key)

reputation = {}
cooldowns = {}

CHAT_RE = re.compile(r"\]: <([A-Za-z0-9_]+)> (.*)")
DEATH_RE = re.compile(r"\]: ([A-Za-z0-9_]+) (was slain|drowned|blew up|fell|hit the ground|burned|tried to swim in lava|froze)")

def send_rcon(*cmds):
    def _send():
        mcr = None
        try:
            mcr = MCRcon(cfg["rcon"]["host"], cfg["rcon"]["password"], port=cfg["rcon"]["port"])
            mcr.connect()
            for command in cmds:
                mcr.command(command)
        except Exception as e:
            print(f"[RCON Error] Connection failed: {e}")
        finally:
            if mcr:
                try:
                    mcr.disconnect()
                except Exception:
                    pass
    Thread(target=_send, daemon=True).start()

def set_reputation(player, value):
    reputation[player] = max(-300, min(100, value))

def add_reputation(player, delta):
    new_value = max(-300, min(100, reputation.get(player, 0) + delta))
    reputation[player] = new_value
    return new_value

ACTIONS = {
    "feed": lambda p: send_rcon(f"give {p} minecraft:cooked_beef 16", f"effect give {p} minecraft:saturation 5 10"),
    "armor": lambda p: send_rcon(f"give {p} minecraft:iron_chestplate", f"give {p} minecraft:shield"),
    "blocks": lambda p: send_rcon(f"give {p} minecraft:obsidian 8"),
    "gold_apples": lambda p: send_rcon(f"give {p} minecraft:enchanted_golden_apple 1", f"give {p} minecraft:golden_apple 3"),
    "xp_boost": lambda p: send_rcon(f"experience add {p} 10 levels"),
    "night_vision": lambda p: send_rcon(f"effect give {p} minecraft:night_vision 120 0"),
    "dog_guard": lambda p: send_rcon(f"execute at {p} run summon wolf ~ ~ ~ {{Owner:{p}}}"),
    "bless": lambda p: send_rcon(f"effect give {p} minecraft:speed 20 1", f"effect give {p} minecraft:regeneration 10 1"),
    "smite": lambda p: send_rcon(f"execute at {p} run summon lightning_bolt"),
    "curse": lambda p: send_rcon(f"effect give {p} minecraft:slowness 10 2", f"effect give {p} minecraft:darkness 10 1"),
    "ignite": lambda p: send_rcon(f"execute at {p} run setblock ~ ~ ~ fire"),
    "launch": lambda p: send_rcon(f"effect give {p} minecraft:levitation 3 8"),
    "bats": lambda p: [send_rcon(f"execute at {p} run summon bat ~ ~2 ~") for _ in range(5)],
    "anvil_trap": lambda p: send_rcon(f"execute at {p} run setblock ~ ~3 ~ minecraft:anvil"),
    "mob_ambush": lambda p: send_rcon(f"execute at {p} run summon phantom ~ ~5 ~", f"execute at {p} run summon zombie ~1 ~ ~"),
    "jumpscare": lambda p: send_rcon(f"playsound minecraft:ambient.cave master {p} ~ ~ ~ 100 1", f"playsound minecraft:entity.wither.spawn master {p} ~ ~ ~ 100 0.5"),
    "tnt_prank": lambda p: send_rcon(f"execute at {p} run summon tnt ~ ~ ~ {{Fuse:80}}"),
    "hunger_curse": lambda p: send_rcon(f"effect give {p} minecraft:hunger 15 255"),
    "fake_rich": lambda p: send_rcon(f"give {p} minecraft:poisonous_potato 16", f"give {p} minecraft:rotten_flesh 16"),
    "disarm": lambda p: send_rcon(f"execute at {p} run item replace entity {p} weapon.mainhand with minecraft:air")
}

def trigger_actions(player, action_str):
    for act in [a.strip() for a in action_str.split(",")]:
        if act in ACTIONS:
            ACTIONS[act](player)
        elif act in cfg.get("quests", {}):
            q = cfg["quests"][act]
            cmds = [f"say §4[Count Nosferatu]§f {player}, {q['msg']}"]
            cmds.extend([c.format(player=player) for c in q["cmds"]])
            send_rcon(*cmds)
            add_reputation(player, q["rep"])

def fetch_ai_response(player, message):
    raw_prompt = cfg["system_prompt"]
    if isinstance(raw_prompt, list):
        raw_prompt = " ".join(raw_prompt)

    prompt = raw_prompt.format(player=player, rep=reputation.get(player, 0))
    
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "chat_response": {"type": "STRING"},
            "rep_change": {"type": "INTEGER"},
            "action": {"type": "STRING"}
        },
        "required": ["chat_response", "rep_change", "action"]
    }

    try:
        res = ai_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=f"Player '{player}' says: {message}",
            config=types.GenerateContentConfig(
                system_instruction=prompt,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.8
            )
        )
        return json.loads(res.text)
    except Exception as e:
        print(f"[Gemini Error] {e}")
        fallback_msg = random.choice(cfg.get("voicelines", ["Silence, mortal!"]))
        return {"chat_response": fallback_msg, "rep_change": 0, "action": "none"}

def process_chat(player, message):
    now = time.time()
    if now - cooldowns.get(player, 0) < cfg.get("spam_cooldown", 3.0):
        return
    cooldowns[player] = now

    data = fetch_ai_response(player, message)
    chat_msg = data.get("chat_response", "...").replace('"', "'")
    action = data.get("action", "none")
    total_rep = add_reputation(player, data.get("rep_change", 0))

    print(f"[{player}] Rep: {total_rep} | Action: {action}")
    send_rcon(f'say §4[Count Nosferatu]§f {chat_msg}')
    trigger_actions(player, action)

def handle_idle_events():
    while True:
        time.sleep(600)
        event = random.choice(["eclipse", "bats", "quote"])
        if event == "eclipse":
            send_rcon("say §4[Count Nosferatu]§f I am BORED! Bow before the darkness!", "time set night", "weather thunder")
        elif event == "bats":
            send_rcon("say §4[Count Nosferatu]§f Fly, my little pests!")
            [send_rcon("execute at @r run summon bat ~ ~2 ~") for _ in range(10)]
        elif event == "quote":
            voicelines = cfg.get("voicelines", [])
            if voicelines:
                send_rcon(f"say §4[Count Nosferatu]§f {random.choice(voicelines)}")

def main():
    Thread(target=handle_idle_events, daemon=True).start()
    print("Nosferatu Engine live. Streaming logs...")

    while True:
        try:
            if not os.path.exists(cfg["log_path"]):
                time.sleep(2)
                continue

            with open(cfg["log_path"], "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.2)
                        continue

                    chat_match = CHAT_RE.search(line)
                    if chat_match:
                        Thread(target=process_chat, args=chat_match.groups(), daemon=True).start()
                        continue

                    death_match = DEATH_RE.search(line)
                    if death_match:
                        player = death_match.group(1)
                        set_reputation(player, 0)
                        send_rcon(f"say §4[Count Nosferatu]§f Another mortal has rotted away... Favor reset for {player}!")
        except Exception as e:
            print(f"[Stream Error] {e}. Re-opening log file in 2s...")
            time.sleep(2)

if __name__ == "__main__":
    main()