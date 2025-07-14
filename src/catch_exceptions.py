from functools import wraps
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
            service_logger.error(f"File not found: {e}")
            raise HTTPException(status_code=404, detail="No xml file")
        except Exception as e:
            service_logger.error(f"Error: {e}")
            raise HTTPException(status_code=422, detail="Error; see server logs for traceback")

    return wrapper
