# src/main.py
from flask import Flask, request, render_template, jsonify, send_file
from typing import Dict, List
from parser.trello_parser import TrelloParser
from linter.rule_engine import RuleEngine
from scoring.scorer import Scorer
from database.db_manager import DatabaseManager
from database.models import Board, List, Card, Report, Finding
from reports.csv_exporter import CSVExporter
from reports.html_exporter import HTMLExporter
import os

app = Flask(__name__)
db_manager = DatabaseManager()
db_manager.init_db()

current_directory= os.getcwd() 
print("Current Working Directory:", current_directory)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Save uploaded file temporarily
    upload_path = os.path.join('uploads', file.filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(upload_path)
    
    # Parse Trello JSON
    parser = TrelloParser(upload_path)
    parsed_data = parser.parse()
    
    # Run linting rules
    rule_engine = RuleEngine()
    findings = rule_engine.run_all_rules(parsed_data)
    
    # Calculate scores
    scorer = Scorer()
    scores = scorer.calculate_score(findings)
    
    # Store in database
    session = db_manager.get_session()
    # ... (database storage logic)
    session.commit()
    
    # Clean up
    os.remove(upload_path)
    
    return jsonify({
        'scores': scores,
        'findings': findings,
        'board_name': parsed_data['board']['name']
    })

@app.route('/export/csv')
def export_csv():
    #TODO
    #returns CSV file
    return 0

@app.route('/export/html')
def export_html():
    #TODO
    #returns html report
    return 0

if __name__ == '__main__':
    app.run(debug=True)