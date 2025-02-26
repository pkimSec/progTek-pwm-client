import asyncio
from functools import wraps
from typing import Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import traceback
from PyQt6 import sip

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
                # Check if the object still exists before handling the error
                if hasattr(self, 'handle_error') and not sip.isdeleted(self):
                    self.handle_error(e)
                else:
                    print(f"Error in async callback: {e}")
                    traceback.print_exc()
        
        # Store a reference to self in the runner to prevent premature garbage collection
        runner = AsyncRunner(self)
        runner.self_ref = self  # Keep reference to self
        QTimer.singleShot(0, lambda: runner.run(async_func()))
        
    return wrapper