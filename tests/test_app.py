import pytest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, write_input


class TestFlaskApp:
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_index_loads(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'CostToFly' in response.data
        
    def test_results_page_loads(self, client):
        response = client.get('/results')
        assert response.status_code == 200
        
    def test_api_flights_returns_json(self, client):
        response = client.get('/api/flights')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
    def test_api_metrics_returns_json(self, client):
        response = client.get('/api/metrics')
        assert response.status_code == 200
        assert response.content_type == 'application/json'


class TestInputValidation:
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_search_missing_fields(self, client):
        response = client.post('/search', data={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        
    def test_search_invalid_departure_code_length(self, client):
        response = client.post('/search', data={
            'departure': 'DE',
            'arrival': 'BOM',
            'date': '01/01/2025'
        })
        assert response.status_code == 400
        
    def test_search_invalid_departure_code_chars(self, client):
        response = client.post('/search', data={
            'departure': 'D12',
            'arrival': 'BOM',
            'date': '01/01/2025'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'letters' in data['error'].lower()
        
    def test_search_invalid_date_format(self, client):
        response = client.post('/search', data={
            'departure': 'DEL',
            'arrival': 'BOM',
            'date': '2025-01-01'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'DD/MM/YYYY' in data['error']


class TestWriteInput:
    
    def test_write_input_valid(self, tmp_path, monkeypatch):
        test_file = tmp_path / "input.json"
        monkeypatch.setattr('app.INPUT_FILE', test_file)
        
        write_input('DEL', 'BOM', '01/01/2025')
        
        with open(test_file) as f:
            data = json.load(f)
        
        assert data['departure'] == 'DEL'
        assert data['arrival'] == 'BOM'
        assert data['date'] == '01/01/2025'
        
    def test_write_input_uppercase(self, tmp_path, monkeypatch):
        test_file = tmp_path / "input.json"
        monkeypatch.setattr('app.INPUT_FILE', test_file)
        
        write_input('del', 'bom', '01/01/2025')
        
        with open(test_file) as f:
            data = json.load(f)
        
        assert data['departure'] == 'DEL'
        assert data['arrival'] == 'BOM'
        
    def test_write_input_invalid_code(self):
        with pytest.raises(ValueError):
            write_input('D12', 'BOM', '01/01/2025')
            
    def test_write_input_short_code(self):
        with pytest.raises(ValueError):
            write_input('DE', 'BOM', '01/01/2025')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
