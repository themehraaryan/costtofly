import pytest
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from visualizer import FlightVisualizer, generate_visualizations


class TestFlightVisualizer:
    
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame([
            {"source": "MakeMyTrip", "airline": "IndiGo", "departure": "10:00", "arrival": "12:00", "duration": "2h", "stops": "Non-stop", "price": 5000},
            {"source": "Goibibo", "airline": "Air India", "departure": "14:00", "arrival": "17:00", "duration": "3h", "stops": "1 stop", "price": 4500},
            {"source": "Cleartrip", "airline": "SpiceJet", "departure": "18:00", "arrival": "20:30", "duration": "2h 30m", "stops": "Non-stop", "price": 5500},
            {"source": "MakeMyTrip", "airline": "Vistara", "departure": "08:00", "arrival": "10:15", "duration": "2h 15m", "stops": "Non-stop", "price": 7000},
        ])
    
    @pytest.fixture
    def visualizer(self, tmp_path):
        return FlightVisualizer(output_dir=tmp_path)
    
    def test_generate_all_creates_charts(self, visualizer, sample_df, tmp_path):
        charts = visualizer.generate_all(sample_df)
        assert len(charts) > 0
        for chart_path in charts:
            assert chart_path.exists()
            assert chart_path.suffix == '.png'
            
    def test_generate_all_empty_df(self, visualizer):
        empty_df = pd.DataFrame()
        charts = visualizer.generate_all(empty_df)
        assert charts == []
        
    def test_generate_all_none_df(self, visualizer):
        charts = visualizer.generate_all(None)
        assert charts == []
        
    def test_price_by_airline_chart(self, visualizer, sample_df, tmp_path):
        path = visualizer.price_by_airline(sample_df)
        assert path is not None
        assert path.exists()
        
    def test_price_distribution_chart(self, visualizer, sample_df, tmp_path):
        path = visualizer.price_distribution(sample_df)
        assert path is not None
        assert path.exists()
        
    def test_cheapest_flights_chart(self, visualizer, sample_df, tmp_path):
        path = visualizer.cheapest_flights_comparison(sample_df)
        assert path is not None
        assert path.exists()
        
    def test_price_by_source_chart(self, visualizer, sample_df, tmp_path):
        path = visualizer.price_by_source(sample_df)
        assert path is not None
        assert path.exists()


class TestParseHour:
    
    @pytest.fixture
    def visualizer(self, tmp_path):
        return FlightVisualizer(output_dir=tmp_path)
    
    def test_parse_hour_valid(self, visualizer):
        assert visualizer._parse_hour("10:00") == 10
        assert visualizer._parse_hour("14:30") == 14
        assert visualizer._parse_hour("00:00") == 0
        assert visualizer._parse_hour("23:59") == 23
        
    def test_parse_hour_invalid(self, visualizer):
        assert visualizer._parse_hour("") == -1
        assert visualizer._parse_hour(None) == -1
        assert visualizer._parse_hour("invalid") == -1


class TestGenerateVisualizationsFunction:
    
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame([
            {"source": "MakeMyTrip", "airline": "IndiGo", "departure": "10:00", "arrival": "12:00", "duration": "2h", "stops": "Non-stop", "price": 5000},
        ])
    
    def test_generate_visualizations_creates_charts(self, sample_df, tmp_path):
        charts = generate_visualizations(sample_df, output_dir=tmp_path)
        assert len(charts) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
