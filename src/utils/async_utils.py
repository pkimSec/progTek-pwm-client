import asyncio
from functools import wraps
from typing import Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class AsyncRunner(QObject):
    """Utility class to run async functions from Qt"""
    
    finished = pyqtSignal(object)  # Signal emitted with result
    error = pyqtSignal(Exception)  # Signal emitted on error
    
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._loop = asyncio.new_event_loop()
        
    def run(self, coro):
        """Run coroutine and emit result or error"""
        try:
            result = self._loop.run_until_complete(coro)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(e)

def async_callback(callback_func: Callable = None) -> Callable:
    """Decorator to handle async callbacks in Qt slots"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> None:
            async def async_func():
                try:
                    result = await func(self, *args, **kwargs)
                    if callback_func:
                        callback_func(self, result)
                except Exception as e:
                    if hasattr(self, 'handle_error'):
                        self.handle_error(e)
                    else:
                        raise e
            
            runner = AsyncRunner(self)
            QTimer.singleShot(0, lambda: runner.run(async_func()))
        return wrapper
    return decorator