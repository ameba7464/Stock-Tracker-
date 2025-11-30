"""
Global error handling middleware.
"""

import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import (
    StockTrackerError,
    ValidationError,
    APIError,
    DatabaseError,
    AuthenticationError
)

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for consistent error handling and logging.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request with error handling."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log request
            duration = time.time() - start_time
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
            )
            
            return response
            
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Validation Error",
                    "message": str(e),
                    "details": e.details if hasattr(e, 'details') else None
                }
            )
        
        except AuthenticationError as e:
            logger.warning(f"Authentication error: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Authentication Error",
                    "message": str(e)
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        except APIError as e:
            logger.error(f"API error: {e}")
            return JSONResponse(
                status_code=e.status_code if hasattr(e, 'status_code') else status.HTTP_502_BAD_GATEWAY,
                content={
                    "error": "API Error",
                    "message": str(e)
                }
            )
        
        except DatabaseError as e:
            logger.error(f"Database error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Database Error",
                    "message": "A database error occurred"
                }
            )
        
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Database Error",
                    "message": "A database error occurred"
                }
            )
        
        except StockTrackerError as e:
            logger.error(f"Stock Tracker error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Error",
                    "message": str(e)
                }
            )
        
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred"
                }
            )
