import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd

from loggerconfig import setup_logger
from dataAnalyser import DataAnalyser
from visualizer import generate_visualizations

logger = setup_logger()

app = Flask(__name__, 
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static"))

INPUT_FILE = Path(__file__).parent / "input.json"
RESULTS_DIR = Path(__file__).parent / "Results"


def write_input(departure: str, arrival: str, date: str) -> None:
    departure = departure.upper().strip()
    arrival = arrival.upper().strip()
    date = date.strip()
    
    if not departure.isalpha() or len(departure) != 3:
        raise ValueError(f"Invalid departure code: {departure}")
    if not arrival.isalpha() or len(arrival) != 3:
        raise ValueError(f"Invalid arrival code: {arrival}")
    
    data = {
        "departure": departure,
        "arrival": arrival,
        "date": date
    }
    with open(INPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def run_scraper() -> bool:
    main_path = Path(__file__).parent / "main.py"
    try:
        result = subprocess.run(
            [sys.executable, str(main_path)],
            capture_output=True,
            text=True,
            timeout=900,
            cwd=str(Path(__file__).parent)
        )
        
        if result.returncode != 0:
            logger.error(f"Scraper failed. stderr: {result.stderr[:500] if result.stderr else 'None'}")
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error("Scraper timed out after 15 minutes")
        return False
    except Exception as e:
        logger.error(f"Failed to run scraper: {e}")
        return False


def get_latest_results() -> tuple[pd.DataFrame, dict, list[Path]]:
    try:
        df, metrics = DataAnalyser.load_latest_results(RESULTS_DIR)
    except Exception as e:
        logger.error(f"Failed to load results: {e}")
        df, metrics = None, {}
    
    charts_dir = RESULTS_DIR / "charts"
    charts = []
    if charts_dir.exists():
        charts = sorted(charts_dir.glob("*.png"), reverse=True)[:6]
    
    return df, metrics, charts


@app.route('/')
def index():
    current_input = {}
    if INPUT_FILE.exists():
        with open(INPUT_FILE, 'r') as f:
            current_input = json.load(f)
    
    return render_template('index.html', current_input=current_input)


@app.route('/search', methods=['POST'])
def search():
    departure = request.form.get('departure', '').strip()
    arrival = request.form.get('arrival', '').strip()
    date = request.form.get('date', '').strip()
    
    if not departure or not arrival or not date:
        return jsonify({'error': 'All fields are required'}), 400
    
    if len(departure) != 3 or len(arrival) != 3:
        return jsonify({'error': 'City codes must be 3 characters (e.g., DEL, BLR)'}), 400
    
    if not departure.isalpha() or not arrival.isalpha():
        return jsonify({'error': 'City codes must contain only letters'}), 400
    
    try:
        datetime.strptime(date, '%d/%m/%Y')
    except ValueError:
        return jsonify({'error': 'Date format must be DD/MM/YYYY'}), 400
    
    write_input(departure, arrival, date)
    
    success = run_scraper()
    
    if not success:
        return jsonify({'error': 'Scraping failed. Check logs for details.'}), 500
    
    df, metrics, _ = get_latest_results()
    
    if df is not None and not df.empty:
        generate_visualizations(df, metrics)
    
    return jsonify({'success': True, 'redirect': '/results'})


@app.route('/results')
def results():
    df, metrics, charts = get_latest_results()
    
    current_input = {}
    if INPUT_FILE.exists():
        with open(INPUT_FILE, 'r') as f:
            current_input = json.load(f)
    
    flights_data = []
    if df is not None and not df.empty:
        flights_data = df.head(50).to_dict('records')
    
    chart_files = [c.name for c in charts]
    
    return render_template('results.html',
                          flights=flights_data,
                          metrics=metrics,
                          charts=chart_files,
                          input_data=current_input,
                          total_flights=len(df) if df is not None else 0)


@app.route('/charts/<filename>')
def serve_chart(filename):
    charts_dir = RESULTS_DIR / "charts"
    return send_from_directory(str(charts_dir), filename)


@app.route('/api/flights')
def api_flights():
    df, _, _ = get_latest_results()
    if df is None or df.empty:
        return jsonify([])
    return jsonify(df.to_dict('records'))


@app.route('/api/metrics')
def api_metrics():
    _, metrics, _ = get_latest_results()
    return jsonify(metrics)


if __name__ == '__main__':
    (Path(__file__).parent / "templates").mkdir(exist_ok=True)
    (Path(__file__).parent / "static").mkdir(exist_ok=True)
    
    app.run(debug=False, port=5000, use_reloader=False)

