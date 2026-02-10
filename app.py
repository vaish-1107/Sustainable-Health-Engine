from flask import Flask, render_template, request, redirect
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

FILE_PATH = "dashboard_inputs.xlsx"

# Columns for input and metrics
input_cols = [
    "planned_study_time", "actual_study_time", "break_time", "personal_care",
    "active_tasks", "deadlines", "context_switches", "task_complexity",
    "stress", "fatigue", "exhaustion", "motivation",
    "sleep_duration", "sleep_quality", "holidays", "micro_breaks"
]

metric_cols = [
    "time_poverty_index", "work_imbalance", "mental_strain",
    "recovery_deficit_score", "sustainability_score", "burnout_risk"
]

all_cols = input_cols + metric_cols

# Create Excel if it doesn't exist
if not os.path.exists(FILE_PATH):
    pd.DataFrame(columns=all_cols).to_excel(FILE_PATH, index=False)

def safe_float(value):
    """Safely convert value to float, handling empty strings and None"""
    if value == '' or value is None or value == 'nan':
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def calculate_metrics(data):
    data = data.copy()
    
    # Safely convert all numeric inputs
    data["planned_study_time"] = safe_float(data.get("planned_study_time"))
    data["actual_study_time"] = safe_float(data.get("actual_study_time"))
    data["active_tasks"] = safe_float(data.get("active_tasks"))
    data["deadlines"] = safe_float(data.get("deadlines"))
    data["context_switches"] = safe_float(data.get("context_switches"))
    data["stress"] = safe_float(data.get("stress"))
    data["fatigue"] = safe_float(data.get("fatigue"))
    data["exhaustion"] = safe_float(data.get("exhaustion"))
    data["sleep_duration"] = safe_float(data.get("sleep_duration"))
    data["micro_breaks"] = safe_float(data.get("micro_breaks"))
    
    # Keep text fields as-is
    for col in ["task_complexity", "sleep_quality", "holidays", "break_time", "personal_care", "motivation"]:
        if col not in data:
            data[col] = ""
    
    # Metrics calculations with safe floats
    data["time_poverty_index"] = data["planned_study_time"] - data["actual_study_time"]
    data["work_imbalance"] = data["active_tasks"] + data["deadlines"] + data["context_switches"]
    data["mental_strain"] = data["stress"] + data["fatigue"] + data["exhaustion"]
    
    recovery_deficit = max(0, 8 - data["sleep_duration"]) + max(0, 3 - data["micro_breaks"])
    data["recovery_deficit_score"] = recovery_deficit
    
    data["sustainability_score"] = max(0, 100 - (
        data["time_poverty_index"] + 
        data["work_imbalance"] + 
        data["mental_strain"] + 
        data["recovery_deficit_score"]
    ))
    
    data["burnout_risk"] = (data["time_poverty_index"] + data["work_imbalance"] + 
                           data["mental_strain"] + data["recovery_deficit_score"]) / 4
    
    return data

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Collect inputs from form with safe defaults
        data = {}
        for col in input_cols:
            val = request.form.get(col, "")
            data[col] = val  # Keep as-is, calculate_metrics will handle conversion

        # Add timestamp
        data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Calculate metrics (handles all conversions safely)
        data = calculate_metrics(data)

        # Append to Excel
        try:
            df = pd.read_excel(FILE_PATH)
        except:
            df = pd.DataFrame(columns=all_cols)
        
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(FILE_PATH, index=False)

        return redirect("/metrics")

    return render_template("index.html")

@app.route("/metrics")
def metrics():
    try:
        df = pd.read_excel(FILE_PATH)
    except:
        df = pd.DataFrame(columns=all_cols)
    
    if len(df) == 0:
        # Return default values if no data
        latest = {col: 0 for col in metric_cols}
    else:
        # Get latest submission, ensure numeric values
        latest_row = df.iloc[-1]
        latest = {}
        for col in metric_cols:
            latest[col] = safe_float(latest_row.get(col, 0))
    
    # Prepare history data for charts (last 20 entries or all if less)
    if len(df) > 0:
        history_df = df.tail(20).copy()
        try:
            history_df['timestamp'] = pd.to_datetime(history_df.get('timestamp', pd.date_range(start='2026-01-01', periods=len(history_df))))
            history_df = history_df.sort_values('timestamp')
            
            history_data = {
                'labels': history_df['timestamp'].dt.strftime('%m-%d %H:%M').tolist(),
                'time_poverty': [safe_float(x) for x in history_df['time_poverty_index']],
                'work_imbalance': [safe_float(x) for x in history_df['work_imbalance']],
                'mental_strain': [safe_float(x) for x in history_df['mental_strain']],
                'recovery_deficit': [safe_float(x) for x in history_df['recovery_deficit_score']],
                'sustainability': [safe_float(x) for x in history_df['sustainability_score']],
                'burnout_risk': [safe_float(x) for x in history_df['burnout_risk']]
            }
        except:
            history_data = {
                'labels': ['No data'],
                'time_poverty': [0],
                'work_imbalance': [0],
                'mental_strain': [0],
                'recovery_deficit': [0],
                'sustainability': [100],
                'burnout_risk': [0]
            }
    else:
        history_data = {
            'labels': ['No data'],
            'time_poverty': [0],
            'work_imbalance': [0],
            'mental_strain': [0],
            'recovery_deficit': [0],
            'sustainability': [100],
            'burnout_risk': [0]
        }
    
    return render_template("metrics.html", metrics=latest, history=history_data)

if __name__ == "__main__":
    app.run(debug=True)


app.py
