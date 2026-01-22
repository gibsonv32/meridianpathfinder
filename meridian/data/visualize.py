"""Visualization Module for MERIDIAN - EDA and Model Insights"""

import json
import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10


@dataclass
class VisualizationReport:
    """Container for visualization outputs"""
    
    dataset_name: str
    plots: Dict[str, str] = field(default_factory=dict)  # name -> base64 encoded image
    insights: Dict[str, str] = field(default_factory=dict)  # name -> text insight
    statistics: Dict[str, Any] = field(default_factory=dict)
    html_report: Optional[str] = None
    
    def save_plots(self, output_dir: Path):
        """Save all plots to directory"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for name, encoded in self.plots.items():
            # Decode base64 and save
            img_data = base64.b64decode(encoded)
            file_path = output_dir / f"{name}.png"
            with open(file_path, 'wb') as f:
                f.write(img_data)
        
        # Save insights
        insights_path = output_dir / "insights.json"
        with open(insights_path, 'w') as f:
            json.dump(self.insights, f, indent=2)
    
    def generate_html_report(self) -> str:
        """Generate HTML report with all visualizations"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MERIDIAN EDA Report - {self.dataset_name}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                h1 {{
                    color: #333;
                    border-bottom: 3px solid #007bff;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #555;
                    margin-top: 30px;
                }}
                .plot-container {{
                    background: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .plot-title {{
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 10px;
                }}
                .insight {{
                    background: #f0f7ff;
                    padding: 10px;
                    border-left: 4px solid #007bff;
                    margin: 10px 0;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
                .stats-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .stats-table th, .stats-table td {{
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                .stats-table th {{
                    background-color: #007bff;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <h1>📊 MERIDIAN EDA Report: {self.dataset_name}</h1>
        """
        
        # Add each plot with its insight
        for plot_name, encoded_img in self.plots.items():
            insight = self.insights.get(plot_name, "")
            clean_name = plot_name.replace('_', ' ').title()
            
            html += f"""
            <div class="plot-container">
                <div class="plot-title">{clean_name}</div>
                <img src="data:image/png;base64,{encoded_img}" alt="{clean_name}">
                {f'<div class="insight">{insight}</div>' if insight else ''}
            </div>
            """
        
        # Add statistics if available
        if self.statistics:
            html += """
            <h2>📈 Statistical Summary</h2>
            <table class="stats-table">
                <tr><th>Metric</th><th>Value</th></tr>
            """
            for key, value in self.statistics.items():
                html += f"<tr><td>{key}</td><td>{value}</td></tr>"
            html += "</table>"
        
        html += """
        </body>
        </html>
        """
        
        self.html_report = html
        return html


class DataVisualizer:
    """Automated EDA and visualization generator"""
    
    def __init__(self, style: str = "seaborn", figsize: Tuple[int, int] = (10, 6)):
        """
        Initialize visualizer
        
        Args:
            style: Matplotlib style to use
            figsize: Default figure size
        """
        self.style = style
        self.figsize = figsize
        if style != "seaborn":
            plt.style.use(style)
    
    def create_eda_report(self, 
                          df: pd.DataFrame, 
                          target_col: Optional[str] = None,
                          dataset_name: str = "dataset") -> VisualizationReport:
        """
        Create comprehensive EDA report with visualizations
        
        Args:
            df: DataFrame to analyze
            target_col: Target column for supervised learning
            dataset_name: Name of the dataset
            
        Returns:
            VisualizationReport with all plots and insights
        """
        report = VisualizationReport(dataset_name=dataset_name)
        
        # Identify column types
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
        
        if target_col and target_col in numeric_cols:
            numeric_cols.remove(target_col)
        elif target_col and target_col in categorical_cols:
            categorical_cols.remove(target_col)
        
        # 1. Distribution plots for numeric features
        if numeric_cols:
            self._create_distribution_plots(df, numeric_cols, report)
        
        # 2. Correlation heatmap
        if len(numeric_cols) > 1:
            self._create_correlation_heatmap(df, numeric_cols, target_col, report)
        
        # 3. Missing values visualization
        self._create_missing_values_plot(df, report)
        
        # 4. Target distribution (if exists)
        if target_col:
            self._create_target_analysis(df, target_col, numeric_cols, report)
        
        # 5. Feature relationships
        if numeric_cols and len(numeric_cols) >= 2:
            self._create_pairplot(df, numeric_cols[:5], target_col, report)  # Limit to 5 features
        
        # 6. Categorical analysis
        if categorical_cols:
            self._create_categorical_analysis(df, categorical_cols[:5], target_col, report)
        
        # 7. Outlier detection visualization
        if numeric_cols:
            self._create_outlier_plots(df, numeric_cols[:6], report)
        
        # Generate statistics
        self._generate_statistics(df, report)
        
        return report
    
    def _create_distribution_plots(self, df: pd.DataFrame, numeric_cols: List[str], report: VisualizationReport):
        """Create distribution plots for numeric features"""
        n_cols = min(len(numeric_cols), 9)  # Limit to 9 subplots
        n_rows = (n_cols + 2) // 3
        n_cols_plot = min(3, n_cols)
        
        fig, axes = plt.subplots(n_rows, n_cols_plot, figsize=(5*n_cols_plot, 4*n_rows))
        axes = axes.flatten() if n_rows * n_cols_plot > 1 else [axes]
        
        for i, col in enumerate(numeric_cols[:9]):
            ax = axes[i]
            
            # Plot histogram with KDE
            df[col].hist(ax=ax, bins=30, alpha=0.7, color='steelblue', edgecolor='black')
            
            # Add KDE
            if df[col].nunique() > 1:
                df[col].plot(kind='density', ax=ax, secondary_y=True, color='red', alpha=0.5)
            
            ax.set_title(f'Distribution of {col}')
            ax.set_xlabel(col)
            ax.set_ylabel('Frequency')
            
            # Add statistics
            mean = df[col].mean()
            median = df[col].median()
            ax.axvline(mean, color='green', linestyle='--', alpha=0.7, label=f'Mean: {mean:.2f}')
            ax.axvline(median, color='orange', linestyle='--', alpha=0.7, label=f'Median: {median:.2f}')
            ax.legend(loc='best', fontsize='small')
        
        # Hide unused subplots
        for i in range(len(numeric_cols[:9]), len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        report.plots['distributions'] = self._fig_to_base64(fig)
        plt.close()
        
        # Generate insight
        skewed_features = []
        for col in numeric_cols:
            skewness = df[col].skew()
            if abs(skewness) > 1:
                skewed_features.append(f"{col} (skew={skewness:.2f})")
        
        if skewed_features:
            report.insights['distributions'] = f"Skewed features detected: {', '.join(skewed_features[:5])}. Consider applying log or box-cox transformation."
        else:
            report.insights['distributions'] = "Features show relatively normal distributions."
    
    def _create_correlation_heatmap(self, df: pd.DataFrame, numeric_cols: List[str], target_col: Optional[str], report: VisualizationReport):
        """Create correlation heatmap"""
        cols_to_use = numeric_cols[:20]  # Limit for readability
        if target_col and target_col in df.columns:
            cols_to_use = cols_to_use + [target_col]
        
        corr_matrix = df[cols_to_use].corr()
        
        # Create figure
        fig, ax = plt.subplots(figsize=(min(12, len(cols_to_use)), min(10, len(cols_to_use)*0.8)))
        
        # Create heatmap
        sns.heatmap(corr_matrix, annot=len(cols_to_use) <= 10, cmap='coolwarm', 
                   center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8},
                   fmt='.2f' if len(cols_to_use) <= 10 else '')
        
        plt.title('Feature Correlation Matrix')
        plt.tight_layout()
        
        report.plots['correlation_heatmap'] = self._fig_to_base64(fig)
        plt.close()
        
        # Find highly correlated pairs
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if abs(corr_matrix.iloc[i, j]) > 0.8:
                    high_corr_pairs.append(
                        f"{corr_matrix.columns[i]} - {corr_matrix.columns[j]}: {corr_matrix.iloc[i, j]:.2f}"
                    )
        
        if high_corr_pairs:
            report.insights['correlation_heatmap'] = f"High correlations found: {'; '.join(high_corr_pairs[:3])}. Consider feature selection."
        else:
            report.insights['correlation_heatmap'] = "No highly correlated features detected (threshold: 0.8)."
    
    def _create_missing_values_plot(self, df: pd.DataFrame, report: VisualizationReport):
        """Visualize missing values"""
        missing_counts = df.isnull().sum()
        missing_pct = (missing_counts / len(df)) * 100
        
        if missing_counts.sum() == 0:
            report.insights['missing_values'] = "No missing values detected in the dataset."
            return
        
        # Filter to columns with missing values
        missing_cols = missing_counts[missing_counts > 0].sort_values(ascending=False)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Bar plot of missing counts
        missing_cols.head(20).plot(kind='barh', ax=ax1, color='coral')
        ax1.set_xlabel('Missing Count')
        ax1.set_title('Missing Values by Column (Count)')
        
        # Bar plot of missing percentages
        missing_pct[missing_cols.index].head(20).plot(kind='barh', ax=ax2, color='skyblue')
        ax2.set_xlabel('Missing Percentage (%)')
        ax2.set_title('Missing Values by Column (Percentage)')
        
        plt.tight_layout()
        report.plots['missing_values'] = self._fig_to_base64(fig)
        plt.close()
        
        # Insight
        high_missing = [f"{col} ({pct:.1f}%)" for col, pct in missing_pct[missing_pct > 20].items()]
        if high_missing:
            report.insights['missing_values'] = f"Columns with >20% missing: {', '.join(high_missing[:5])}. Consider dropping or advanced imputation."
        else:
            report.insights['missing_values'] = f"Total {missing_counts.sum()} missing values across {len(missing_cols)} columns. All manageable with standard imputation."
    
    def _create_target_analysis(self, df: pd.DataFrame, target_col: str, feature_cols: List[str], report: VisualizationReport):
        """Analyze target variable"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. Target distribution
        ax1 = axes[0, 0]
        if pd.api.types.is_numeric_dtype(df[target_col]):
            df[target_col].hist(ax=ax1, bins=30, color='green', alpha=0.7, edgecolor='black')
            ax1.set_title(f'Target Distribution: {target_col}')
            
            # Check if regression or classification
            n_unique = df[target_col].nunique()
            if n_unique <= 20:
                # Classification
                value_counts = df[target_col].value_counts()
                report.insights['target'] = f"Classification target with {n_unique} classes. "
                if value_counts.min() / value_counts.max() < 0.1:
                    report.insights['target'] += "Warning: Class imbalance detected!"
            else:
                # Regression
                skewness = df[target_col].skew()
                report.insights['target'] = f"Regression target with skewness={skewness:.2f}. "
                if abs(skewness) > 1:
                    report.insights['target'] += "Consider target transformation."
        else:
            df[target_col].value_counts().plot(kind='bar', ax=ax1, color='green', alpha=0.7)
            ax1.set_title(f'Target Distribution: {target_col}')
            ax1.set_xlabel(target_col)
            ax1.set_ylabel('Count')
        
        # 2. Target vs top features (if numeric)
        if feature_cols and pd.api.types.is_numeric_dtype(df[target_col]):
            # Calculate correlations with target
            correlations = df[feature_cols].corrwith(df[target_col]).abs().sort_values(ascending=False)
            
            # Plot top correlations
            ax2 = axes[0, 1]
            correlations.head(10).plot(kind='barh', ax=ax2, color='steelblue')
            ax2.set_title('Top 10 Feature Correlations with Target')
            ax2.set_xlabel('Absolute Correlation')
            
            # Scatter plots for top 2 features
            if len(correlations) >= 2:
                top_features = correlations.head(2).index
                
                ax3 = axes[1, 0]
                ax3.scatter(df[top_features[0]], df[target_col], alpha=0.5, s=10)
                ax3.set_xlabel(top_features[0])
                ax3.set_ylabel(target_col)
                ax3.set_title(f'{target_col} vs {top_features[0]}')
                
                ax4 = axes[1, 1]
                ax4.scatter(df[top_features[1]], df[target_col], alpha=0.5, s=10)
                ax4.set_xlabel(top_features[1])
                ax4.set_ylabel(target_col)
                ax4.set_title(f'{target_col} vs {top_features[1]}')
        else:
            axes[0, 1].set_visible(False)
            axes[1, 0].set_visible(False)
            axes[1, 1].set_visible(False)
        
        plt.tight_layout()
        report.plots['target_analysis'] = self._fig_to_base64(fig)
        plt.close()
    
    def _create_pairplot(self, df: pd.DataFrame, numeric_cols: List[str], target_col: Optional[str], report: VisualizationReport):
        """Create pairplot for feature relationships"""
        cols_to_plot = numeric_cols[:4]  # Limit to 4 for readability
        if target_col and pd.api.types.is_numeric_dtype(df[target_col]):
            cols_to_plot.append(target_col)
        
        if len(cols_to_plot) < 2:
            return
        
        # Create pairplot
        fig = plt.figure(figsize=(12, 10))
        
        # Use seaborn pairplot
        if target_col and target_col in cols_to_plot and df[target_col].nunique() <= 10:
            # Use hue for classification
            g = sns.pairplot(df[cols_to_plot], hue=target_col, diag_kind='kde', 
                           plot_kws={'alpha': 0.6, 's': 20})
        else:
            g = sns.pairplot(df[cols_to_plot], diag_kind='kde', 
                           plot_kws={'alpha': 0.6, 's': 20})
        
        plt.suptitle('Feature Relationships Pairplot', y=1.02)
        
        report.plots['pairplot'] = self._fig_to_base64(g.fig)
        plt.close()
        
        report.insights['pairplot'] = f"Pairwise relationships shown for top {len(cols_to_plot)} features. Look for linear relationships and clusters."
    
    def _create_categorical_analysis(self, df: pd.DataFrame, categorical_cols: List[str], target_col: Optional[str], report: VisualizationReport):
        """Analyze categorical features"""
        n_cats = min(len(categorical_cols), 6)
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        for i, col in enumerate(categorical_cols[:6]):
            ax = axes[i]
            
            # Get value counts
            value_counts = df[col].value_counts().head(10)  # Top 10 categories
            
            if target_col and pd.api.types.is_numeric_dtype(df[target_col]):
                # Show mean target by category
                mean_target = df.groupby(col)[target_col].mean().loc[value_counts.index]
                mean_target.plot(kind='bar', ax=ax, color='teal', alpha=0.7)
                ax.set_title(f'Mean {target_col} by {col}')
                ax.set_ylabel(f'Mean {target_col}')
            else:
                # Just show counts
                value_counts.plot(kind='bar', ax=ax, color='purple', alpha=0.7)
                ax.set_title(f'Distribution of {col}')
                ax.set_ylabel('Count')
            
            ax.set_xlabel(col)
            ax.tick_params(axis='x', rotation=45)
        
        # Hide unused
        for i in range(len(categorical_cols[:6]), len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        report.plots['categorical_analysis'] = self._fig_to_base64(fig)
        plt.close()
        
        # Insight
        high_cardinality = [f"{col} ({df[col].nunique()} unique)" 
                          for col in categorical_cols 
                          if df[col].nunique() > 50]
        if high_cardinality:
            report.insights['categorical_analysis'] = f"High cardinality features: {', '.join(high_cardinality[:3])}. Consider encoding strategies."
        else:
            report.insights['categorical_analysis'] = "Categorical features have manageable cardinality for one-hot encoding."
    
    def _create_outlier_plots(self, df: pd.DataFrame, numeric_cols: List[str], report: VisualizationReport):
        """Create outlier detection visualizations"""
        n_cols = min(len(numeric_cols), 6)
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        outlier_summary = {}
        
        for i, col in enumerate(numeric_cols[:6]):
            ax = axes[i]
            
            # Create box plot
            df[col].plot(kind='box', ax=ax, vert=True)
            ax.set_title(f'Outliers in {col}')
            ax.set_ylabel(col)
            
            # Calculate outliers using IQR
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            outlier_pct = (len(outliers) / len(df)) * 100
            
            outlier_summary[col] = outlier_pct
            
            # Add text annotation
            ax.text(0.5, 0.95, f'Outliers: {outlier_pct:.1f}%',
                   transform=ax.transAxes, ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Hide unused
        for i in range(len(numeric_cols[:6]), len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        report.plots['outlier_analysis'] = self._fig_to_base64(fig)
        plt.close()
        
        # Insight
        high_outlier_cols = [f"{col} ({pct:.1f}%)" 
                           for col, pct in outlier_summary.items() 
                           if pct > 5]
        if high_outlier_cols:
            report.insights['outlier_analysis'] = f"Features with >5% outliers: {', '.join(high_outlier_cols)}. Consider robust scaling or outlier treatment."
        else:
            report.insights['outlier_analysis'] = "Outliers are within acceptable range (<5% for all features)."
    
    def _generate_statistics(self, df: pd.DataFrame, report: VisualizationReport):
        """Generate statistical summary"""
        report.statistics = {
            "Total Rows": len(df),
            "Total Columns": len(df.columns),
            "Numeric Features": len(df.select_dtypes(include=[np.number]).columns),
            "Categorical Features": len(df.select_dtypes(exclude=[np.number]).columns),
            "Memory Usage (MB)": f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f}",
            "Missing Values": df.isnull().sum().sum(),
            "Duplicate Rows": df.duplicated().sum()
        }
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 encoded string"""
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        return encoded
    
    def create_model_performance_plots(self, 
                                      y_true: np.ndarray, 
                                      y_pred: np.ndarray,
                                      model_name: str = "Model") -> VisualizationReport:
        """
        Create model performance visualizations
        
        Args:
            y_true: True labels
            y_pred: Predicted labels/probabilities
            model_name: Name of the model
            
        Returns:
            VisualizationReport with performance plots
        """
        report = VisualizationReport(dataset_name=f"{model_name} Performance")
        
        # Determine if classification or regression
        if len(np.unique(y_true)) <= 20:  # Classification
            self._create_classification_plots(y_true, y_pred, report)
        else:  # Regression
            self._create_regression_plots(y_true, y_pred, report)
        
        return report
    
    def _create_classification_plots(self, y_true: np.ndarray, y_pred: np.ndarray, report: VisualizationReport):
        """Create classification performance plots"""
        from sklearn.metrics import confusion_matrix, classification_report
        
        # Confusion Matrix
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        cm = confusion_matrix(y_true, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax1)
        ax1.set_title('Confusion Matrix')
        ax1.set_xlabel('Predicted')
        ax1.set_ylabel('Actual')
        
        # Classification metrics by class
        from sklearn.metrics import precision_recall_fscore_support
        precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred)
        
        x = np.arange(len(precision))
        width = 0.25
        
        ax2.bar(x - width, precision, width, label='Precision', alpha=0.8)
        ax2.bar(x, recall, width, label='Recall', alpha=0.8)
        ax2.bar(x + width, f1, width, label='F1-Score', alpha=0.8)
        
        ax2.set_xlabel('Class')
        ax2.set_ylabel('Score')
        ax2.set_title('Performance Metrics by Class')
        ax2.set_xticks(x)
        ax2.set_xticklabels([str(i) for i in range(len(precision))])
        ax2.legend()
        ax2.set_ylim([0, 1.1])
        
        plt.tight_layout()
        report.plots['classification_performance'] = self._fig_to_base64(fig)
        plt.close()
        
        # Generate insight
        avg_f1 = np.mean(f1)
        report.insights['classification_performance'] = f"Average F1-Score: {avg_f1:.3f}. "
        if avg_f1 < 0.5:
            report.insights['classification_performance'] += "Model performance needs improvement."
        elif avg_f1 < 0.7:
            report.insights['classification_performance'] += "Moderate performance. Consider feature engineering or model tuning."
        else:
            report.insights['classification_performance'] += "Good performance achieved."
    
    def _create_regression_plots(self, y_true: np.ndarray, y_pred: np.ndarray, report: VisualizationReport):
        """Create regression performance plots"""
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        
        # 1. Predicted vs Actual
        ax1 = axes[0, 0]
        ax1.scatter(y_true, y_pred, alpha=0.5, s=10)
        ax1.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
        ax1.set_xlabel('Actual')
        ax1.set_ylabel('Predicted')
        ax1.set_title('Predicted vs Actual')
        
        # Add R2 score
        r2 = r2_score(y_true, y_pred)
        ax1.text(0.05, 0.95, f'R² = {r2:.3f}', transform=ax1.transAxes, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 2. Residuals
        ax2 = axes[0, 1]
        residuals = y_true - y_pred
        ax2.scatter(y_pred, residuals, alpha=0.5, s=10)
        ax2.axhline(y=0, color='r', linestyle='--')
        ax2.set_xlabel('Predicted')
        ax2.set_ylabel('Residuals')
        ax2.set_title('Residual Plot')
        
        # 3. Residual Distribution
        ax3 = axes[1, 0]
        ax3.hist(residuals, bins=30, alpha=0.7, color='blue', edgecolor='black')
        ax3.set_xlabel('Residuals')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Residual Distribution')
        
        # 4. Q-Q Plot
        ax4 = axes[1, 1]
        stats.probplot(residuals, dist="norm", plot=ax4)
        ax4.set_title('Q-Q Plot')
        
        plt.tight_layout()
        report.plots['regression_performance'] = self._fig_to_base64(fig)
        plt.close()
        
        # Metrics
        mse = mean_squared_error(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        
        report.insights['regression_performance'] = f"R² Score: {r2:.3f}, RMSE: {np.sqrt(mse):.3f}, MAE: {mae:.3f}. "
        if r2 < 0.3:
            report.insights['regression_performance'] += "Poor model fit. Consider different algorithms or features."
        elif r2 < 0.7:
            report.insights['regression_performance'] += "Moderate fit. Check residuals for patterns."
        else:
            report.insights['regression_performance'] += "Good model fit achieved."