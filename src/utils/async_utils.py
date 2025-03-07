import asyncio
from functools import wraps
from typing import Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import traceback

class AsyncRunner(QObject):
    """Utility class to run async functions from Qt"""
    
    finished = pyqtSignal(object)  # Signal emitted with result
    error = pyqtSignal(Exception)  # Signal emitted on error
    
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.loop = None
        print("Creating AsyncRunner")
        
    def run(self, coro):
        """Run coroutine and emit result or error"""
        try:
            # Create or get event loop
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
            
            result = self.loop.run_until_complete(coro)
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(e)

def async_callback(func: Callable) -> Callable:
    """Decorator to handle async callbacks in Qt slots"""
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> None:
        async def async_func():
            try:
                result = await func(self, *args, **kwargs)
                return result
            except Exception as e:
                if hasattr(self, 'handle_error'):
                    self.handle_error(e)
                else:
                    raise e
        
        # Check if self is a QObject before using as parent
        if isinstance(self, QObject):
            runner = AsyncRunner(self)
        else:
            # Use no parent if self is not a QObject
            runner = AsyncRunner()
            
        QTimer.singleShot(0, lambda: runner.run(async_func()))
        
    return wrapper

def standalone_async_task(func: Callable, *args, **kwargs) -> None:
    """Run an async function without needing a QObject instance"""
    async def async_func():
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(f"Error in standalone_async_task: {str(e)}")
            traceback.print_exc()
            return None
    
    runner = AsyncRunner()  # No parent
    QTimer.singleShot(0, lambda: runner.run(async_func()))