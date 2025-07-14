from functools import wraps
import traceback
from fastapi import HTTPException

from .configuration import service_logger


def catch_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            service_logger.info(f"Calling endpoint: {func.__name__}")
            if kwargs and "file" in kwargs:
                service_logger.info(f"Processing file: {kwargs['file'].filename}")
            if kwargs and "xml_file_name" in kwargs:
                service_logger.info(f"Asking for file: {kwargs['xml_file_name']}")
            return await func(*args, **kwargs)
        except FileNotFoundError as e:
            service_logger.error(f"File not found in {func.__name__}: {e}")
            service_logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise HTTPException(status_code=404, detail="No xml file")
        except Exception as e:
            # Log comprehensive error information
            service_logger.error(f"Unhandled exception in {func.__name__}:")
            service_logger.error(f"  Exception type: {type(e).__name__}")
            service_logger.error(f"  Exception message: {str(e)}")
            service_logger.error(f"  Function arguments: args={args}, kwargs={list(kwargs.keys())}")
            service_logger.error(f"Full traceback:\n{traceback.format_exc()}")
            
            # Provide more informative HTTP response
            error_detail = f"Error in {func.__name__}: {type(e).__name__}: {str(e)}"
            raise HTTPException(status_code=422, detail=error_detail)

    return wrapper
