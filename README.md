# GATE CSE Forecast - Quick Start Guide

Welcome to the GATE CSE Forecast Lab! This system has two parts: a **Python Backend** (which handles the AI forecasting and database) and a **React Frontend** (which gives you a beautiful dashboard to interact with).

You need to run **both** of these parts at the same time to use the application.

---

## 🛠️ Step 1: Start the Backend (Terminal 1)

The backend is an API that serves data from our SQLite database to the frontend.

1. Open your terminal app (like Terminal on macOS or iTerm).
2. Navigate to your project folder:
   ```bash
   cd "/Users/My Applications /Exam-paper-prediction/gate_forecasting"
   ```
3. Activate the Python virtual environment:
   ```bash
   source venv/bin/activate
   ```
4. Start the server:
   ```bash
   uvicorn api.main:app --reload
   ```
   *(Keep this terminal open and running. You should see it say "Application startup complete".)*

---

## 🎨 Step 2: Start the Frontend (Terminal 2)

The frontend is the visual dashboard built with React.

1. Open a **new** terminal window (leave Terminal 1 running).
2. Navigate to the frontend folder inside your project:
   ```bash
   cd "/Users/My Applications /Exam-paper-prediction/gate_forecasting/web"
   ```
3. Start the React app:
   ```bash
   npm run dev
   ```
   *(Keep this terminal open and running.)*

---

## 🌐 Step 3: Open the Dashboard in your Browser

1. Open Google Chrome, Safari, or your preferred web browser.
2. Type this URL into the address bar and press Enter:
   **`http://localhost:5173`**

You should now see the dark-mode dashboard with 3 tabs at the top!

---

## 🎮 Step 4: How to Operate the App

Once you are in the browser, here is how you interact with the 3 modes:

### Tab 1: Historical Forecast Lab (The Simulator)
- **What it does:** Allows you to test the model on past years (e.g., 2021).
- **How to use it:** You will see the "Target Year: 2021". Click the **"Reveal Actual 2021 Paper"** button.
- **What to look for:** A table will appear showing exactly what the AI predicted vs what actually appeared on the real GATE 2021 exam. It will grade the AI with green "Strong Match" badges or red "False Positive" badges.

### Tab 2: Model Intelligence
- **What it does:** Shows how the AI learns from its mistakes.
- **How to use it:** Click the tab. Scroll down the timeline.
- **What to look for:** You will see a log of every year the AI messed up, what hypothesis it generated to fix it, and whether the strategy update improved its F1 Score.

### Tab 3: GATE 2027 Forecast
- **What it does:** The final output of the entire system.
- **How to use it:** Click the tab.
- **What to look for:** You will see the predicted questions for the 2027 exam. Expand the "Why this prediction?" sections to see the AI's evidence for choosing that topic.

---

## ⚠️ Important Note on Generating New Years
Right now, you can only view data for **2021** in the Lab, because that is the only year we ran the simulation script for in the backend. 

If you want to view 2022 in the dashboard, open a 3rd terminal window and run:
```bash
cd "/Users/My Applications /Exam-paper-prediction/gate_forecasting"
python3 scripts/forecast_runner.py --year 2022
```
Then refresh your browser!
