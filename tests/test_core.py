import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.utils import (
    load_input,
    parse_duration_minutes,
    parse_price,
    deduplicate_flights,
    build_flight_record
)
from dataAnalyser import DataAnalyser, FlightMetrics


class TestInputValidation:
    
    def test_parse_duration_hours_minutes(self):
        assert parse_duration_minutes("2h 30m") == 150
        assert parse_duration_minutes("1h 15m") == 75
        assert parse_duration_minutes("3h") == 180
        
    def test_parse_duration_minutes_only(self):
        assert parse_duration_minutes("45m") == 45
        assert parse_duration_minutes("90m") == 90
        
    def test_parse_duration_invalid(self):
        assert parse_duration_minutes("") == 9999
        assert parse_duration_minutes(None) == 9999
        assert parse_duration_minutes("invalid") == 9999
        
    def test_parse_price_valid(self):
        assert parse_price("₹5,629") == 5629
        assert parse_price("Price: ₹ 12,345") == 12345
        assert parse_price("₹1000 ₹2000 ₹3000") == 3000
        
    def test_parse_price_invalid(self):
        assert parse_price("") == 0
        assert parse_price("No price here") == 0
        assert parse_price("₹500") == 0
        assert parse_price("₹999999") == 0


class TestDeduplication:
    
    def test_deduplicate_empty(self):
        assert deduplicate_flights([]) == []
        
    def test_deduplicate_no_duplicates(self):
        flights = [
            {"departure": "10:00", "arrival": "12:00", "price": 5000},
            {"departure": "14:00", "arrival": "16:00", "price": 6000},
        ]
        result = deduplicate_flights(flights)
        assert len(result) == 2
        
    def test_deduplicate_with_duplicates(self):
        flights = [
            {"departure": "10:00", "arrival": "12:00", "price": 5000},
            {"departure": "10:00", "arrival": "12:00", "price": 5000},
            {"departure": "14:00", "arrival": "16:00", "price": 6000},
        ]
        result = deduplicate_flights(flights)
        assert len(result) == 2


class TestFlightRecord:
    
    def test_build_flight_record(self):
        record = build_flight_record(
            source="TestSource",
            airline="TestAirline",
            flight_code="TS123",
            departure="10:00",
            arrival="12:00",
            duration="2h",
            stops="Non-stop",
            price=5000
        )
        
        assert record["source"] == "TestSource"
        assert record["airline"] == "TestAirline"
        assert record["flight_code"] == "TS123"
        assert record["departure"] == "10:00"
        assert record["arrival"] == "12:00"
        assert record["duration"] == "2h"
        assert record["stops"] == "Non-stop"
        assert record["price"] == 5000
        assert "timestamp" in record
        
    def test_build_flight_record_default_airline(self):
        record = build_flight_record(
            source="Test",
            airline="",
            flight_code="",
            departure="10:00",
            arrival="12:00",
            duration="2h",
            stops="Non-stop",
            price=5000
        )
        assert record["airline"] == "Unknown"


class TestFlightMetrics:
    
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame([
            {"source": "MakeMyTrip", "airline": "IndiGo", "departure": "10:00", "arrival": "12:00", "duration": "2h", "stops": "Non-stop", "price": 5000},
            {"source": "Goibibo", "airline": "Air India", "departure": "14:00", "arrival": "17:00", "duration": "3h", "stops": "1 stop", "price": 4500},
            {"source": "Cleartrip", "airline": "IndiGo", "departure": "18:00", "arrival": "20:30", "duration": "2h 30m", "stops": "Non-stop", "price": 5500},
        ])
    
    def test_compute_cheapest_overall(self, sample_df):
        metrics = FlightMetrics(sample_df)
        metrics.compute_all()
        
        assert "cheapest_overall" in metrics.metrics
        assert metrics.metrics["cheapest_overall"]["price"] == 4500
        assert metrics.metrics["cheapest_overall"]["airline"] == "Air India"
        
    def test_compute_price_stats(self, sample_df):
        metrics = FlightMetrics(sample_df)
        metrics.compute_all()
        
        assert "price_stats" in metrics.metrics
        stats = metrics.metrics["price_stats"]
        assert stats["min"] == 4500
        assert stats["max"] == 5500
        
    def test_compute_cheapest_per_source(self, sample_df):
        metrics = FlightMetrics(sample_df)
        metrics.compute_all()
        
        assert "cheapest_per_source" in metrics.metrics
        per_source = metrics.metrics["cheapest_per_source"]
        assert "MakeMyTrip" in per_source
        assert "Goibibo" in per_source
        assert "Cleartrip" in per_source
        assert per_source["Goibibo"]["price"] == 4500


class TestDataAnalyser:
    
    def test_create_master_dataframe_single_source(self):
        analyser = DataAnalyser()
        df1 = pd.DataFrame([
            {"source": "MakeMyTrip", "airline": "IndiGo", "departure": "10:00", "arrival": "12:00", "duration": "2h", "stops": "Non-stop", "price": 5000, "flight_code": "6E123", "timestamp": "2024-01-01"},
        ])
        
        result = analyser._create_master_dataframe([df1])
        assert len(result) == 1
        assert list(result.columns) == ['source', 'airline', 'flight_code', 'departure', 'arrival', 'duration', 'stops', 'price', 'timestamp']
        
    def test_create_master_dataframe_deduplication(self):
        analyser = DataAnalyser()
        df1 = pd.DataFrame([
            {"source": "MakeMyTrip", "airline": "IndiGo", "departure": "10:00", "arrival": "12:00", "duration": "2h", "stops": "Non-stop", "price": 5000, "flight_code": "6E123", "timestamp": "2024-01-01"},
        ])
        df2 = pd.DataFrame([
            {"source": "Goibibo", "airline": "IndiGo", "departure": "10:00", "arrival": "12:00", "duration": "2h", "stops": "Non-stop", "price": 5000, "flight_code": "6E123", "timestamp": "2024-01-01"},
        ])
        
        result = analyser._create_master_dataframe([df1, df2])
        assert len(result) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
