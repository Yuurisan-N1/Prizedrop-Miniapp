<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Prize%20Drop%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Channels%7CAd%20Rewards%7CSpin%20Wheel%7CTask%20Board%7CGiveaway%20Entries&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Mandatory%20channel%20check;Ad%20reward%20runner;Spin%20wheel%20runner;Task%20board%20claims;Giveaway%20entries"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Prize%20Drop%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Prize Drop Bot</b> is a full automation bot for the Prize Drop Telegram Miniapp.<br/>
  It walks the complete daily cycle for every account: the mandatory channel check, the rewarded ad loop, the free spin wheel, the task board and the giveaway entries, all running automatically across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Prizedrop-Miniapp.git
cd Prizedrop-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening Prize Drop on Telegram Web.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Mandatory Channels
Runs the channel membership check the app requires before the rest of the miniapp is unlocked. A pass is reported as verified, and every channel that is still missing is listed on its own line instead of blocking silently.

### Ad Rewards
Runs the rewarded ad loop that the app pays for, paced by the cooldown the server publishes instead of a guessed one, and keeps going until the server itself reports that the daily limit for that network is reached. Every credited view gets its own line with the amount the server returned, and the limit the server reports is printed along with the server reason instead of ending the phase silently.

### Spin Wheel
Takes the spins the reward wheel still has available for the day and reports each credited amount. Once the server reports that the day's spins are used up, that refusal is printed with the server reason, so the phase never ends without an explanation.

### Task Board
Reads the task board straight from the server every cycle, so the bot always works the offers that are actually open for the account instead of a list baked into the code. Each settled task gets its own line with the credited amount, and a task the server no longer accepts is reported with the server reason instead of being dropped silently.

### Giveaway Entries
Reads the live giveaways with their target and their current progress, then enters the ticket balance the account collected on that run into the running giveaway, logging the accepted amount and the giveaway name. Tickets are only entered while the account still has some, so a spent balance closes the phase without noise.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Each account is logged with its profile name, its own phase lines, the total credited on that run and the ticket balance the server reports back for that account. The cycle number is tracked and logged at the start of each round.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
PrizeDrop-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>