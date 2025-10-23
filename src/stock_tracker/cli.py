"""
Command-line interface for Stock Tracker manual operations.

Provides a comprehensive CLI for manual stock tracking operations, health checks,
configuration management, and system monitoring. Supports both interactive and
batch modes for different use cases.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

import colorlog

from stock_tracker.utils.logger import get_logger, setup_logging
from stock_tracker.utils.config import get_config, validate_configuration, reload_config
from stock_tracker.utils.health_checks import check_system_health, get_health_manager
from stock_tracker.core.models import SyncStatus
from stock_tracker.utils.monitoring import get_monitoring_system
from stock_tracker.utils.exceptions import StockTrackerError


# Setup CLI-specific logging
cli_logger = get_logger(__name__)


class StockTrackerCLI:
    """Command-line interface for Stock Tracker operations."""
    
    def __init__(self):
        self.config = None
        self.health_manager = None
        self.monitoring = None
    
    def _init_services(self):
        """Initialize services (lazy loading)."""
        if not self.config:
            try:
                self.config = get_config()
                self.health_manager = get_health_manager()
                self.monitoring = get_monitoring_system()
                cli_logger.info("Services initialized successfully")
            except Exception as e:
                cli_logger.error(f"Failed to initialize services: {e}")
                raise
    
    async def cmd_config(self, args) -> int:
        """Handle configuration commands."""
        try:
            if args.config_action == "validate":
                cli_logger.info("Validating configuration...")
                validation_result = validate_configuration()
                
                if validation_result["valid"]:
                    print("✅ Configuration is valid")
                    print(f"📊 Summary: {json.dumps(validation_result['summary'], indent=2)}")
                    return 0
                else:
                    print(f"❌ Configuration validation failed: {validation_result['error']}")
                    return 1
            
            elif args.config_action == "show":
                self._init_services()
                print("📋 Current configuration:")
                
                # Show sanitized config (without sensitive data)
                config_summary = {
                    "wildberries": {
                        "base_url": self.config.wildberries.base_url,
                        "statistics_base_url": self.config.wildberries.statistics_base_url,
                        "timeout": self.config.wildberries.timeout,
                        "rate_limit": self.config.wildberries.rate_limit,
                        "has_api_key": bool(self.config.wildberries.api_key)
                    },
                    "google_sheets": {
                        "sheet_id": self.config.google_sheets.sheet_id,
                        "sheet_name": self.config.google_sheets.sheet_name,
                        "batch_size": self.config.google_sheets.batch_size,
                        "service_account_exists": Path(self.config.google_sheets.service_account_key_path).exists()
                    },
                    "application": {
                        "log_level": self.config.app.log_level,
                        "log_dir": self.config.app.log_dir,
                        "timezone": self.config.app.timezone,
                        "debug_mode": self.config.app.debug_mode,
                        "dry_run": self.config.app.dry_run,
                        "auto_sync_enabled": self.config.app.auto_sync_enabled,
                        "sync_schedule": self.config.app.sync_schedule
                    }
                }
                
                print(json.dumps(config_summary, indent=2))
                return 0
            
            elif args.config_action == "reload":
                cli_logger.info("Reloading configuration...")
                reload_config()
                print("✅ Configuration reloaded successfully")
                return 0
            
        except Exception as e:
            cli_logger.error(f"Config command failed: {e}")
            print(f"❌ Configuration operation failed: {e}")
            return 1
    
    async def cmd_health(self, args) -> int:
        """Handle health check commands."""
        try:
            self._init_services()
            
            if args.health_action == "check":
                cli_logger.info("Running system health checks...")
                
                if args.check_name:
                    # Run specific health check
                    result = await self.health_manager.run_check(args.check_name)
                    if result:
                        status_emoji = {
                            "healthy": "✅",
                            "warning": "⚠️",
                            "critical": "❌",
                            "unknown": "❓"
                        }[result.status.value]
                        
                        print(f"{status_emoji} {result.name}: {result.message}")
                        print(f"⏱️  Duration: {result.duration_ms:.1f}ms")
                        
                        if result.details and args.verbose:
                            print(f"📋 Details: {json.dumps(result.details, indent=2)}")
                        
                        return 0 if result.status.value in ["healthy", "warning"] else 1
                    else:
                        print(f"❌ Health check '{args.check_name}' not found")
                        return 1
                else:
                    # Run all health checks
                    system_health = await check_system_health()
                    
                    status_emoji = {
                        "healthy": "✅",
                        "warning": "⚠️",
                        "critical": "❌",
                        "unknown": "❓"
                    }[system_health["overall_status"]]
                    
                    print(f"{status_emoji} Overall Status: {system_health['overall_status'].upper()}")
                    print(f"📊 {system_health['overall_message']}")
                    print(f"📈 Summary: {system_health['summary']}")
                    
                    if args.verbose:
                        print("\n🔍 Individual Check Results:")
                        for name, check_result in system_health["checks"].items():
                            check_emoji = {
                                "healthy": "✅",
                                "warning": "⚠️",
                                "critical": "❌",
                                "unknown": "❓"
                            }[check_result["status"]]
                            
                            print(f"  {check_emoji} {name}: {check_result['message']} ({check_result['duration_ms']:.1f}ms)")
                    
                    return 0 if system_health["overall_status"] in ["healthy", "warning"] else 1
            
            elif args.health_action == "list":
                print("🔍 Available health checks:")
                for check in self.health_manager.checks:
                    print(f"  • {check.name} (timeout: {check.timeout}s)")
                return 0
            
        except Exception as e:
            cli_logger.error(f"Health command failed: {e}")
            print(f"❌ Health check operation failed: {e}")
            return 1
    
    async def cmd_sync(self, args) -> int:
        """Handle sync operations."""
        try:
            self._init_services()
            
            if args.sync_action == "run":
                from stock_tracker.services.product_service import ProductService
                
                cli_logger.info("Starting manual sync operation...")
                print("🔄 Starting manual sync...")
                
                # Initialize product service
                product_service = ProductService()
                
                # Run sync operation
                if args.dry_run:
                    print("🧪 Running in dry-run mode (no changes will be made)")
                    # Set dry-run mode in config
                    self.config.app.dry_run = True
                
                # Perform the sync
                sync_result = await product_service.sync_all_products()
                
                if sync_result.status == SyncStatus.COMPLETED:
                    print("✅ Sync completed successfully")
                    print(f"📊 Products processed: {sync_result.products_processed}")
                    print(f"📋 Products total: {sync_result.products_total}")
                    if sync_result.errors:
                        print(f"⚠️  Errors encountered: {len(sync_result.errors)}")
                        if args.verbose:
                            for error in sync_result.errors:
                                print(f"   • {error}")
                    return 0
                else:
                    print(f"❌ Sync failed: {sync_result.get('error', 'Unknown error')}")
                    return 1
            
            elif args.sync_action == "status":
                print("📊 Sync status:")
                # Show last sync time, next scheduled sync, etc.
                # This would integrate with scheduling service
                print("  • Last sync: Not implemented yet")
                print("  • Next sync: Not implemented yet")
                print("  • Auto sync enabled: ", self.config.app.auto_sync_enabled)
                print("  • Sync schedule: ", self.config.app.sync_schedule)
                return 0
            
        except Exception as e:
            cli_logger.error(f"Sync command failed: {e}")
            print(f"❌ Sync operation failed: {e}")
            return 1
    
    async def cmd_api(self, args) -> int:
        """Handle API testing commands."""
        try:
            from stock_tracker.api.client import create_wildberries_client
            
            cli_logger.info("Testing Wildberries API...")
            print("🔌 Testing Wildberries API connection...")
            
            client = create_wildberries_client()
            
            try:
                result = await client.test_connection()
                
                if result["success"]:
                    print("✅ Wildberries API connection successful")
                    print(f"🔑 Has API key: {result['has_api_key']}")
                    print(f"📡 Base URL: {result['base_url']}")
                    print(f"📊 Statistics URL: {result['statistics_url']}")
                    
                    if args.verbose and result.get('task_id'):
                        print(f"📋 Test task ID: {result['task_id']}")
                    
                    return 0
                else:
                    print(f"❌ API connection failed: {result['error']}")
                    return 1
            
            finally:
                client.close()
            
        except Exception as e:
            cli_logger.error(f"API test failed: {e}")
            print(f"❌ API test failed: {e}")
            return 1
    
    async def cmd_monitor(self, args) -> int:
        """Handle monitoring commands."""
        try:
            self._init_services()
            
            if args.monitor_action == "status":
                print("📊 Monitoring system status:")
                
                # Get monitoring metrics
                metrics = self.monitoring.get_metrics_summary()
                print(f"📈 Total metrics: {len(metrics)}")
                
                if args.verbose:
                    print("\n📋 Recent metrics:")
                    for metric_name, data in list(metrics.items())[:10]:  # Show last 10
                        latest = data[-1] if data else None
                        if latest:
                            print(f"  • {metric_name}: {latest['value']} (tags: {latest.get('tags', {})})")
                
                return 0
            
            elif args.monitor_action == "alerts":
                print("🚨 Active alerts:")
                
                active_alerts = self.monitoring.get_active_alerts()
                if active_alerts:
                    for alert in active_alerts:
                        level_emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "❌"}
                        emoji = level_emoji.get(alert.level.name, "❓")
                        print(f"  {emoji} {alert.message} (triggered: {alert.triggered_at})")
                else:
                    print("  ✅ No active alerts")
                
                return 0
            
        except Exception as e:
            cli_logger.error(f"Monitor command failed: {e}")
            print(f"❌ Monitoring operation failed: {e}")
            return 1
    
    async def cmd_logs(self, args) -> int:
        """Handle log management commands."""
        try:
            self._init_services()
            
            log_dir = Path(self.config.app.log_dir)
            
            if args.logs_action == "list":
                print(f"📁 Log files in {log_dir}:")
                
                if log_dir.exists():
                    log_files = list(log_dir.glob("*.log"))
                    for log_file in sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True):
                        size = log_file.stat().st_size
                        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        print(f"  • {log_file.name} ({size} bytes, modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
                else:
                    print("  ❌ Log directory does not exist")
                
                return 0
            
            elif args.logs_action == "tail":
                log_file = log_dir / "stock_tracker.log"
                
                if log_file.exists():
                    print(f"📄 Last {args.lines} lines from {log_file.name}:")
                    
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines[-args.lines:]:
                            print(f"  {line.rstrip()}")
                else:
                    print(f"❌ Log file {log_file.name} not found")
                    return 1
                
                return 0
            
        except Exception as e:
            cli_logger.error(f"Logs command failed: {e}")
            print(f"❌ Logs operation failed: {e}")
            return 1
    
    async def cmd_security(self, args) -> int:
        """Handle security and credential management commands."""
        try:
            # Check if security module is available
            try:
                from stock_tracker.utils.security import (
                    get_credential_store, SecurityValidator, SecurityConfig
                )
                from stock_tracker.utils.config import setup_secure_credentials
            except ImportError:
                print("❌ Security module not available. Install required dependencies:")
                print("   pip install cryptography keyring")
                return 1
            
            if not args.security_action:
                print("❌ Security action required. Use --help for options.")
                return 1
            
            if args.security_action == "setup":
                print("🔐 Setting up secure credential storage...")
                
                # Get master password
                master_password = args.master_password
                if not master_password:
                    import getpass
                    master_password = getpass.getpass("Enter master password for encryption: ")
                
                if not master_password:
                    print("❌ Master password is required")
                    return 1
                
                # Validate password strength
                validator = SecurityValidator()
                strength = validator.check_password_strength(master_password)
                
                print(f"🔑 Password strength: {strength['strength']} (score: {strength['score']:.2f})")
                
                if strength['strength'] == 'weak':
                    print("⚠️  Warning: Weak password detected")
                    for rec in strength['recommendations']:
                        print(f"   • {rec}")
                    
                    confirm = input("Continue with weak password? (y/N): ").lower()
                    if confirm != 'y':
                        print("❌ Setup cancelled")
                        return 1
                
                # Setup credentials
                success = setup_secure_credentials(master_password)
                if success:
                    print("✅ Secure credential setup completed")
                    return 0
                else:
                    print("❌ Secure credential setup failed")
                    return 1
            
            elif args.security_action == "list":
                print("📋 Stored credentials:")
                
                store = get_credential_store()
                master_password = args.master_password
                
                if not master_password:
                    import getpass
                    master_password = getpass.getpass("Enter master password: ")
                
                try:
                    keys = store.list_stored_credentials(master_password)
                    
                    if keys:
                        for key in keys:
                            print(f"  • {key}")
                        print(f"\n📊 Total: {len(keys)} credentials stored")
                    else:
                        print("  No credentials found")
                    
                    return 0
                    
                except Exception as e:
                    print(f"❌ Failed to list credentials: {e}")
                    return 1
            
            elif args.security_action == "validate":
                print("🛡️  Validating security configuration...")
                
                # Load current config
                from stock_tracker.utils.config import get_config
                config = get_config()
                
                # Convert to dict for validation
                config_dict = {
                    "wildberries": config.wildberries.dict(),
                    "google_sheets": config.google_sheets.dict(),
                    "app": config.app.dict()
                }
                
                validator = SecurityValidator()
                warnings = validator.validate_configuration(config_dict)
                
                if warnings:
                    print(f"⚠️  Found {len(warnings)} security warnings:")
                    for warning in warnings:
                        print(f"   • {warning}")
                    return 1
                else:
                    print("✅ No security issues found")
                    return 0
            
            elif args.security_action == "change-password":
                print("🔄 Changing master password...")
                
                store = get_credential_store()
                
                # Get old password
                old_password = args.old_password
                if not old_password:
                    import getpass
                    old_password = getpass.getpass("Enter current master password: ")
                
                # Get new password
                new_password = args.new_password
                if not new_password:
                    import getpass
                    new_password = getpass.getpass("Enter new master password: ")
                    confirm_password = getpass.getpass("Confirm new master password: ")
                    
                    if new_password != confirm_password:
                        print("❌ Passwords do not match")
                        return 1
                
                # Validate new password strength
                validator = SecurityValidator()
                strength = validator.check_password_strength(new_password)
                
                print(f"🔑 New password strength: {strength['strength']} (score: {strength['score']:.2f})")
                
                if strength['strength'] == 'weak':
                    print("⚠️  Warning: Weak password detected")
                    confirm = input("Continue with weak password? (y/N): ").lower()
                    if confirm != 'y':
                        print("❌ Password change cancelled")
                        return 1
                
                try:
                    # Get all credentials with old password
                    keys = store.list_stored_credentials(old_password)
                    credentials = {}
                    
                    for key in keys:
                        credential = store.retrieve_credential(key, old_password)
                        if credential:
                            credentials[key] = credential
                    
                    # Re-store all credentials with new password
                    for key, credential in credentials.items():
                        store.delete_credential(key, old_password)
                        store.store_credential(key, credential, new_password)
                    
                    print(f"✅ Master password changed successfully")
                    print(f"📊 Re-encrypted {len(credentials)} credentials")
                    return 0
                    
                except Exception as e:
                    print(f"❌ Failed to change master password: {e}")
                    return 1
            
            elif args.security_action == "delete":
                print(f"🗑️  Deleting credential: {args.key}")
                
                store = get_credential_store()
                master_password = args.master_password
                
                if not master_password:
                    import getpass
                    master_password = getpass.getpass("Enter master password: ")
                
                # Confirm deletion
                confirm = input(f"Are you sure you want to delete '{args.key}'? (y/N): ").lower()
                if confirm != 'y':
                    print("❌ Deletion cancelled")
                    return 1
                
                try:
                    success = store.delete_credential(args.key, master_password)
                    
                    if success:
                        print(f"✅ Credential '{args.key}' deleted successfully")
                        return 0
                    else:
                        print(f"❌ Failed to delete credential '{args.key}'")
                        return 1
                        
                except Exception as e:
                    print(f"❌ Failed to delete credential: {e}")
                    return 1
            
            else:
                print(f"❌ Unknown security action: {args.security_action}")
                return 1
                
        except Exception as e:
            cli_logger.error(f"Security command failed: {e}")
            print(f"❌ Security operation failed: {e}")
            return 1


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="stock-tracker",
        description="Stock Tracker CLI - Manual operations and system management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  stock-tracker config validate          # Validate configuration
  stock-tracker health check            # Run all health checks
  stock-tracker health check --name api # Run specific health check
  stock-tracker sync run --dry-run      # Test sync without changes
  stock-tracker api test               # Test API connectivity
  stock-tracker monitor status         # Show monitoring status
  stock-tracker logs tail              # Show recent log entries
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Configuration commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_parser.add_argument(
        "config_action",
        choices=["validate", "show", "reload"],
        help="Configuration action to perform"
    )
    
    # Health check commands
    health_parser = subparsers.add_parser("health", help="Health check operations")
    health_parser.add_argument(
        "health_action",
        choices=["check", "list"],
        help="Health check action to perform"
    )
    health_parser.add_argument(
        "--name",
        dest="check_name",
        help="Name of specific health check to run"
    )
    
    # Sync commands
    sync_parser = subparsers.add_parser("sync", help="Data synchronization")
    sync_parser.add_argument(
        "sync_action",
        choices=["run", "status"],
        help="Sync action to perform"
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run sync in dry-run mode (no changes)"
    )
    
    # API commands
    api_parser = subparsers.add_parser("api", help="API testing")
    api_parser.add_argument(
        "api_action",
        choices=["test"],
        default="test",
        nargs="?",
        help="API action to perform"
    )
    
    # Monitoring commands
    monitor_parser = subparsers.add_parser("monitor", help="Monitoring and metrics")
    monitor_parser.add_argument(
        "monitor_action",
        choices=["status", "alerts"],
        help="Monitoring action to perform"
    )
    
    # Log commands
    logs_parser = subparsers.add_parser("logs", help="Log management")
    logs_parser.add_argument(
        "logs_action",
        choices=["list", "tail"],
        help="Log action to perform"
    )
    logs_parser.add_argument(
        "--lines",
        type=int,
        default=50,
        help="Number of lines to show (for tail command)"
    )
    
    # Security subcommands
    security_parser = subparsers.add_parser("security", help="Security and credential management")
    security_subparsers = security_parser.add_subparsers(dest="security_action", help="Security actions")
    
    # Setup secure credentials
    setup_parser = security_subparsers.add_parser("setup", help="Setup secure credential storage")
    setup_parser.add_argument("--master-password", help="Master password for encryption")
    
    # List stored credentials
    list_parser = security_subparsers.add_parser("list", help="List stored credentials")
    list_parser.add_argument("--master-password", help="Master password for decryption")
    
    # Validate security configuration
    validate_parser = security_subparsers.add_parser("validate", help="Validate security configuration")
    
    # Change master password
    change_pw_parser = security_subparsers.add_parser("change-password", help="Change master password")
    change_pw_parser.add_argument("--old-password", help="Current master password")
    change_pw_parser.add_argument("--new-password", help="New master password")
    
    # Delete credential
    delete_parser = security_subparsers.add_parser("delete", help="Delete stored credential")
    delete_parser.add_argument("key", help="Credential key to delete")
    delete_parser.add_argument("--master-password", help="Master password for access")
    
    return parser


async def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging for CLI
    setup_logging()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create CLI instance
    cli = StockTrackerCLI()
    
    try:
        # Route to appropriate command handler
        if args.command == "config":
            return await cli.cmd_config(args)
        elif args.command == "health":
            return await cli.cmd_health(args)
        elif args.command == "sync":
            return await cli.cmd_sync(args)
        elif args.command == "api":
            return await cli.cmd_api(args)
        elif args.command == "monitor":
            return await cli.cmd_monitor(args)
        elif args.command == "logs":
            return await cli.cmd_logs(args)
        elif args.command == "security":
            return await cli.cmd_security(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        return 130
    except Exception as e:
        cli_logger.error(f"CLI operation failed: {e}", exc_info=True)
        print(f"❌ Operation failed: {e}")
        return 1


def cli_entry_point():
    """Entry point for console script."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"❌ CLI failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_entry_point()