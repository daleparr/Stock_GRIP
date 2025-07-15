"""
Data Quality Monitoring and Anomaly Detection for Live Data
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from scipy import stats
import warnings

from .models import Product, get_session
from .live_data_models import (
    LiveSalesData, LiveInventoryUpdate, LiveDemandSignals,
    DataQualityMetrics
)
from config.settings import DATABASE_URL


class DataQualityMonitor:
    """Monitor data quality and detect anomalies in live data streams"""
    
    def __init__(self, database_session: Session):
        self.session = database_session
        self.logger = logging.getLogger(__name__)
        
        # Quality thresholds
        self.thresholds = {
            'completeness': {
                'pass': 0.95,
                'warning': 0.90
            },
            'timeliness': {
                'pass': 24,  # hours
                'warning': 48
            },
            'accuracy': {
                'pass': 0.95,
                'warning': 0.90
            },
            'consistency': {
                'pass': 0.95,
                'warning': 0.90
            },
            'anomaly_score': {
                'pass': 2.0,  # z-score threshold
                'warning': 1.5
            }
        }
    
    def check_data_completeness(self, data_type: str, date: datetime = None) -> Dict[str, Any]:
        """Check data completeness for a given date"""
        if date is None:
            date = datetime.utcnow().date()
        
        start_date = datetime.combine(date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        result = {
            'metric_name': 'completeness',
            'data_source': data_type,
            'timestamp': datetime.utcnow(),
            'status': 'pass',
            'details': {}
        }
        
        try:
            if data_type == 'sales':
                # Check sales data completeness
                total_products = self.session.query(Product).count()
                products_with_sales = self.session.query(
                    func.count(func.distinct(LiveSalesData.product_id))
                ).filter(
                    and_(
                        LiveSalesData.date >= start_date,
                        LiveSalesData.date < end_date
                    )
                ).scalar() or 0
                
                completeness_ratio = products_with_sales / max(total_products, 1)
                
                result['metric_value'] = completeness_ratio
                result['threshold_value'] = self.thresholds['completeness']['pass']
                result['details'] = {
                    'total_products': total_products,
                    'products_with_sales': products_with_sales,
                    'missing_products': total_products - products_with_sales
                }
            
            elif data_type == 'inventory':
                # Check inventory data completeness
                total_products = self.session.query(Product).count()
                products_with_inventory = self.session.query(
                    func.count(func.distinct(LiveInventoryUpdate.product_id))
                ).filter(
                    and_(
                        LiveInventoryUpdate.date >= start_date,
                        LiveInventoryUpdate.date < end_date
                    )
                ).scalar() or 0
                
                completeness_ratio = products_with_inventory / max(total_products, 1)
                
                result['metric_value'] = completeness_ratio
                result['threshold_value'] = self.thresholds['completeness']['pass']
                result['details'] = {
                    'total_products': total_products,
                    'products_with_inventory': products_with_inventory,
                    'missing_products': total_products - products_with_inventory
                }
            
            elif data_type == 'demand':
                # Check demand signals completeness
                total_products = self.session.query(Product).count()
                products_with_demand = self.session.query(
                    func.count(func.distinct(LiveDemandSignals.product_id))
                ).filter(
                    and_(
                        LiveDemandSignals.date >= start_date,
                        LiveDemandSignals.date < end_date
                    )
                ).scalar() or 0
                
                completeness_ratio = products_with_demand / max(total_products, 1)
                
                result['metric_value'] = completeness_ratio
                result['threshold_value'] = self.thresholds['completeness']['pass']
                result['details'] = {
                    'total_products': total_products,
                    'products_with_demand': products_with_demand,
                    'missing_products': total_products - products_with_demand
                }
            
            # Determine status
            if result['metric_value'] >= self.thresholds['completeness']['pass']:
                result['status'] = 'pass'
            elif result['metric_value'] >= self.thresholds['completeness']['warning']:
                result['status'] = 'warning'
            else:
                result['status'] = 'fail'
                
        except Exception as e:
            result['status'] = 'fail'
            result['metric_value'] = 0.0
            result['threshold_value'] = self.thresholds['completeness']['pass']
            result['details'] = {'error': str(e)}
            self.logger.error(f"Error checking completeness for {data_type}: {e}")
        
        return result
    
    def check_data_timeliness(self, data_type: str) -> Dict[str, Any]:
        """Check data timeliness (how recent is the latest data)"""
        result = {
            'metric_name': 'timeliness',
            'data_source': data_type,
            'timestamp': datetime.utcnow(),
            'status': 'pass',
            'details': {}
        }
        
        try:
            current_time = datetime.utcnow()
            
            if data_type == 'sales':
                latest_record = self.session.query(
                    func.max(LiveSalesData.timestamp_created)
                ).scalar()
            elif data_type == 'inventory':
                latest_record = self.session.query(
                    func.max(LiveInventoryUpdate.timestamp_created)
                ).scalar()
            elif data_type == 'demand':
                latest_record = self.session.query(
                    func.max(LiveDemandSignals.timestamp_created)
                ).scalar()
            else:
                latest_record = None
            
            if latest_record:
                hours_since_latest = (current_time - latest_record).total_seconds() / 3600
                result['metric_value'] = hours_since_latest
                result['threshold_value'] = self.thresholds['timeliness']['pass']
                result['details'] = {
                    'latest_record_time': latest_record,
                    'hours_since_latest': hours_since_latest
                }
                
                # Determine status (lower is better for timeliness)
                if hours_since_latest <= self.thresholds['timeliness']['pass']:
                    result['status'] = 'pass'
                elif hours_since_latest <= self.thresholds['timeliness']['warning']:
                    result['status'] = 'warning'
                else:
                    result['status'] = 'fail'
            else:
                result['status'] = 'fail'
                result['metric_value'] = float('inf')
                result['threshold_value'] = self.thresholds['timeliness']['pass']
                result['details'] = {'error': 'No records found'}
                
        except Exception as e:
            result['status'] = 'fail'
            result['metric_value'] = float('inf')
            result['threshold_value'] = self.thresholds['timeliness']['pass']
            result['details'] = {'error': str(e)}
            self.logger.error(f"Error checking timeliness for {data_type}: {e}")
        
        return result
    
    def detect_sales_anomalies(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Detect anomalies in sales data"""
        result = {
            'metric_name': 'anomaly_score',
            'data_source': 'sales',
            'timestamp': datetime.utcnow(),
            'status': 'pass',
            'details': {'anomalies': []}
        }
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get daily sales aggregates
            daily_sales = self.session.query(
                func.date(LiveSalesData.date).label('date'),
                func.sum(LiveSalesData.quantity_sold).label('total_quantity'),
                func.sum(LiveSalesData.revenue).label('total_revenue'),
                func.count(LiveSalesData.id).label('transaction_count')
            ).filter(
                and_(
                    LiveSalesData.date >= start_date,
                    LiveSalesData.date <= end_date
                )
            ).group_by(func.date(LiveSalesData.date)).all()
            
            if len(daily_sales) < 7:  # Need at least a week of data
                result['metric_value'] = 0.0
                result['threshold_value'] = self.thresholds['anomaly_score']['pass']
                result['details'] = {'error': 'Insufficient data for anomaly detection'}
                return result
            
            # Convert to arrays for analysis
            quantities = np.array([float(row.total_quantity) for row in daily_sales])
            revenues = np.array([float(row.total_revenue) for row in daily_sales])
            transactions = np.array([float(row.transaction_count) for row in daily_sales])
            
            # Detect anomalies using z-score
            anomalies = []
            
            # Quantity anomalies
            qty_z_scores = np.abs(stats.zscore(quantities))
            qty_anomalies = np.where(qty_z_scores > self.thresholds['anomaly_score']['warning'])[0]
            
            for idx in qty_anomalies:
                anomalies.append({
                    'date': daily_sales[idx].date,
                    'type': 'quantity',
                    'value': quantities[idx],
                    'z_score': qty_z_scores[idx],
                    'severity': 'high' if qty_z_scores[idx] > self.thresholds['anomaly_score']['pass'] else 'medium'
                })
            
            # Revenue anomalies
            rev_z_scores = np.abs(stats.zscore(revenues))
            rev_anomalies = np.where(rev_z_scores > self.thresholds['anomaly_score']['warning'])[0]
            
            for idx in rev_anomalies:
                anomalies.append({
                    'date': daily_sales[idx].date,
                    'type': 'revenue',
                    'value': revenues[idx],
                    'z_score': rev_z_scores[idx],
                    'severity': 'high' if rev_z_scores[idx] > self.thresholds['anomaly_score']['pass'] else 'medium'
                })
            
            # Calculate overall anomaly score
            max_z_score = max(np.max(qty_z_scores), np.max(rev_z_scores))
            result['metric_value'] = max_z_score
            result['threshold_value'] = self.thresholds['anomaly_score']['pass']
            result['details'] = {
                'anomalies': anomalies,
                'total_anomalies': len(anomalies),
                'max_z_score': max_z_score
            }
            
            # Determine status
            if max_z_score <= self.thresholds['anomaly_score']['warning']:
                result['status'] = 'pass'
            elif max_z_score <= self.thresholds['anomaly_score']['pass']:
                result['status'] = 'warning'
            else:
                result['status'] = 'fail'
                
        except Exception as e:
            result['status'] = 'fail'
            result['metric_value'] = float('inf')
            result['threshold_value'] = self.thresholds['anomaly_score']['pass']
            result['details'] = {'error': str(e)}
            self.logger.error(f"Error detecting sales anomalies: {e}")
        
        return result
    
    def detect_inventory_anomalies(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Detect anomalies in inventory data"""
        result = {
            'metric_name': 'anomaly_score',
            'data_source': 'inventory',
            'timestamp': datetime.utcnow(),
            'status': 'pass',
            'details': {'anomalies': []}
        }
        
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get products with significant inventory changes
            inventory_changes = self.session.query(
                LiveInventoryUpdate.product_id,
                func.min(LiveInventoryUpdate.stock_level).label('min_stock'),
                func.max(LiveInventoryUpdate.stock_level).label('max_stock'),
                func.avg(LiveInventoryUpdate.stock_level).label('avg_stock'),
                func.count(LiveInventoryUpdate.id).label('update_count')
            ).filter(
                and_(
                    LiveInventoryUpdate.date >= start_date,
                    LiveInventoryUpdate.date <= end_date
                )
            ).group_by(LiveInventoryUpdate.product_id).all()
            
            anomalies = []
            max_z_score = 0.0
            
            for row in inventory_changes:
                if row.update_count < 3:  # Need multiple updates to detect anomalies
                    continue
                
                # Calculate stock volatility
                stock_range = row.max_stock - row.min_stock
                volatility_ratio = stock_range / max(row.avg_stock, 1)
                
                # Flag high volatility as anomaly
                if volatility_ratio > 2.0:  # Stock range > 200% of average
                    z_score = volatility_ratio
                    max_z_score = max(max_z_score, z_score)
                    
                    anomalies.append({
                        'product_id': row.product_id,
                        'type': 'high_volatility',
                        'volatility_ratio': volatility_ratio,
                        'min_stock': row.min_stock,
                        'max_stock': row.max_stock,
                        'avg_stock': row.avg_stock,
                        'severity': 'high' if volatility_ratio > 3.0 else 'medium'
                    })
                
                # Flag potential stockouts
                if row.min_stock == 0:
                    anomalies.append({
                        'product_id': row.product_id,
                        'type': 'stockout',
                        'min_stock': row.min_stock,
                        'avg_stock': row.avg_stock,
                        'severity': 'high'
                    })
            
            result['metric_value'] = max_z_score
            result['threshold_value'] = self.thresholds['anomaly_score']['pass']
            result['details'] = {
                'anomalies': anomalies,
                'total_anomalies': len(anomalies),
                'max_volatility_ratio': max_z_score
            }
            
            # Determine status
            if max_z_score <= self.thresholds['anomaly_score']['warning']:
                result['status'] = 'pass'
            elif max_z_score <= self.thresholds['anomaly_score']['pass']:
                result['status'] = 'warning'
            else:
                result['status'] = 'fail'
                
        except Exception as e:
            result['status'] = 'fail'
            result['metric_value'] = float('inf')
            result['threshold_value'] = self.thresholds['anomaly_score']['pass']
            result['details'] = {'error': str(e)}
            self.logger.error(f"Error detecting inventory anomalies: {e}")
        
        return result
    
    def check_data_consistency(self, data_type: str) -> Dict[str, Any]:
        """Check data consistency across different sources"""
        result = {
            'metric_name': 'consistency',
            'data_source': data_type,
            'timestamp': datetime.utcnow(),
            'status': 'pass',
            'details': {}
        }
        
        try:
            if data_type == 'sales':
                # Check for negative values
                negative_qty = self.session.query(LiveSalesData).filter(
                    LiveSalesData.quantity_sold < 0
                ).count()
                
                negative_revenue = self.session.query(LiveSalesData).filter(
                    LiveSalesData.revenue < 0
                ).count()
                
                total_records = self.session.query(LiveSalesData).count()
                
                consistency_ratio = 1.0 - (negative_qty + negative_revenue) / max(total_records, 1)
                
                result['metric_value'] = consistency_ratio
                result['threshold_value'] = self.thresholds['consistency']['pass']
                result['details'] = {
                    'total_records': total_records,
                    'negative_quantity_records': negative_qty,
                    'negative_revenue_records': negative_revenue,
                    'inconsistent_records': negative_qty + negative_revenue
                }
            
            elif data_type == 'inventory':
                # Check for logical inconsistencies
                inconsistent_reserved = self.session.query(LiveInventoryUpdate).filter(
                    LiveInventoryUpdate.reserved_stock > LiveInventoryUpdate.stock_level
                ).count()
                
                negative_stock = self.session.query(LiveInventoryUpdate).filter(
                    LiveInventoryUpdate.stock_level < 0
                ).count()
                
                total_records = self.session.query(LiveInventoryUpdate).count()
                
                consistency_ratio = 1.0 - (inconsistent_reserved + negative_stock) / max(total_records, 1)
                
                result['metric_value'] = consistency_ratio
                result['threshold_value'] = self.thresholds['consistency']['pass']
                result['details'] = {
                    'total_records': total_records,
                    'inconsistent_reserved_records': inconsistent_reserved,
                    'negative_stock_records': negative_stock,
                    'inconsistent_records': inconsistent_reserved + negative_stock
                }
            
            # Determine status
            if result['metric_value'] >= self.thresholds['consistency']['pass']:
                result['status'] = 'pass'
            elif result['metric_value'] >= self.thresholds['consistency']['warning']:
                result['status'] = 'warning'
            else:
                result['status'] = 'fail'
                
        except Exception as e:
            result['status'] = 'fail'
            result['metric_value'] = 0.0
            result['threshold_value'] = self.thresholds['consistency']['pass']
            result['details'] = {'error': str(e)}
            self.logger.error(f"Error checking consistency for {data_type}: {e}")
        
        return result
    
    def run_comprehensive_quality_check(self) -> Dict[str, Any]:
        """Run comprehensive data quality check across all data types"""
        self.logger.info("Running comprehensive data quality check")
        
        results = {
            'timestamp': datetime.utcnow(),
            'overall_status': 'pass',
            'checks': [],
            'summary': {
                'total_checks': 0,
                'passed_checks': 0,
                'warning_checks': 0,
                'failed_checks': 0
            }
        }
        
        data_types = ['sales', 'inventory', 'demand']
        
        for data_type in data_types:
            # Completeness check
            completeness_result = self.check_data_completeness(data_type)
            results['checks'].append(completeness_result)
            
            # Timeliness check
            timeliness_result = self.check_data_timeliness(data_type)
            results['checks'].append(timeliness_result)
            
            # Consistency check
            consistency_result = self.check_data_consistency(data_type)
            results['checks'].append(consistency_result)
            
            # Anomaly detection
            if data_type == 'sales':
                anomaly_result = self.detect_sales_anomalies()
                results['checks'].append(anomaly_result)
            elif data_type == 'inventory':
                anomaly_result = self.detect_inventory_anomalies()
                results['checks'].append(anomaly_result)
        
        # Calculate summary
        for check in results['checks']:
            results['summary']['total_checks'] += 1
            
            if check['status'] == 'pass':
                results['summary']['passed_checks'] += 1
            elif check['status'] == 'warning':
                results['summary']['warning_checks'] += 1
            else:
                results['summary']['failed_checks'] += 1
        
        # Determine overall status
        if results['summary']['failed_checks'] > 0:
            results['overall_status'] = 'fail'
        elif results['summary']['warning_checks'] > 0:
            results['overall_status'] = 'warning'
        else:
            results['overall_status'] = 'pass'
        
        # Save results to database
        self._save_quality_metrics(results['checks'])
        
        return results
    
    def _save_quality_metrics(self, checks: List[Dict[str, Any]]):
        """Save quality metrics to database"""
        try:
            for check in checks:
                metric = DataQualityMetrics(
                    data_source=check['data_source'],
                    metric_name=check['metric_name'],
                    metric_value=check['metric_value'],
                    threshold_value=check['threshold_value'],
                    status=check['status']
                )
                
                if check.get('details'):
                    metric.set_details(check['details'])
                
                self.session.add(metric)
            
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Failed to save quality metrics: {e}")
    
    def get_quality_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get data quality trends over time"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        trends = {}
        
        try:
            # Get quality metrics over time
            metrics = self.session.query(DataQualityMetrics).filter(
                and_(
                    DataQualityMetrics.timestamp >= start_date,
                    DataQualityMetrics.timestamp <= end_date
                )
            ).order_by(DataQualityMetrics.timestamp).all()
            
            # Group by data source and metric
            for metric in metrics:
                key = f"{metric.data_source}_{metric.metric_name}"
                if key not in trends:
                    trends[key] = {
                        'timestamps': [],
                        'values': [],
                        'statuses': []
                    }
                
                trends[key]['timestamps'].append(metric.timestamp)
                trends[key]['values'].append(metric.metric_value)
                trends[key]['statuses'].append(metric.status)
            
            # Calculate trend statistics
            for key, data in trends.items():
                if len(data['values']) > 1:
                    # Calculate trend direction
                    values = np.array(data['values'])
                    x = np.arange(len(values))
                    trend_slope = np.polyfit(x, values, 1)[0] if len(values) > 2 else 0
                    
                    trends[key]['trend_slope'] = trend_slope
                    trends[key]['avg_value'] = np.mean(values)
                    trends[key]['latest_value'] = values[-1]
                    trends[key]['latest_status'] = data['statuses'][-1]
                
        except Exception as e:
            self.logger.error(f"Error getting quality trends: {e}")
        
        return trends


def main():
    """Main function for testing data quality monitoring"""
    from sqlalchemy import create_engine
    
    engine = create_engine(DATABASE_URL)
    session = get_session(engine)
    
    monitor = DataQualityMonitor(session)
    results = monitor.run_comprehensive_quality_check()
    
    print("Data Quality Check Results:")
    print(f"Overall Status: {results['overall_status']}")
    print(f"Summary: {results['summary']}")
    
    for check in results['checks']:
        print(f"\n{check['data_source']} - {check['metric_name']}: {check['status']}")
        print(f"  Value: {check['metric_value']:.3f} (Threshold: {check['threshold_value']:.3f})")
    
    session.close()


if __name__ == "__main__":
    main()