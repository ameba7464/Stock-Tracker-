"""
Main entry point for Wildberries Stock Tracker application.

This module provides the main application entry point and legacy command-line interface
for the stock tracking system. For the full CLI interface, use the dedicated CLI module
(stock_tracker.cli) which provides comprehensive operations and management.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_tracker.utils.logger import setup_logging, get_logger
from stock_tracker.utils.config import get_config
from stock_tracker.utils.health_checks import check_system_health


def setup_environment() -> None:
    """Setup application environment and load configuration."""
    # Load environment variables from .env file if it exists
    try:
        from dotenv import load_dotenv
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment from {env_file}")
        else:
            logger.info("No .env file found, using system environment variables")
    except ImportError:
        logger.warning("python-dotenv not installed, using system environment variables only")
    
    # Validate configuration using pydantic
    try:
        config = get_config()
        logger.info("Configuration validation passed")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        logger.error("Please check your .env file or environment configuration")
        sys.exit(1)


async def run_sync(sync_type: str = "manual") -> None:
    """
    Run data synchronization.
    
    Args:
        sync_type: Type of sync ("manual" or "scheduled")
    """
    logger.info(f"Starting {sync_type} synchronization...")
    
    try:
        from stock_tracker.services.product_service import ProductService
        
        # Initialize product service
        product_service = ProductService()
        
        # Run sync operation
        sync_session = await product_service.sync_all_products()
        sync_result = sync_session.to_dict()
        
        if sync_session.is_completed():
            logger.info(f"Sync completed successfully")
            logger.info(f"Products processed: {sync_result.get('products_processed', 0)}")
            logger.info(f"Products synced: {sync_session.products_synced}")
            logger.info(f"Success rate: {sync_session.get_success_rate():.1f}%")
            
            if sync_session.errors:
                logger.warning(f"Sync completed with {len(sync_session.errors)} errors")
                for error in sync_session.errors:
                    logger.error(f"Sync error: {error}")
        else:
            logger.error(f"Sync failed: {sync_session.last_error or 'Unknown error'}")
            raise Exception(sync_session.last_error or 'Sync failed')
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise


async def run_scheduler() -> None:
    """Run the automated scheduler for daily sync."""
    logger.info("Starting automated scheduler...")
    
    try:
        from stock_tracker.services.scheduler import SchedulerService
        
        # Initialize scheduler service
        scheduler_service = SchedulerService()
        
        # Start scheduler (this will run indefinitely)
        await scheduler_service.start()
        
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        raise


async def check_health() -> None:
    """Check application health and connectivity."""
    logger.info("Performing health check...")
    
    try:
        health_status = await check_system_health()
        
        logger.info(f"Health check completed: {health_status['overall_status']}")
        logger.info(f"Summary: {health_status['summary']}")
        
        # Log individual check results
        for check_name, result in health_status['checks'].items():
            if result['status'] == 'healthy':
                logger.info(f"✅ {check_name}: {result['message']}")
            elif result['status'] == 'warning':
                logger.warning(f"⚠️ {check_name}: {result['message']}")
            else:
                logger.error(f"❌ {check_name}: {result['message']}")
        
        if health_status['overall_status'] == 'critical':
            raise Exception("Critical health check failures detected")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise


async def update_table() -> None:
    """Update Google Sheets table with fresh data from Wildberries API."""
    logger.info("Starting table update...")
    
    try:
        from stock_tracker.database.sheets import GoogleSheetsClient
        from stock_tracker.database.operations import SheetsOperations
        from pathlib import Path
        
        # Get configuration
        config = get_config()
        
        # Check if spreadsheet ID is configured
        spreadsheet_id = getattr(config, 'google_sheet_id', None)
        if not spreadsheet_id:
            logger.error("Spreadsheet ID not configured. Please set GOOGLE_SHEET_ID in environment")
            raise Exception("Missing spreadsheet ID configuration")
        
        # Initialize Google Sheets client
        service_account_path = Path(__file__).parent.parent.parent / "config" / "service-account.json"
        
        if not service_account_path.exists():
            logger.error(f"Service account file not found: {service_account_path}")
            raise Exception(f"Missing service account file: {service_account_path}")
        
        logger.info("Connecting to Google Sheets...")
        sheets_client = GoogleSheetsClient(str(service_account_path))
        operations = SheetsOperations(sheets_client)
        
        # Update the table
        logger.info("Updating table with fresh data from Wildberries API...")
        success = operations.update_table_on_startup(
            spreadsheet_id=spreadsheet_id,
            worksheet_name="Stock Tracker"
        )
        
        if success:
            logger.info("✅ Table update completed successfully")
        else:
            logger.error("❌ Table update failed")
            raise Exception("Table update operation failed")
    
    except Exception as e:
        logger.error(f"Table update failed: {e}")
        raise


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Wildberries Stock Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m stock_tracker.main                      # Start scheduler
  python -m stock_tracker.main --sync               # Manual sync
  python -m stock_tracker.main --health             # Health check
  python -m stock_tracker.main --update-table       # Update Google Sheets table
  python -m stock_tracker.main --sync --dry-run     # Dry run sync

For full CLI functionality, use:
  python -m stock_tracker.cli --help
        """
    )
    
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Trigger manual synchronization"
    )
    
    parser.add_argument(
        "--health",
        action="store_true", 
        help="Perform health check"
    )
    
    parser.add_argument(
        "--update-table",
        action="store_true",
        help="Update Google Sheets table with fresh data from API"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't make actual changes"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override log level"
    )
    
    return parser


async def main() -> None:
    """Main application entry point."""
    # Setup logging first
    setup_logging()
    
    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Override log level if specified
    if args.log_level:
        os.environ["LOG_LEVEL"] = args.log_level
        # Re-setup logging with new level
        setup_logging()
    
    # Set dry run mode if specified
    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        logger.info("Running in DRY RUN mode - no actual changes will be made")
    
    logger.info("Wildberries Stock Tracker starting...")
    
    try:
        # Setup environment and validate configuration
        setup_environment()
        
        # Execute based on command line arguments
        if args.health:
            await check_health()
        elif args.sync:
            await run_sync("manual")
        elif args.update_table:
            await update_table()
        else:
            # Default: start scheduler
            await run_scheduler()
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        logger.info("Wildberries Stock Tracker shutting down...")


# Module-level logger
logger = get_logger(__name__)


if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)