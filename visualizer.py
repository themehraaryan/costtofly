from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from loggerconfig import setup_logger
from scrapers.utils import parse_duration_minutes as _shared_parse_duration

logger = setup_logger()

COLORS = {
    'primary': '#2563EB',
    'secondary': '#7C3AED',
    'accent': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'dark': '#1F2937',
    'light': '#F3F4F6',
    'gradient': ['#2563EB', '#7C3AED', '#EC4899', '#F59E0B', '#10B981']
}


class FlightVisualizer:
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path(__file__).parent / "Results" / "charts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._setup_style()
    
    def _setup_style(self):
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': ['Segoe UI', 'Arial', 'Helvetica'],
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.titleweight': 'bold',
            'axes.labelsize': 11,
            'axes.labelweight': 'medium',
            'axes.spines.top': False,
            'axes.spines.right': False,
            'axes.edgecolor': '#E5E7EB',
            'axes.facecolor': 'white',
            'figure.facecolor': 'white',
            'figure.figsize': (12, 7),
            'figure.dpi': 120,
            'grid.alpha': 0.3,
            'grid.linestyle': '--',
            'legend.frameon': False,
            'legend.fontsize': 10
        })
    
    def generate_all(self, df: pd.DataFrame, metrics: dict = None) -> list[Path]:
        if df is None or df.empty:
            logger.warning("No data for visualization")
            return []
        
        generated = []
        generated.append(self.price_by_departure_time(df))
        generated.append(self.price_by_airline(df))
        generated.append(self.price_distribution(df))
        generated.append(self.duration_vs_price(df))
        generated.append(self.cheapest_flights_comparison(df))
        generated.append(self.price_by_source(df))
        
        generated = [p for p in generated if p is not None]
        logger.info(f"Generated {len(generated)} visualizations")
        return generated
    
    def price_by_departure_time(self, df: pd.DataFrame) -> Path:
        try:
            fig, ax = plt.subplots()
            
            df_plot = df.copy()
            df_plot['dep_hour'] = df_plot['departure'].apply(self._parse_hour)
            df_plot = df_plot[df_plot['dep_hour'] >= 0].sort_values('dep_hour')
            
            if df_plot.empty:
                plt.close(fig)
                return None
            
            prices_norm = (df_plot['price'] - df_plot['price'].min()) / (df_plot['price'].max() - df_plot['price'].min())
            colors = plt.cm.RdYlGn_r(prices_norm)
            
            scatter = ax.scatter(
                df_plot['dep_hour'], 
                df_plot['price'], 
                c=colors, 
                s=80, 
                alpha=0.7,
                edgecolors='white',
                linewidths=0.5
            )
            
            min_idx = df_plot['price'].idxmin()
            min_row = df_plot.loc[min_idx]
            ax.scatter([min_row['dep_hour']], [min_row['price']], 
                      c=COLORS['accent'], s=200, marker='*', zorder=5,
                      label=f"Best: ₹{int(min_row['price']):,}")
            
            ax.set_xlabel('Departure Hour', fontweight='medium')
            ax.set_ylabel('Price (₹)', fontweight='medium')
            ax.set_title('Flight Prices by Departure Time', pad=15)
            ax.set_xticks(range(0, 24, 3))
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
            
            path = self.output_dir / f"price_departure_{self.timestamp}.png"
            fig.savefig(path, bbox_inches='tight', facecolor='white', dpi=120)
            plt.close(fig)
            return path
        except Exception as e:
            logger.error(f"Error generating price_departure chart: {e}")
            return None
    
    def price_by_airline(self, df: pd.DataFrame) -> Path:
        try:
            fig, ax = plt.subplots()
            
            airline_stats = df.groupby('airline')['price'].agg(['min', 'mean', 'count']).reset_index()
            airline_stats = airline_stats.sort_values('min').head(8)
            
            x = range(len(airline_stats))
            width = 0.35
            
            bars_min = ax.bar([i - width/2 for i in x], airline_stats['min'], width, 
                             label='Lowest Price', color=COLORS['primary'], alpha=0.9)
            bars_avg = ax.bar([i + width/2 for i in x], airline_stats['mean'], width, 
                             label='Average Price', color=COLORS['secondary'], alpha=0.7)
            
            for bar, val in zip(bars_min, airline_stats['min']):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100, 
                       f'₹{int(val):,}', ha='center', va='bottom', fontsize=8, fontweight='bold')
            
            ax.set_xlabel('Airline', fontweight='medium')
            ax.set_ylabel('Price (₹)', fontweight='medium')
            ax.set_title('Price Comparison by Airline', pad=15)
            ax.set_xticks(x)
            ax.set_xticklabels([a[:12] for a in airline_stats['airline']], rotation=30, ha='right')
            ax.legend(loc='upper right')
            ax.grid(True, axis='y', alpha=0.3)
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
            
            path = self.output_dir / f"price_airline_{self.timestamp}.png"
            fig.savefig(path, bbox_inches='tight', facecolor='white', dpi=120)
            plt.close(fig)
            return path
        except Exception as e:
            logger.error(f"Error generating price_airline chart: {e}")
            return None
    
    def price_distribution(self, df: pd.DataFrame) -> Path:
        try:
            fig, ax = plt.subplots()
            
            prices = df['price'].dropna()
            
            n, bins, patches = ax.hist(prices, bins=15, edgecolor='white', linewidth=1.5, alpha=0.8)
            
            bin_centers = 0.5 * (bins[:-1] + bins[1:])
            col = (bin_centers - bin_centers.min()) / (bin_centers.max() - bin_centers.min())
            cm = plt.cm.RdYlGn_r
            for c, p in zip(col, patches):
                plt.setp(p, 'facecolor', cm(c))
            
            ax.axvline(prices.min(), color=COLORS['accent'], linestyle='--', linewidth=2.5, 
                      label=f'Minimum: ₹{int(prices.min()):,}')
            ax.axvline(prices.median(), color=COLORS['warning'], linestyle='--', linewidth=2.5, 
                      label=f'Median: ₹{int(prices.median()):,}')
            
            ax.set_xlabel('Price (₹)', fontweight='medium')
            ax.set_ylabel('Number of Flights', fontweight='medium')
            ax.set_title('Price Distribution', pad=15)
            ax.legend(loc='upper right', framealpha=0.9)
            ax.grid(True, axis='y', alpha=0.3)
            
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
            
            path = self.output_dir / f"price_distribution_{self.timestamp}.png"
            fig.savefig(path, bbox_inches='tight', facecolor='white', dpi=120)
            plt.close(fig)
            return path
        except Exception as e:
            logger.error(f"Error generating price_distribution chart: {e}")
            return None
    
    def duration_vs_price(self, df: pd.DataFrame) -> Path:
        try:
            fig, ax = plt.subplots()
            
            df_plot = df.copy()
            df_plot['duration_min'] = df_plot['duration'].apply(self._parse_duration_minutes)
            df_plot = df_plot[df_plot['duration_min'] < 1000]
            
            if df_plot.empty:
                plt.close(fig)
                return None
            
            scatter = ax.scatter(
                df_plot['duration_min'], 
                df_plot['price'], 
                c=df_plot['price'],
                cmap='RdYlGn_r',
                s=70, 
                alpha=0.7,
                edgecolors='white',
                linewidths=0.5
            )
            
            best_idx = df_plot.loc[(df_plot['price'] < df_plot['price'].quantile(0.25)) & 
                                   (df_plot['duration_min'] < df_plot['duration_min'].quantile(0.5))].index
            if len(best_idx) > 0:
                best_row = df_plot.loc[best_idx[0]]
                ax.scatter([best_row['duration_min']], [best_row['price']], 
                          c=COLORS['accent'], s=200, marker='*', zorder=5,
                          label='Best Value')
            
            ax.set_xlabel('Duration (minutes)', fontweight='medium')
            ax.set_ylabel('Price (₹)', fontweight='medium')
            ax.set_title('Duration vs Price Analysis', pad=15)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
            
            cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
            cbar.set_label('Price', fontsize=10)
            
            path = self.output_dir / f"duration_price_{self.timestamp}.png"
            fig.savefig(path, bbox_inches='tight', facecolor='white', dpi=120)
            plt.close(fig)
            return path
        except Exception as e:
            logger.error(f"Error generating duration_price chart: {e}")
            return None
    
    def cheapest_flights_comparison(self, df: pd.DataFrame) -> Path:
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            top_10 = df.nsmallest(10, 'price')
            
            labels = [f"{row['airline'][:15]}\n{row['departure']} → {row['arrival']}" for _, row in top_10.iterrows()]
            prices = top_10['price'].tolist()
            
            colors = [COLORS['accent'] if i == 0 else plt.cm.Blues(0.4 + i * 0.06) for i in range(len(prices))]
            
            bars = ax.barh(range(len(prices)), prices, color=colors, 
                          edgecolor='white', linewidth=1.5, height=0.7)
            
            for i, (bar, price) in enumerate(zip(bars, prices)):
                ax.text(bar.get_width() + 100, bar.get_y() + bar.get_height()/2, 
                       f'₹{price:,}', va='center', fontsize=10, fontweight='bold',
                       color=COLORS['dark'])
            
            ax.set_yticks(range(len(labels)))
            ax.set_yticklabels(labels, fontsize=10)
            ax.set_xlabel('Price (₹)', fontweight='medium')
            ax.set_title('🏆 Top 10 Cheapest Flights', pad=15, fontsize=16)
            ax.invert_yaxis()
            ax.grid(True, axis='x', alpha=0.3)
            
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
            
            path = self.output_dir / f"cheapest_flights_{self.timestamp}.png"
            fig.savefig(path, bbox_inches='tight', facecolor='white', dpi=120)
            plt.close(fig)
            return path
        except Exception as e:
            logger.error(f"Error generating cheapest_flights chart: {e}")
            return None
    
    def price_by_source(self, df: pd.DataFrame) -> Path:
        try:
            fig, ax = plt.subplots()
            
            source_stats = df.groupby('source')['price'].agg(['min', 'mean', 'count']).reset_index()
            source_stats = source_stats.sort_values('min')
            
            x = range(len(source_stats))
            colors = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], COLORS['warning']][:len(source_stats)]
            
            bars = ax.bar(x, source_stats['min'], color=colors, 
                         edgecolor='white', linewidth=2, width=0.6)
            
            for i, (bar, row) in enumerate(zip(bars, source_stats.itertuples())):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100, 
                       f'₹{int(row.min):,}', ha='center', va='bottom', 
                       fontsize=11, fontweight='bold')
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() / 2, 
                       f'{int(row.count)} flights', ha='center', va='center', 
                       fontsize=9, color='white', fontweight='medium')
            
            ax.set_xlabel('Source', fontweight='medium')
            ax.set_ylabel('Lowest Price (₹)', fontweight='medium')
            ax.set_title('Price Comparison by Source', pad=15)
            ax.set_xticks(x)
            ax.set_xticklabels(source_stats['source'], fontsize=12, fontweight='medium')
            ax.grid(True, axis='y', alpha=0.3)
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))
            
            path = self.output_dir / f"price_source_{self.timestamp}.png"
            fig.savefig(path, bbox_inches='tight', facecolor='white', dpi=120)
            plt.close(fig)
            return path
        except Exception as e:
            logger.error(f"Error generating price_source chart: {e}")
            return None
    
    def _parse_hour(self, time_str: str) -> int:
        if not time_str or pd.isna(time_str):
            return -1
        try:
            time_str = str(time_str).strip()
            if ':' in time_str:
                return int(time_str.split(':')[0])
            return -1
        except:
            return -1
    
    def _parse_duration_minutes(self, duration_str: str) -> int:
        return _shared_parse_duration(duration_str)


def generate_visualizations(df: pd.DataFrame, metrics: dict = None, output_dir: Path = None) -> list[Path]:
    visualizer = FlightVisualizer(output_dir)
    return visualizer.generate_all(df, metrics)
