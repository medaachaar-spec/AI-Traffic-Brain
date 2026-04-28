# AI Traffic Brain — Intelligent Urban Traffic Management System

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![SUMO](https://img.shields.io/badge/SUMO-1.19%2B-green?logo=data:image/png;base64,&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-Academic-lightgrey)

A multi-controller traffic intelligence system that simulates, learns, and optimises signal timing across a 3-intersection urban network. Built on SUMO + TraCI, it progresses from a simple fixed cycle to a demand-adaptive smart controller and a tabular Q-learning agent trained via imitation from the smart policy.

---

## Key Results

Average vehicle waiting time across a full simulation episode:

| Controller | Avg Waiting Time | vs Fixed |
|---|---|---|
| Fixed (30 s / 3 s cycle) | 241 s | baseline |
| Smart (demand-adaptive) | 213 s | −12 % |
| RL (Q-learning, pretrained) | 183 s | −24 % |

---

## Features

| Mode | Description |
|---|---|
| **Fixed** | Classic 30 s green / 3 s yellow cycle, same timing for all intersections |
| **Smart** | Normalised pressure-based FSM with green-wave coordination and congestion relief |
| **Vision** | Smart controller augmented with a camera bridge for per-vehicle type detection |
| **RL** | Tabular Q-learning agent with phase-aware state (11 features) and imitation pretraining from Smart |
| **RL-Pretrain** | Warm-starts the Q-table from Smart's policy before running Q-learning |
| **Hybrid** | Smart runs the FSM; RL overrides only when its confidence exceeds a threshold |

---

## Screenshots

> _Dashboard and live map screenshots — add your own images to `docs/screenshots/` and update the paths below._

| Dashboard overview | Live schematic map |
|---|---|
| ![dashboard](docs/screenshots/dashboard.png) | ![live map](docs/screenshots/live_map.png) |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/medaachaar-spec/AI-Traffic-Brain.git
cd AI-Traffic-Brain
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install SUMO

Download and install SUMO ≥ 1.19 from the official site:
**https://sumo.dlr.de/docs/Downloads.php**

Make sure the `sumo` and `sumo-gui` binaries are on your `PATH`, and that the `SUMO_HOME` environment variable is set:

```bash
# Linux / macOS
export SUMO_HOME=/usr/share/sumo

# Windows (PowerShell)
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
```

---

## Usage

All commands are run from the project root.

### Run a simulation

```bash
# Fixed-cycle controller (headless)
python main.py --mode fixed

# Demand-adaptive smart controller
python main.py --mode smart

# Smart controller + camera vision bridge
python main.py --mode vision

# Q-learning inference (requires a trained Q-table)
python main.py --mode rl

# Open SUMO-GUI for any mode
python main.py --mode smart --gui
```

### Train the RL agent

```bash
# Imitation pretraining from Smart (5 eps), then Q-learning (15 eps)
python main.py --mode rl-pretrain --pretrain-episodes 5 --train-episodes-after-pretrain 15

# Pure Q-learning training
python main.py --mode rl-train --episodes 50
```

### Launch the dashboard

```bash
streamlit run dashboard/app.py
```

Open your browser at `http://localhost:8501`.

---

## Project Structure

```
AI-Traffic-Brain/
├── core/
│   ├── traffic_env.py        # SUMO/TraCI environment wrapper
│   ├── fixed_controller.py   # Fixed-cycle controller
│   ├── smart_controller.py   # Demand-adaptive FSM controller
│   ├── rl_controller.py      # Tabular Q-learning controller
│   ├── vision_bridge.py      # Camera-vision controller bridge
│   └── camera_detector.py    # Per-vehicle type detection
├── dashboard/
│   ├── app.py                # Streamlit comparison dashboard
│   ├── map_view.py           # Map utilities
│   └── pages/
│       └── live_map.py       # Animated live schematic map
├── simulation/
│   └── simulation.sumocfg    # SUMO network configuration
├── data/                     # Generated CSVs and Q-table (gitignored)
├── main.py                   # Simulation entry point & CLI
├── requirements.txt
└── README.md
```

---

## Authors

**ACHAAR Mohammed Amine** 
Institut National des Postes et Télécommunications (INPT) — Rabat
Academic year 2025–2026
