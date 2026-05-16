========================================================
AI TRAFFIC BRAIN — CMD PROMPTS & COMMANDS
========================================================

Project:
AI Traffic Brain — Intelligent Urban Traffic Management System

Purpose:
This file contains all important CMD commands used during
development, simulation, RL training, dashboard execution,
Git workflow, debugging, and maintenance.

========================================================
1. NAVIGATE TO PROJECT
========================================================

cd C:\Users\HP\AI-Traffic-Brain

Check project files:

dir

========================================================
2. OPEN PROJECT IN VSCODE
========================================================

code .

========================================================
3. START STREAMLIT DASHBOARD
========================================================

Default port:

streamlit run dashboard/app.py

Alternative port (if 8501 already used):

streamlit run dashboard/app.py --server.port 8502

Safe version:

python -m streamlit run dashboard/app.py

Dashboard URLs:

http://localhost:8501

or

http://localhost:8502

========================================================
4. RUN TRAFFIC SIMULATION
========================================================

--------------------------------------------------------
4.1 Fixed Controller
--------------------------------------------------------

python main.py --mode fixed --cfg simulation/simulation.sumocfg

--------------------------------------------------------
4.2 Smart Controller
--------------------------------------------------------

python main.py --mode smart --cfg simulation/simulation.sumocfg

--------------------------------------------------------
4.3 Vision Controller
--------------------------------------------------------

python main.py --mode vision --cfg simulation/simulation.sumocfg

--------------------------------------------------------
4.4 Reinforcement Learning Controller
--------------------------------------------------------

python main.py --mode rl --cfg simulation/simulation.sumocfg

========================================================
5. RUN SIMULATION WITH SUMO GUI
========================================================

--------------------------------------------------------
5.1 Fixed + GUI
--------------------------------------------------------

python main.py --mode fixed --cfg simulation/simulation.sumocfg --gui

--------------------------------------------------------
5.2 Smart + GUI
--------------------------------------------------------

python main.py --mode smart --cfg simulation/simulation.sumocfg --gui

--------------------------------------------------------
5.3 RL + GUI
--------------------------------------------------------

python main.py --mode rl --cfg simulation/simulation.sumocfg --gui

========================================================
6. RL TRAINING
========================================================

--------------------------------------------------------
6.1 Quick RL Test
--------------------------------------------------------

python main.py --mode rl-train --episodes 10 --cfg simulation/simulation.sumocfg

--------------------------------------------------------
6.2 Medium Training
--------------------------------------------------------

python main.py --mode rl-train --episodes 100 --cfg simulation/simulation.sumocfg

--------------------------------------------------------
6.3 Long Training
--------------------------------------------------------

python main.py --mode rl-train --episodes 1000 --cfg simulation/simulation.sumocfg

========================================================
7. RL TRAINING WITH SEED
========================================================

Purpose:
Use seeds to generate different traffic randomness patterns.

--------------------------------------------------------
7.1 Train with Seed
--------------------------------------------------------

python main.py --mode rl-train --episodes 100 --seed 42 --cfg simulation/simulation.sumocfg

--------------------------------------------------------
7.2 Run RL with Seed
--------------------------------------------------------

python main.py --mode rl --seed 42 --cfg simulation/simulation.sumocfg

========================================================
8. MULTI-SEED RL TRAINING
========================================================

Purpose:
Avoid overfitting RL to one traffic pattern.

python main.py --mode rl-train --episodes 50 --seed 42 --cfg simulation/simulation.sumocfg

python main.py --mode rl-train --episodes 50 --seed 43 --cfg simulation/simulation.sumocfg

python main.py --mode rl-train --episodes 50 --seed 44 --cfg simulation/simulation.sumocfg

python main.py --mode rl-train --episodes 50 --seed 45 --cfg simulation/simulation.sumocfg

python main.py --mode rl-train --episodes 50 --seed 46 --cfg simulation/simulation.sumocfg

========================================================
9. RL PRETRAINING
========================================================

Purpose:
Pretrain RL using Smart Controller logic.

--------------------------------------------------------
9.1 RL Pretraining
--------------------------------------------------------

python main.py --mode rl-pretrain --pretrain-episodes 5 --train-episodes-after-pretrain 15 --cfg simulation/simulation.sumocfg

--------------------------------------------------------
9.2 RL Pretraining with Seed
--------------------------------------------------------

python main.py --mode rl-pretrain --pretrain-episodes 5 --train-episodes-after-pretrain 15 --cfg simulation/simulation.sumocfg --seed 42

========================================================
10. CONTROLLER COMPARISON TESTS
========================================================

--------------------------------------------------------
10.1 Fixed
--------------------------------------------------------

python main.py --mode fixed --seed 42 --cfg simulation/simulation.sumocfg

--------------------------------------------------------
10.2 Smart
--------------------------------------------------------

python main.py --mode smart --seed 42 --cfg simulation/simulation.sumocfg

--------------------------------------------------------
10.3 Vision
--------------------------------------------------------

python main.py --mode vision --seed 42 --cfg simulation/simulation.sumocfg

--------------------------------------------------------
10.4 RL
--------------------------------------------------------

python main.py --mode rl --seed 42 --cfg simulation/simulation.sumocfg

========================================================
11. Q-TABLE MANAGEMENT
========================================================

--------------------------------------------------------
11.1 Backup Current Q-table
--------------------------------------------------------

copy data\qtable.pkl data\qtable_backup.pkl

--------------------------------------------------------
11.2 Backup Before Major RL Change
--------------------------------------------------------

copy data\qtable.pkl data\qtable_before_change.pkl

--------------------------------------------------------
11.3 Delete Current Q-table
--------------------------------------------------------

WARNING:
Deletes learned RL model.

del data\qtable.pkl

--------------------------------------------------------
11.4 Delete Temporary RL Files
--------------------------------------------------------

del data\qtable.bak

del data\qtable.tmp

========================================================
12. VIEW RESULT FILES
========================================================

View all files in data folder:

dir data

View CSV result files:

dir data\*.csv

View Q-table files:

dir data\*.pkl

========================================================
13. PYTHON CODE VALIDATION
========================================================

--------------------------------------------------------
13.1 Validate Main File
--------------------------------------------------------

python -m py_compile main.py

--------------------------------------------------------
13.2 Validate Dashboard
--------------------------------------------------------

python -m py_compile dashboard\app.py

--------------------------------------------------------
13.3 Validate Live Map
--------------------------------------------------------

python -m py_compile dashboard\pages\live_map.py

--------------------------------------------------------
13.4 Validate RL Controller
--------------------------------------------------------

python -m py_compile core\rl_controller.py

--------------------------------------------------------
13.5 Validate Multiple Important Files
--------------------------------------------------------

python -m py_compile main.py core\rl_controller.py dashboard\app.py dashboard\pages\live_map.py

========================================================
14. INSTALL DEPENDENCIES
========================================================

--------------------------------------------------------
14.1 Install from requirements.txt
--------------------------------------------------------

pip install -r requirements.txt

--------------------------------------------------------
14.2 Safe pip Version
--------------------------------------------------------

python -m pip install -r requirements.txt

--------------------------------------------------------
14.3 Install Streamlit
--------------------------------------------------------

pip install streamlit

--------------------------------------------------------
14.4 Install SUMO Python Libraries
--------------------------------------------------------

pip install traci sumolib

========================================================
15. CHECK SOFTWARE VERSIONS
========================================================

--------------------------------------------------------
15.1 Python Version
--------------------------------------------------------

python --version

--------------------------------------------------------
15.2 Pip Version
--------------------------------------------------------

pip --version

--------------------------------------------------------
15.3 Streamlit Version
--------------------------------------------------------

streamlit --version

or

python -m streamlit --version

========================================================
16. GIT — STATUS & HISTORY
========================================================

--------------------------------------------------------
16.1 Check Git Status
--------------------------------------------------------

git status

--------------------------------------------------------
16.2 View Changes
--------------------------------------------------------

git diff

--------------------------------------------------------
16.3 View Commit History
--------------------------------------------------------

git log --oneline

========================================================
17. GIT — SAVE CHANGES
========================================================

--------------------------------------------------------
17.1 Add All Files
--------------------------------------------------------

git add .

--------------------------------------------------------
17.2 Commit Changes
--------------------------------------------------------

git commit -m "your message"

--------------------------------------------------------
17.3 Push Changes
--------------------------------------------------------

git push

========================================================
18. GIT — PUSH REJECTED FIX
========================================================

If push is rejected:

git pull --rebase origin main

git push

========================================================
19. GIT — INDEX.LOCK FIX
========================================================

If Git says:

"Unable to create .git/index.lock"

Run:

del .git\index.lock

Then:

git status

========================================================
20. GIT — SAVE BEFORE MAJOR CHANGES
========================================================

git add .

git commit -m "Save current working version before major changes"

========================================================
21. GIT — RESTORE FILES
========================================================

WARNING:
Discard local modifications.

--------------------------------------------------------
21.1 Restore Dashboard
--------------------------------------------------------

git restore dashboard\app.py

--------------------------------------------------------
21.2 Restore Live Map
--------------------------------------------------------

git restore dashboard\pages\live_map.py

========================================================
22. GIT — UNSTAGE FILES
========================================================

git restore --staged dashboard\app.py

========================================================
23. GIT — CREATE TEST BRANCH
========================================================

--------------------------------------------------------
23.1 Create Branch
--------------------------------------------------------

git checkout -b dashboard-rebuild

--------------------------------------------------------
23.2 Return to Main
--------------------------------------------------------

git checkout main

========================================================
24. CLEAN PYTHON CACHE
========================================================

--------------------------------------------------------
24.1 Remove Root Cache
--------------------------------------------------------

rmdir /s /q __pycache__

--------------------------------------------------------
24.2 Remove All Nested Caches
--------------------------------------------------------

for /d /r . %d in (__pycache__) do @if exist "%d" rmdir /s /q "%d"

========================================================
25. FAST DAILY WORKFLOW
========================================================

--------------------------------------------------------
25.1 Open Project
--------------------------------------------------------

cd C:\Users\HP\AI-Traffic-Brain

--------------------------------------------------------
25.2 Open VSCode
--------------------------------------------------------

code .

--------------------------------------------------------
25.3 Start Dashboard
--------------------------------------------------------

streamlit run dashboard/app.py --server.port 8502

--------------------------------------------------------
25.4 Run RL Simulation
--------------------------------------------------------

python main.py --mode rl --cfg simulation/simulation.sumocfg

--------------------------------------------------------
25.5 Train RL
--------------------------------------------------------

python main.py --mode rl-train --episodes 100 --cfg simulation/simulation.sumocfg

========================================================
26. MOST IMPORTANT COMMANDS
========================================================

cd C:\Users\HP\AI-Traffic-Brain

streamlit run dashboard/app.py --server.port 8502

python main.py --mode fixed --cfg simulation/simulation.sumocfg

python main.py --mode smart --cfg simulation/simulation.sumocfg

python main.py --mode vision --cfg simulation/simulation.sumocfg

python main.py --mode rl --cfg simulation/simulation.sumocfg

python main.py --mode rl-train --episodes 100 --cfg simulation/simulation.sumocfg

python main.py --mode rl-pretrain --pretrain-episodes 5 --train-episodes-after-pretrain 15 --cfg simulation/simulation.sumocfg

git status

git add .

git commit -m "message"

git pull --rebase origin main

git push

========================================================
END OF FILE
========================================================