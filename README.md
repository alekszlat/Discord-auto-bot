# 🎉 Discord Auto-Bot & Config Editor

> A fun little side‐project to learn Python, C++ UIs, and Python virtual environments.

---

## 🚀 Overview

This repository contains two parts:

1. **Discord Auto-Bot** (Python)  
   A bot that schedules and sends DMs on a cron-style schedule, reloads its config on the fly, and responds to simple commands.

2. **Config Editor** (C++ / wxWidgets)  
   A graphical UI for editing the bot’s configuration (`config.json`) and its list of scheduled jobs (`scheduler.json`).

You’ll brush up on:

- Python virtual environments & packaging  
- `discord.py`, APScheduler, and Watchdog  
- C++17, wxWidgets, and nlohmann/json  
- Cross-platform Linux & Windows considerations  

---

## 🛠️ Technologies & Frameworks

| Layer            | Framework / Library   |
|------------------|-----------------------|
| **Bot (Python)** | `discord.py`          |
|                  | APScheduler           |
|                  | Watchdog              |
|                  | Python 3.8+           |
|                  | Virtualenv (`.venv`)  |
| **UI (C++)**     | wxWidgets 3.2         |
|                  | nlohmann/json         |
|                  | C++17 (via CMake)     |

---

## 📦 Prerequisites

- **Linux** (Ubuntu/Debian recommended)  
- **Git**  
- **Python 3.8+**  
- **C++17** toolchain: `g++`, `cmake`, etc.

---

## 🔧 Setup & Installation

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

cd bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json      # edit token, IDs, timezone
python bot.py

sudo apt update
sudo apt install -y build-essential cmake libwxgtk3.2-dev nlohmann-json3-dev
cd ../ui_cpp
mkdir -p build && cd build
cmake ..
make
./DiscordConfigEditor
