from typing import Any
from datetime import datetime
from pathlib import Path
import pandas as pd
import json

from loggerconfig import setup_logger
from scrapers.utils import parse_duration_minutes

logger = setup_logger()


class FlightMetrics:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.metrics = {}
        
    def compute_all(self) -> dict:
        if self.df.empty:
            return {}
        
        self._compute_cheapest_overall()
        self._compute_shortest_duration()
        self._compute_best_value()
        self._compute_cheapest_per_airline()
        self._compute_cheapest_per_source()
        self._compute_price_stats()
        self._compute_stop_analysis()
        
        return self.metrics
    
    def _parse_duration_minutes(self, duration_str: str) -> int:
        return parse_duration_minutes(duration_str) if parse_duration_minutes(duration_str) != 9999 else float('inf')
    
    def _compute_cheapest_overall(self):
        cheapest = self.df.loc[self.df['price'].idxmin()]
        self.metrics['cheapest_overall'] = cheapest.to_dict()
    
    def _compute_shortest_duration(self):
        df_with_dur = self.df.copy()
        df_with_dur['duration_minutes'] = df_with_dur['duration'].apply(self._parse_duration_minutes)
        valid = df_with_dur[df_with_dur['duration_minutes'] < float('inf')]
        
        if not valid.empty:
            shortest = valid.loc[valid['duration_minutes'].idxmin()]
            result = shortest.to_dict()
            result['duration_minutes'] = int(result['duration_minutes'])
            self.metrics['shortest_duration'] = result
    
    def _compute_best_value(self):
        df_with_dur = self.df.copy()
        df_with_dur['duration_minutes'] = df_with_dur['duration'].apply(self._parse_duration_minutes)
        valid = df_with_dur[df_with_dur['duration_minutes'] < float('inf')]
        
        if valid.empty:
            return
        
        min_duration = valid['duration_minutes'].min()
        threshold = min_duration * 1.2
        
        short_flights = valid[valid['duration_minutes'] <= threshold]
        
        if not short_flights.empty:
            best = short_flights.loc[short_flights['price'].idxmin()]
            result = best.to_dict()
            result['duration_minutes'] = int(result['duration_minutes'])
            self.metrics['best_value'] = result
    
    def _compute_cheapest_per_airline(self):
        result = {}
        for airline in self.df['airline'].unique():
            airline_df = self.df[self.df['airline'] == airline]
            cheapest = airline_df.loc[airline_df['price'].idxmin()]
            result[airline] = {
                'price': int(cheapest['price']),
                'departure': cheapest['departure'],
                'arrival': cheapest['arrival'],
                'source': cheapest['source']
            }
        self.metrics['cheapest_per_airline'] = result
    
    def _compute_cheapest_per_source(self):
        result = {}
        for source in self.df['source'].unique():
            source_df = self.df[self.df['source'] == source]
            cheapest = source_df.loc[source_df['price'].idxmin()]
            result[source] = {
                'price': int(cheapest['price']),
                'airline': cheapest['airline'],
                'departure': cheapest['departure'],
                'arrival': cheapest['arrival']
            }
        self.metrics['cheapest_per_source'] = result
    
    def _compute_price_stats(self):
        self.metrics['price_stats'] = {
            'min': int(self.df['price'].min()),
            'max': int(self.df['price'].max()),
            'mean': round(self.df['price'].mean(), 2),
            'median': int(self.df['price'].median()),
            'std': round(self.df['price'].std(), 2)
        }
    
    def _compute_stop_analysis(self):
        stop_counts = {}
        stop_prices = {}
        
        for stop_type in self.df['stops'].unique():
            stop_df = self.df[self.df['stops'] == stop_type]
            key = 'non_stop' if 'non' in str(stop_type).lower() else str(stop_type)[:20]
            stop_counts[key] = len(stop_df)
            stop_prices[key] = int(stop_df['price'].min())
        
        self.metrics['stop_analysis'] = {
            'counts': stop_counts,
            'min_prices': stop_prices
        }


class DataAnalyser:
    def __init__(self):
        self.output_dir = Path(__file__).parent / "Results"
        self.output_dir.mkdir(exist_ok=True)
        self.master_df = None
        self.metrics = None
        self.timestamp = None
    
    def analyse(self, scraped_data: dict[str, Any]) -> tuple[pd.DataFrame, dict]:
        logger.info("=" * 80)
        logger.info("DataAnalyser: Processing and exporting results")
        logger.info("=" * 80)
        
        if not scraped_data:
            logger.warning("No data to analyze")
            return None, {}
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_flights = []
        
        for scraper_name, data in scraped_data.items():
            if data is not None and isinstance(data, pd.DataFrame) and len(data) > 0:
                logger.info(f"{scraper_name}: {len(data)} flights")
                
                csv_filename = f"{scraper_name.lower()}_{self.timestamp}.csv"
                csv_path = self.output_dir / csv_filename
                data.to_csv(csv_path, index=False)
                logger.info(f"Saved {scraper_name} data to: {csv_path}")
                
                combined_flights.append(data)
            else:
                logger.info(f"{scraper_name}: No data")
        
        if not combined_flights:
            logger.warning("No valid flight data to combine")
            return None, {}
        
        self.master_df = self._create_master_dataframe(combined_flights)
        self._save_master_csv()
        
        self.metrics = self._compute_metrics()
        self._save_metrics()
        
        self._log_summary()
        
        return self.master_df, self.metrics
    
    def _create_master_dataframe(self, dataframes: list[pd.DataFrame]) -> pd.DataFrame:
        combined = pd.concat(dataframes, ignore_index=True)
        
        schema = ['source', 'airline', 'flight_code', 'departure', 'arrival', 'duration', 'stops', 'price', 'timestamp']
        for col in schema:
            if col not in combined.columns:
                combined[col] = ''
        combined = combined[schema]
        
        combined = combined.drop_duplicates(
            subset=['airline', 'departure', 'arrival', 'price'],
            keep='first'
        )
        
        combined = combined.sort_values(['price', 'departure'], ascending=[True, True])
        combined = combined.reset_index(drop=True)
        
        return combined
    
    def _save_master_csv(self):
        master_path = self.output_dir / f"master_flights_{self.timestamp}.csv"
        self.master_df.to_csv(master_path, index=False)
        logger.info(f"Saved master CSV: {master_path}")
        
        combined_path = self.output_dir / f"all_flights_{self.timestamp}.csv"
        self.master_df.to_csv(combined_path, index=False)
    
    def _compute_metrics(self) -> dict:
        calculator = FlightMetrics(self.master_df)
        metrics = calculator.compute_all()
        
        metrics['summary'] = {
            'total_flights': len(self.master_df),
            'unique_airlines': self.master_df['airline'].nunique(),
            'sources_count': self.master_df['source'].nunique(),
            'timestamp': self.timestamp
        }
        
        return metrics
    
    def _save_metrics(self):
        metrics_path = self.output_dir / f"metrics_{self.timestamp}.json"
        
        serializable_metrics = self._make_serializable(self.metrics)
        
        with open(metrics_path, 'w') as f:
            json.dump(serializable_metrics, f, indent=2, default=str)
        
        logger.info(f"Saved metrics: {metrics_path}")
    
    def _make_serializable(self, obj):
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(v) for v in obj]
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return str(obj)
        elif hasattr(obj, 'item'):
            return obj.item()
        return obj
    
    def _log_summary(self):
        logger.info("=" * 80)
        logger.info(f"MASTER RESULTS: {len(self.master_df)} unique flights")
        logger.info("=" * 80)
        
        if 'cheapest_overall' in self.metrics:
            c = self.metrics['cheapest_overall']
            logger.info(f"Cheapest: ₹{c['price']:,} | {c['airline']} | {c['departure']} → {c['arrival']}")
        
        if 'shortest_duration' in self.metrics:
            s = self.metrics['shortest_duration']
            logger.info(f"Shortest: {s['duration']} | {s['airline']} | ₹{s['price']:,}")
        
        if 'best_value' in self.metrics:
            b = self.metrics['best_value']
            logger.info(f"Best Value: ₹{b['price']:,} | {b['duration']} | {b['airline']}")
        
        logger.info("Top 5 cheapest flights:")
        for _, flight in self.master_df.head(5).iterrows():
            logger.info(f"  {flight['source']:12} | {flight['airline']:18} | ₹{flight['price']:,} | {flight['departure']} → {flight['arrival']}")
    
    def get_master_dataframe(self) -> pd.DataFrame:
        return self.master_df
    
    def get_metrics(self) -> dict:
        return self.metrics

    @staticmethod
    def load_latest_results(results_dir: Path = None) -> tuple[pd.DataFrame, dict]:
        if results_dir is None:
            results_dir = Path(__file__).parent / "Results"
        
        if not results_dir.exists():
            return None, {}
        
        master_files = sorted(results_dir.glob("master_flights_*.csv"), reverse=True)
        metrics_files = sorted(results_dir.glob("metrics_*.json"), reverse=True)
        
        df = None
        metrics = {}
        
        if master_files:
            df = pd.read_csv(master_files[0])
        
        if metrics_files:
            with open(metrics_files[0], 'r') as f:
                metrics = json.load(f)
        
        return df, metrics
