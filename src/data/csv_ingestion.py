"""
CSV Data Ingestion Pipeline for Live Data Integration
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import os
import json
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Product, Inventory, Demand, get_session
from .live_data_models import (
    LiveSalesData, LiveInventoryUpdate, LiveDemandSignals,
    DataIngestionLog, DataQualityMetrics
)
from config.settings import DATABASE_URL

class CSVValidator:
    """Validates CSV data before ingestion"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define expected schemas
        self.schemas = {
            'sales': {
                'required_columns': ['date', 'product_id', 'channel', 'quantity_sold', 'revenue'],
                'optional_columns': ['customer_segment', 'promotion_code', 'fulfillment_method'],
                'data_types': {
                    'date': 'datetime',
                    'product_id': 'string',
                    'channel': 'string',
                    'quantity_sold': 'int',
                    'revenue': 'float',
                    'customer_segment': 'string',
                    'promotion_code': 'string',
                    'fulfillment_method': 'string'
                }
            },
            'inventory': {
                'required_columns': ['date', 'product_id', 'location', 'stock_level'],
                'optional_columns': ['reserved_stock', 'in_transit', 'supplier_id', 'last_reorder_date'],
                'data_types': {
                    'date': 'datetime',
                    'product_id': 'string',
                    'location': 'string',
                    'stock_level': 'int',
                    'reserved_stock': 'int',
                    'in_transit': 'int',
                    'supplier_id': 'string',
                    'last_reorder_date': 'datetime'
                }
            },
            'demand': {
                'required_columns': ['date', 'product_id', 'external_demand'],
                'optional_columns': ['market_trend', 'competitor_price', 'weather_factor', 'event_impact', 'social_sentiment'],
                'data_types': {
                    'date': 'datetime',
                    'product_id': 'string',
                    'external_demand': 'string',
                    'market_trend': 'float',
                    'competitor_price': 'float',
                    'weather_factor': 'string',
                    'event_impact': 'string',
                    'social_sentiment': 'float'
                }
            }
        }
    
    def validate_schema(self, df: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Validate CSV schema against expected format"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if data_type not in self.schemas:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Unknown data type: {data_type}")
            return validation_result
        
        schema = self.schemas[data_type]
        
        # Check required columns
        missing_columns = set(schema['required_columns']) - set(df.columns)
        if missing_columns:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Missing required columns: {missing_columns}")
        
        # Check for unexpected columns
        expected_columns = set(schema['required_columns'] + schema['optional_columns'])
        unexpected_columns = set(df.columns) - expected_columns
        if unexpected_columns:
            validation_result['warnings'].append(f"Unexpected columns: {unexpected_columns}")
        
        return validation_result
    
    def validate_data_types(self, df: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Validate data types and convert where possible"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'converted_df': df.copy()
        }
        
        schema = self.schemas[data_type]
        converted_df = df.copy()
        
        for column, expected_type in schema['data_types'].items():
            if column not in df.columns:
                continue
            
            try:
                if expected_type == 'datetime':
                    converted_df[column] = pd.to_datetime(df[column])
                elif expected_type == 'int':
                    converted_df[column] = pd.to_numeric(df[column], errors='coerce').astype('Int64')
                elif expected_type == 'float':
                    converted_df[column] = pd.to_numeric(df[column], errors='coerce')
                elif expected_type == 'string':
                    converted_df[column] = df[column].astype(str)
                
                # Check for conversion failures
                if expected_type in ['int', 'float']:
                    null_count = converted_df[column].isnull().sum() - df[column].isnull().sum()
                    if null_count > 0:
                        validation_result['warnings'].append(
                            f"Column '{column}': {null_count} values could not be converted to {expected_type}"
                        )
                
            except Exception as e:
                validation_result['errors'].append(f"Error converting column '{column}' to {expected_type}: {e}")
                validation_result['valid'] = False
        
        validation_result['converted_df'] = converted_df
        return validation_result
    
    def validate_business_rules(self, df: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Validate business logic rules"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if data_type == 'sales':
            # Sales-specific validations
            if 'quantity_sold' in df.columns:
                negative_qty = df[df['quantity_sold'] < 0]
                if not negative_qty.empty:
                    validation_result['errors'].append(f"Found {len(negative_qty)} records with negative quantity_sold")
            
            if 'revenue' in df.columns:
                negative_revenue = df[df['revenue'] < 0]
                if not negative_revenue.empty:
                    validation_result['warnings'].append(f"Found {len(negative_revenue)} records with negative revenue")
            
            # Check valid channels
            if 'channel' in df.columns:
                valid_channels = ['online', 'pos', 'marketplace', 'wholesale']
                invalid_channels = df[~df['channel'].isin(valid_channels)]
                if not invalid_channels.empty:
                    validation_result['warnings'].append(f"Found {len(invalid_channels)} records with invalid channels")
        
        elif data_type == 'inventory':
            # Inventory-specific validations
            if 'stock_level' in df.columns:
                negative_stock = df[df['stock_level'] < 0]
                if not negative_stock.empty:
                    validation_result['errors'].append(f"Found {len(negative_stock)} records with negative stock_level")
            
            if 'reserved_stock' in df.columns and 'stock_level' in df.columns:
                invalid_reserved = df[df['reserved_stock'] > df['stock_level']]
                if not invalid_reserved.empty:
                    validation_result['errors'].append(f"Found {len(invalid_reserved)} records where reserved_stock > stock_level")
        
        elif data_type == 'demand':
            # Demand-specific validations
            if 'external_demand' in df.columns:
                valid_demand_levels = ['high', 'medium', 'low']
                invalid_demand = df[~df['external_demand'].isin(valid_demand_levels)]
                if not invalid_demand.empty:
                    validation_result['warnings'].append(f"Found {len(invalid_demand)} records with invalid external_demand values")
            
            if 'market_trend' in df.columns:
                out_of_range = df[(df['market_trend'] < -1.0) | (df['market_trend'] > 1.0)]
                if not out_of_range.empty:
                    validation_result['warnings'].append(f"Found {len(out_of_range)} records with market_trend outside [-1.0, 1.0] range")
        
        if validation_result['errors']:
            validation_result['valid'] = False
        
        return validation_result


class CSVIngestionPipeline:
    """Main CSV ingestion pipeline"""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.validator = CSVValidator()
        self.logger = logging.getLogger(__name__)
        
        # Create data directories
        self.data_dir = Path("data/live_feeds")
        self.processed_dir = Path("data/processed")
        self.error_dir = Path("data/errors")
        
        for directory in [self.data_dir, self.processed_dir, self.error_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def process_csv_file(self, file_path: str, data_type: str) -> Dict[str, Any]:
        """Process a single CSV file"""
        start_time = datetime.utcnow()
        file_name = os.path.basename(file_path)
        
        # Initialize processing log
        processing_log = {
            'file_name': file_name,
            'file_type': data_type,
            'records_processed': 0,
            'records_successful': 0,
            'records_failed': 0,
            'status': 'pending',
            'errors': []
        }
        
        try:
            # Read CSV file
            self.logger.info(f"Processing {file_name} as {data_type} data")
            df = pd.read_csv(file_path)
            processing_log['records_processed'] = len(df)
            
            # Validate schema
            schema_validation = self.validator.validate_schema(df, data_type)
            if not schema_validation['valid']:
                processing_log['errors'].extend(schema_validation['errors'])
                processing_log['status'] = 'failed'
                return processing_log
            
            # Validate and convert data types
            type_validation = self.validator.validate_data_types(df, data_type)
            if not type_validation['valid']:
                processing_log['errors'].extend(type_validation['errors'])
                processing_log['status'] = 'failed'
                return processing_log
            
            df = type_validation['converted_df']
            
            # Validate business rules
            business_validation = self.validator.validate_business_rules(df, data_type)
            if not business_validation['valid']:
                processing_log['errors'].extend(business_validation['errors'])
                processing_log['status'] = 'failed'
                return processing_log
            
            # Add warnings to log
            all_warnings = (schema_validation.get('warnings', []) + 
                          type_validation.get('warnings', []) + 
                          business_validation.get('warnings', []))
            if all_warnings:
                processing_log['warnings'] = all_warnings
            
            # Ingest data into database
            ingestion_result = self._ingest_data(df, data_type)
            processing_log['records_successful'] = ingestion_result['successful']
            processing_log['records_failed'] = ingestion_result['failed']
            
            if ingestion_result['failed'] > 0:
                processing_log['status'] = 'partial'
                processing_log['errors'].extend(ingestion_result['errors'])
            else:
                processing_log['status'] = 'success'
            
            # Move processed file
            self._move_processed_file(file_path, processing_log['status'])
            
        except Exception as e:
            self.logger.error(f"Error processing {file_name}: {e}")
            processing_log['status'] = 'failed'
            processing_log['errors'].append(str(e))
            
            # Move to error directory
            self._move_processed_file(file_path, 'failed')
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        processing_log['processing_time_seconds'] = processing_time
        
        # Log to database
        self._log_processing_result(processing_log)
        
        return processing_log
    
    def _ingest_data(self, df: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Ingest validated data into database"""
        from sqlalchemy import create_engine
        
        engine = create_engine(self.database_url)
        session = get_session(engine)
        
        result = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            for index, row in df.iterrows():
                try:
                    if data_type == 'sales':
                        record = LiveSalesData(
                            date=row['date'],
                            product_id=row['product_id'],
                            channel=row['channel'],
                            quantity_sold=row['quantity_sold'],
                            revenue=row['revenue'],
                            customer_segment=row.get('customer_segment', 'regular'),
                            promotion_code=row.get('promotion_code'),
                            fulfillment_method=row.get('fulfillment_method', 'warehouse')
                        )
                    
                    elif data_type == 'inventory':
                        record = LiveInventoryUpdate(
                            date=row['date'],
                            product_id=row['product_id'],
                            location=row['location'],
                            stock_level=row['stock_level'],
                            reserved_stock=row.get('reserved_stock', 0),
                            in_transit=row.get('in_transit', 0),
                            supplier_id=row.get('supplier_id'),
                            last_reorder_date=row.get('last_reorder_date')
                        )
                    
                    elif data_type == 'demand':
                        record = LiveDemandSignals(
                            date=row['date'],
                            product_id=row['product_id'],
                            external_demand=row['external_demand'],
                            market_trend=row.get('market_trend', 0.0),
                            competitor_price=row.get('competitor_price'),
                            weather_factor=row.get('weather_factor', 'normal'),
                            event_impact=row.get('event_impact', 'none'),
                            social_sentiment=row.get('social_sentiment', 0.0)
                        )
                    
                    session.add(record)
                    result['successful'] += 1
                    
                except Exception as e:
                    result['failed'] += 1
                    result['errors'].append(f"Row {index}: {str(e)}")
                    self.logger.warning(f"Failed to process row {index}: {e}")
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            result['errors'].append(f"Database error: {str(e)}")
            self.logger.error(f"Database error during ingestion: {e}")
        
        finally:
            session.close()
        
        return result
    
    def _move_processed_file(self, file_path: str, status: str):
        """Move processed file to appropriate directory"""
        file_name = os.path.basename(file_path)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if status == 'success':
            destination = self.processed_dir / f"{timestamp}_{file_name}"
        else:
            destination = self.error_dir / f"{timestamp}_{file_name}"
        
        try:
            os.rename(file_path, destination)
            self.logger.info(f"Moved {file_name} to {destination}")
        except Exception as e:
            self.logger.error(f"Failed to move {file_name}: {e}")
    
    def _log_processing_result(self, processing_log: Dict[str, Any]):
        """Log processing result to database"""
        from sqlalchemy import create_engine
        
        try:
            engine = create_engine(self.database_url)
            session = get_session(engine)
            
            log_entry = DataIngestionLog(
                file_name=processing_log['file_name'],
                file_type=processing_log['file_type'],
                records_processed=processing_log['records_processed'],
                records_successful=processing_log['records_successful'],
                records_failed=processing_log['records_failed'],
                processing_time_seconds=processing_log['processing_time_seconds'],
                status=processing_log['status']
            )
            
            if processing_log.get('errors'):
                log_entry.set_error_details({
                    'errors': processing_log['errors'],
                    'warnings': processing_log.get('warnings', [])
                })
            
            session.add(log_entry)
            session.commit()
            session.close()
            
        except Exception as e:
            self.logger.error(f"Failed to log processing result: {e}")
    
    def process_daily_files(self) -> Dict[str, Any]:
        """Process all CSV files in the data directory"""
        results = {
            'processed_files': [],
            'total_records': 0,
            'successful_records': 0,
            'failed_records': 0,
            'errors': []
        }
        
        # Look for CSV files in data directory
        csv_files = list(self.data_dir.glob("*.csv"))
        
        if not csv_files:
            self.logger.info("No CSV files found for processing")
            return results
        
        for csv_file in csv_files:
            # Determine data type from filename
            file_name = csv_file.name.lower()
            
            if 'sales' in file_name:
                data_type = 'sales'
            elif 'inventory' in file_name:
                data_type = 'inventory'
            elif 'demand' in file_name:
                data_type = 'demand'
            else:
                self.logger.warning(f"Cannot determine data type for {csv_file.name}")
                continue
            
            # Process file
            processing_result = self.process_csv_file(str(csv_file), data_type)
            
            results['processed_files'].append(processing_result)
            results['total_records'] += processing_result['records_processed']
            results['successful_records'] += processing_result['records_successful']
            results['failed_records'] += processing_result['records_failed']
            
            if processing_result.get('errors'):
                results['errors'].extend(processing_result['errors'])
        
        self.logger.info(f"Daily processing complete: {len(csv_files)} files, "
                        f"{results['successful_records']}/{results['total_records']} records successful")
        
        return results


def main():
    """Main function for testing CSV ingestion"""
    pipeline = CSVIngestionPipeline()
    results = pipeline.process_daily_files()
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()