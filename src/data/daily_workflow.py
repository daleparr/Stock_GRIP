"""
Automated Daily Data Processing Workflow
"""
import os
import sys
import time
import schedule
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import smtplib
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    MimeText = None
    MimeMultipart = None
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .models import get_session
from .live_data_models import DataIngestionLog, DataQualityMetrics
from .csv_ingestion import CSVIngestionPipeline
from .live_feature_engineering import LiveFeatureEngineer
from .data_quality_monitor import DataQualityMonitor
from config.settings import DATABASE_URL


class WorkflowOrchestrator:
    """Orchestrates the daily data processing workflow"""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.logger = self._setup_logging()
        
        # Initialize components
        self.csv_pipeline = CSVIngestionPipeline(database_url)
        
        # Workflow configuration
        self.config = {
            'data_retention_days': 90,
            'quality_check_enabled': True,
            'feature_engineering_enabled': True,
            'notification_enabled': False,  # Set to True to enable email notifications
            'notification_email': 'admin@company.com',
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_username': '',
            'smtp_password': '',
            'max_processing_time_minutes': 60,
            'retry_attempts': 3,
            'retry_delay_minutes': 5
        }
        
        # Workflow state
        self.workflow_state = {
            'last_run': None,
            'current_run_id': None,
            'status': 'idle',
            'errors': []
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for workflow"""
        logger = logging.getLogger('workflow_orchestrator')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(log_dir / 'daily_workflow.log')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def run_daily_workflow(self) -> Dict[str, Any]:
        """Execute the complete daily data processing workflow"""
        start_time = datetime.utcnow()
        run_id = f"workflow_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.workflow_state['current_run_id'] = run_id
        self.workflow_state['status'] = 'running'
        self.workflow_state['errors'] = []
        
        self.logger.info(f"Starting daily workflow: {run_id}")
        
        workflow_result = {
            'run_id': run_id,
            'start_time': start_time,
            'end_time': None,
            'status': 'running',
            'steps': [],
            'summary': {
                'total_files_processed': 0,
                'total_records_processed': 0,
                'successful_records': 0,
                'failed_records': 0,
                'quality_checks_passed': 0,
                'quality_checks_failed': 0
            },
            'errors': []
        }
        
        try:
            # Step 1: Data Ingestion
            self.logger.info("Step 1: Starting CSV data ingestion")
            ingestion_result = self._run_data_ingestion()
            workflow_result['steps'].append(ingestion_result)
            
            if ingestion_result['status'] != 'success':
                self.logger.warning("Data ingestion completed with issues")
            
            # Update summary
            workflow_result['summary']['total_files_processed'] = len(ingestion_result.get('processed_files', []))
            workflow_result['summary']['total_records_processed'] = ingestion_result.get('total_records', 0)
            workflow_result['summary']['successful_records'] = ingestion_result.get('successful_records', 0)
            workflow_result['summary']['failed_records'] = ingestion_result.get('failed_records', 0)
            
            # Step 2: Data Quality Checks
            if self.config['quality_check_enabled']:
                self.logger.info("Step 2: Running data quality checks")
                quality_result = self._run_quality_checks()
                workflow_result['steps'].append(quality_result)
                
                # Update summary
                workflow_result['summary']['quality_checks_passed'] = quality_result.get('passed_checks', 0)
                workflow_result['summary']['quality_checks_failed'] = quality_result.get('failed_checks', 0)
            
            # Step 3: Feature Engineering (if enabled)
            if self.config['feature_engineering_enabled']:
                self.logger.info("Step 3: Running feature engineering")
                feature_result = self._run_feature_engineering()
                workflow_result['steps'].append(feature_result)
            
            # Step 4: Data Cleanup
            self.logger.info("Step 4: Running data cleanup")
            cleanup_result = self._run_data_cleanup()
            workflow_result['steps'].append(cleanup_result)
            
            # Step 5: Generate Reports
            self.logger.info("Step 5: Generating workflow reports")
            report_result = self._generate_reports(workflow_result)
            workflow_result['steps'].append(report_result)
            
            # Determine overall status
            failed_steps = [step for step in workflow_result['steps'] if step['status'] == 'failed']
            warning_steps = [step for step in workflow_result['steps'] if step['status'] == 'warning']
            
            if failed_steps:
                workflow_result['status'] = 'failed'
                self.workflow_state['status'] = 'failed'
            elif warning_steps:
                workflow_result['status'] = 'warning'
                self.workflow_state['status'] = 'warning'
            else:
                workflow_result['status'] = 'success'
                self.workflow_state['status'] = 'success'
            
        except Exception as e:
            self.logger.error(f"Workflow failed with exception: {e}")
            workflow_result['status'] = 'failed'
            workflow_result['errors'].append(str(e))
            self.workflow_state['status'] = 'failed'
            self.workflow_state['errors'].append(str(e))
        
        finally:
            # Finalize workflow
            end_time = datetime.utcnow()
            workflow_result['end_time'] = end_time
            workflow_result['duration_minutes'] = (end_time - start_time).total_seconds() / 60
            
            self.workflow_state['last_run'] = end_time
            self.workflow_state['current_run_id'] = None
            
            self.logger.info(f"Workflow completed: {workflow_result['status']} "
                           f"(Duration: {workflow_result['duration_minutes']:.2f} minutes)")
            
            # Send notifications if enabled
            if self.config['notification_enabled']:
                self._send_notification(workflow_result)
        
        return workflow_result
    
    def _run_data_ingestion(self) -> Dict[str, Any]:
        """Run CSV data ingestion step"""
        step_result = {
            'step_name': 'data_ingestion',
            'start_time': datetime.utcnow(),
            'status': 'running',
            'details': {}
        }
        
        try:
            # Process CSV files
            ingestion_result = self.csv_pipeline.process_daily_files()
            
            step_result['details'] = ingestion_result
            
            # Determine step status
            if ingestion_result['failed_records'] == 0:
                step_result['status'] = 'success'
            elif ingestion_result['successful_records'] > 0:
                step_result['status'] = 'warning'
            else:
                step_result['status'] = 'failed'
            
        except Exception as e:
            step_result['status'] = 'failed'
            step_result['details'] = {'error': str(e)}
            self.logger.error(f"Data ingestion failed: {e}")
        
        step_result['end_time'] = datetime.utcnow()
        step_result['duration_seconds'] = (step_result['end_time'] - step_result['start_time']).total_seconds()
        
        return step_result
    
    def _run_quality_checks(self) -> Dict[str, Any]:
        """Run data quality checks step"""
        step_result = {
            'step_name': 'quality_checks',
            'start_time': datetime.utcnow(),
            'status': 'running',
            'details': {}
        }
        
        try:
            engine = create_engine(self.database_url)
            session = get_session(engine)
            
            monitor = DataQualityMonitor(session)
            quality_result = monitor.run_comprehensive_quality_check()
            
            step_result['details'] = quality_result
            step_result['passed_checks'] = quality_result['summary']['passed_checks']
            step_result['failed_checks'] = quality_result['summary']['failed_checks']
            
            # Determine step status
            if quality_result['overall_status'] == 'pass':
                step_result['status'] = 'success'
            elif quality_result['overall_status'] == 'warning':
                step_result['status'] = 'warning'
            else:
                step_result['status'] = 'failed'
            
            session.close()
            
        except Exception as e:
            step_result['status'] = 'failed'
            step_result['details'] = {'error': str(e)}
            step_result['passed_checks'] = 0
            step_result['failed_checks'] = 0
            self.logger.error(f"Quality checks failed: {e}")
        
        step_result['end_time'] = datetime.utcnow()
        step_result['duration_seconds'] = (step_result['end_time'] - step_result['start_time']).total_seconds()
        
        return step_result
    
    def _run_feature_engineering(self) -> Dict[str, Any]:
        """Run feature engineering step"""
        step_result = {
            'step_name': 'feature_engineering',
            'start_time': datetime.utcnow(),
            'status': 'running',
            'details': {}
        }
        
        try:
            engine = create_engine(self.database_url)
            session = get_session(engine)
            
            feature_engineer = LiveFeatureEngineer(session)
            
            # Get products that need feature updates
            from .models import Product
            products = session.query(Product).limit(10).all()  # Process subset for performance
            
            features_generated = 0
            for product in products:
                try:
                    features = feature_engineer.create_comprehensive_feature_set(product.product_id)
                    if features:
                        features_generated += 1
                except Exception as e:
                    self.logger.warning(f"Failed to generate features for {product.product_id}: {e}")
            
            step_result['details'] = {
                'products_processed': len(products),
                'features_generated': features_generated
            }
            step_result['status'] = 'success'
            
            session.close()
            
        except Exception as e:
            step_result['status'] = 'failed'
            step_result['details'] = {'error': str(e)}
            self.logger.error(f"Feature engineering failed: {e}")
        
        step_result['end_time'] = datetime.utcnow()
        step_result['duration_seconds'] = (step_result['end_time'] - step_result['start_time']).total_seconds()
        
        return step_result
    
    def _run_data_cleanup(self) -> Dict[str, Any]:
        """Run data cleanup step"""
        step_result = {
            'step_name': 'data_cleanup',
            'start_time': datetime.utcnow(),
            'status': 'running',
            'details': {}
        }
        
        try:
            engine = create_engine(self.database_url)
            session = get_session(engine)
            
            # Clean up old data based on retention policy
            cutoff_date = datetime.utcnow() - timedelta(days=self.config['data_retention_days'])
            
            # Clean old ingestion logs
            old_logs = session.query(DataIngestionLog).filter(
                DataIngestionLog.timestamp < cutoff_date
            ).count()
            
            session.query(DataIngestionLog).filter(
                DataIngestionLog.timestamp < cutoff_date
            ).delete()
            
            # Clean old quality metrics
            old_metrics = session.query(DataQualityMetrics).filter(
                DataQualityMetrics.timestamp < cutoff_date
            ).count()
            
            session.query(DataQualityMetrics).filter(
                DataQualityMetrics.timestamp < cutoff_date
            ).delete()
            
            session.commit()
            
            step_result['details'] = {
                'old_logs_cleaned': old_logs,
                'old_metrics_cleaned': old_metrics,
                'retention_days': self.config['data_retention_days']
            }
            step_result['status'] = 'success'
            
            session.close()
            
        except Exception as e:
            step_result['status'] = 'failed'
            step_result['details'] = {'error': str(e)}
            self.logger.error(f"Data cleanup failed: {e}")
        
        step_result['end_time'] = datetime.utcnow()
        step_result['duration_seconds'] = (step_result['end_time'] - step_result['start_time']).total_seconds()
        
        return step_result
    
    def _generate_reports(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workflow reports"""
        step_result = {
            'step_name': 'generate_reports',
            'start_time': datetime.utcnow(),
            'status': 'running',
            'details': {}
        }
        
        try:
            # Create reports directory
            reports_dir = Path('reports')
            reports_dir.mkdir(exist_ok=True)
            
            # Generate workflow summary report
            report_file = reports_dir / f"workflow_report_{workflow_result['run_id']}.json"
            
            with open(report_file, 'w') as f:
                json.dump(workflow_result, f, indent=2, default=str)
            
            # Generate daily summary
            daily_summary = {
                'date': datetime.utcnow().date(),
                'workflow_status': workflow_result['status'],
                'files_processed': workflow_result['summary']['total_files_processed'],
                'records_processed': workflow_result['summary']['total_records_processed'],
                'success_rate': workflow_result['summary']['successful_records'] / max(workflow_result['summary']['total_records_processed'], 1),
                'quality_score': workflow_result['summary']['quality_checks_passed'] / max(workflow_result['summary']['quality_checks_passed'] + workflow_result['summary']['quality_checks_failed'], 1)
            }
            
            summary_file = reports_dir / f"daily_summary_{datetime.utcnow().strftime('%Y%m%d')}.json"
            with open(summary_file, 'w') as f:
                json.dump(daily_summary, f, indent=2, default=str)
            
            step_result['details'] = {
                'report_file': str(report_file),
                'summary_file': str(summary_file),
                'daily_summary': daily_summary
            }
            step_result['status'] = 'success'
            
        except Exception as e:
            step_result['status'] = 'failed'
            step_result['details'] = {'error': str(e)}
            self.logger.error(f"Report generation failed: {e}")
        
        step_result['end_time'] = datetime.utcnow()
        step_result['duration_seconds'] = (step_result['end_time'] - step_result['start_time']).total_seconds()
        
        return step_result
    
    def _send_notification(self, workflow_result: Dict[str, Any]):
        """Send email notification about workflow results"""
        if not self.config['notification_email'] or not EMAIL_AVAILABLE:
            if not EMAIL_AVAILABLE:
                self.logger.warning("Email functionality not available - skipping notification")
            return
        
        try:
            # Create email content
            subject = f"Stock GRIP Daily Workflow - {workflow_result['status'].upper()}"
            
            body = f"""
            Daily Workflow Report
            =====================
            
            Run ID: {workflow_result['run_id']}
            Status: {workflow_result['status']}
            Duration: {workflow_result['duration_minutes']:.2f} minutes
            
            Summary:
            - Files Processed: {workflow_result['summary']['total_files_processed']}
            - Records Processed: {workflow_result['summary']['total_records_processed']}
            - Successful Records: {workflow_result['summary']['successful_records']}
            - Failed Records: {workflow_result['summary']['failed_records']}
            - Quality Checks Passed: {workflow_result['summary']['quality_checks_passed']}
            - Quality Checks Failed: {workflow_result['summary']['quality_checks_failed']}
            
            Steps Completed:
            """
            
            for step in workflow_result['steps']:
                body += f"\n- {step['step_name']}: {step['status']} ({step['duration_seconds']:.1f}s)"
            
            if workflow_result['errors']:
                body += "\n\nErrors:\n"
                for error in workflow_result['errors']:
                    body += f"- {error}\n"
            
            # Send email
            msg = MimeMultipart()
            msg['From'] = self.config['smtp_username']
            msg['To'] = self.config['notification_email']
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            server.starttls()
            server.login(self.config['smtp_username'], self.config['smtp_password'])
            text = msg.as_string()
            server.sendmail(self.config['smtp_username'], self.config['notification_email'], text)
            server.quit()
            
            self.logger.info("Notification email sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def schedule_daily_workflow(self, time_str: str = "02:00"):
        """Schedule the daily workflow to run at specified time"""
        self.logger.info(f"Scheduling daily workflow to run at {time_str}")
        
        schedule.every().day.at(time_str).do(self.run_daily_workflow)
        
        self.logger.info("Daily workflow scheduled. Starting scheduler...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        return self.workflow_state.copy()


class FallbackDataHandler:
    """Handle missing or corrupted data with fallback mechanisms"""
    
    def __init__(self, database_session: Session):
        self.session = database_session
        self.logger = logging.getLogger(__name__)
    
    def handle_missing_sales_data(self, product_id: str, date: datetime) -> Dict[str, Any]:
        """Handle missing sales data using historical patterns"""
        try:
            # Get historical sales for the same day of week
            historical_sales = self.session.query(LiveSalesData).filter(
                LiveSalesData.product_id == product_id,
                func.extract('dow', LiveSalesData.date) == date.weekday()
            ).limit(10).all()
            
            if historical_sales:
                avg_quantity = sum(sale.quantity_sold for sale in historical_sales) / len(historical_sales)
                avg_revenue = sum(sale.revenue for sale in historical_sales) / len(historical_sales)
                
                # Create fallback record
                fallback_data = {
                    'product_id': product_id,
                    'date': date,
                    'quantity_sold': int(avg_quantity),
                    'revenue': avg_revenue,
                    'channel': 'estimated',
                    'is_fallback': True
                }
                
                return {'status': 'success', 'data': fallback_data}
            
            return {'status': 'no_historical_data', 'data': None}
            
        except Exception as e:
            self.logger.error(f"Error handling missing sales data: {e}")
            return {'status': 'error', 'data': None}
    
    def handle_missing_inventory_data(self, product_id: str, date: datetime) -> Dict[str, Any]:
        """Handle missing inventory data using last known values"""
        try:
            # Get last known inventory
            last_inventory = self.session.query(LiveInventoryUpdate).filter(
                LiveInventoryUpdate.product_id == product_id
            ).order_by(LiveInventoryUpdate.date.desc()).first()
            
            if last_inventory:
                # Create fallback record with last known values
                fallback_data = {
                    'product_id': product_id,
                    'date': date,
                    'stock_level': last_inventory.stock_level,
                    'reserved_stock': last_inventory.reserved_stock,
                    'in_transit': last_inventory.in_transit,
                    'location': last_inventory.location,
                    'is_fallback': True
                }
                
                return {'status': 'success', 'data': fallback_data}
            
            return {'status': 'no_historical_data', 'data': None}
            
        except Exception as e:
            self.logger.error(f"Error handling missing inventory data: {e}")
            return {'status': 'error', 'data': None}


def main():
    """Main function for running the workflow orchestrator"""
    orchestrator = WorkflowOrchestrator()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'schedule':
            # Run as scheduled service
            time_str = sys.argv[2] if len(sys.argv) > 2 else "02:00"
            orchestrator.schedule_daily_workflow(time_str)
        elif sys.argv[1] == 'run':
            # Run once
            result = orchestrator.run_daily_workflow()
            print(json.dumps(result, indent=2, default=str))
    else:
        # Default: run once
        result = orchestrator.run_daily_workflow()
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()