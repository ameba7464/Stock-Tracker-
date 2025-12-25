"""
Transaction management utilities for database operations.

Provides decorators and context managers for safe transaction handling
with automatic rollback on errors and retry logic for deadlocks.
"""

import time
import functools
from typing import Callable, Any, Optional
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DBAPIError

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def transaction_scope(db: Session, auto_commit: bool = True):
    """
    Context manager for database transactions with automatic rollback.
    
    Usage:
        with transaction_scope(db):
            tenant = Tenant(name="Test")
            db.add(tenant)
            # Automatically commits on success, rolls back on error
    
    Args:
        db: SQLAlchemy session
        auto_commit: Whether to commit automatically (default: True)
    
    Yields:
        Session: Database session
    
    Raises:
        Exception: Re-raises any exception after rollback
    
    Note:
        Does NOT close the session - that's handled by the dependency injection system.
    """
    try:
        yield db
        if auto_commit:
            db.commit()
            logger.debug("Transaction committed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back due to error: {e}")
        raise


def with_transaction(auto_commit: bool = True):
    """
    Decorator for functions that need transaction management.
    
    Wraps function in transaction_scope, automatically handling commit/rollback.
    Function must accept 'db: Session' as first argument or keyword argument.
    
    Usage:
        @with_transaction()
        def create_tenant(db: Session, name: str):
            tenant = Tenant(name=name)
            db.add(tenant)
            return tenant
    
    Args:
        auto_commit: Whether to commit automatically
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract db session from arguments
            db = kwargs.get('db') or (args[0] if args and isinstance(args[0], Session) else None)
            
            if not db:
                raise ValueError(f"Function {func.__name__} must have 'db: Session' parameter")
            
            with transaction_scope(db, auto_commit=auto_commit):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def retry_on_deadlock(max_retries: int = 3, initial_backoff: float = 0.1):
    """
    Decorator to retry operations on database deadlock.
    
    Implements exponential backoff: wait = initial_backoff * (2 ** attempt).
    Only retries on deadlock or lock timeout errors.
    
    Usage:
        @retry_on_deadlock(max_retries=3)
        def update_stock(db: Session, product_id: str, quantity: int):
            product = db.query(Product).filter_by(id=product_id).with_for_update().first()
            product.total_stock += quantity
            db.commit()
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_backoff: Initial backoff time in seconds (default: 0.1)
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DBAPIError) as e:
                    error_msg = str(e).lower()
                    
                    # Check if it's a deadlock or lock timeout
                    if 'deadlock' in error_msg or 'lock' in error_msg:
                        last_exception = e
                        
                        # Get db session from args/kwargs to rollback
                        db = kwargs.get('db') or (args[0] if args and isinstance(args[0], Session) else None)
                        if db:
                            db.rollback()
                        
                        if attempt < max_retries - 1:
                            backoff_time = initial_backoff * (2 ** attempt)
                            logger.warning(
                                f"Deadlock detected in {func.__name__}, "
                                f"retrying in {backoff_time:.2f}s (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(backoff_time)
                        else:
                            logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                    else:
                        # Not a deadlock, don't retry
                        raise
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


def execute_with_lock(db: Session, model_class, filter_condition, callback: Callable[[Any], None]):
    """
    Execute callback with row-level lock (SELECT FOR UPDATE).
    
    Prevents race conditions by locking rows before modification.
    
    Usage:
        def update_callback(product):
            product.total_stock -= 10
        
        execute_with_lock(
            db,
            Product,
            Product.id == product_id,
            update_callback
        )
        db.commit()
    
    Args:
        db: SQLAlchemy session
        model_class: Model class (e.g., Product)
        filter_condition: Filter expression (e.g., Product.id == '...')
        callback: Function to execute on locked row(s)
    
    Returns:
        Result of query (locked rows)
    
    Raises:
        ValueError: If no rows found
    """
    # Lock rows with SELECT FOR UPDATE
    query = db.query(model_class).filter(filter_condition).with_for_update()
    result = query.first()
    
    if not result:
        raise ValueError(f"No {model_class.__name__} found matching condition")
    
    # Execute callback on locked row
    callback(result)
    
    logger.debug(f"Executed {callback.__name__} with row lock on {model_class.__name__}")
    
    return result


@contextmanager
def savepoint(db: Session, name: Optional[str] = None):
    """
    Context manager for nested transactions using SAVEPOINT.
    
    Useful for partial rollbacks within a larger transaction.
    
    Usage:
        db.begin()
        try:
            tenant = Tenant(name="Test")
            db.add(tenant)
            
            with savepoint(db, "create_user"):
                user = User(tenant_id=tenant.id)
                db.add(user)
                # If this fails, only user creation is rolled back
            
            db.commit()  # Commits tenant + user
        except:
            db.rollback()  # Rolls back everything
    
    Args:
        db: SQLAlchemy session
        name: Optional savepoint name
    
    Yields:
        Session: Database session with savepoint
    """
    savepoint_name = name or f"sp_{int(time.time() * 1000)}"
    
    try:
        nested = db.begin_nested()
        logger.debug(f"Created savepoint: {savepoint_name}")
        yield db
        nested.commit()
        logger.debug(f"Committed savepoint: {savepoint_name}")
    except Exception as e:
        nested.rollback()
        logger.warning(f"Rolled back savepoint {savepoint_name}: {e}")
        raise


class TransactionManager:
    """
    Advanced transaction manager with statistics tracking.
    
    Tracks commit/rollback counts, deadlock retries, and execution times.
    """
    
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.deadlocks = 0
        self.retries = 0
    
    @contextmanager
    def managed_transaction(self, db: Session):
        """
        Managed transaction with statistics tracking.
        
        Usage:
            tm = TransactionManager()
            with tm.managed_transaction(db):
                # operations
            
            print(f"Stats: {tm.commits} commits, {tm.rollbacks} rollbacks")
        """
        start_time = time.time()
        
        try:
            yield db
            db.commit()
            self.commits += 1
            duration = time.time() - start_time
            logger.info(f"Transaction committed in {duration:.3f}s")
        except (OperationalError, DBAPIError) as e:
            if 'deadlock' in str(e).lower():
                self.deadlocks += 1
            db.rollback()
            self.rollbacks += 1
            logger.error(f"Transaction rolled back: {e}")
            raise
        except Exception as e:
            db.rollback()
            self.rollbacks += 1
            logger.error(f"Transaction rolled back: {e}")
            raise
    
    def get_stats(self) -> dict:
        """Get transaction statistics."""
        return {
            "commits": self.commits,
            "rollbacks": self.rollbacks,
            "deadlocks": self.deadlocks,
            "retries": self.retries,
            "success_rate": self.commits / (self.commits + self.rollbacks) if self.commits + self.rollbacks > 0 else 0
        }


# Global transaction manager instance
transaction_manager = TransactionManager()
