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
            # Create or get event loop safely
            loop = None
            try:
                # Check if we can get the existing event loop
                loop = asyncio.get_event_loop()
                
                # Check if the loop is already running
                if loop.is_running():
                    # Create a new loop for this task
                    loop = asyncio.new_event_loop()
                    print("Created new event loop (existing loop was running)")
            except RuntimeError:
                # No event loop in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                print("Created new event loop (no existing loop)")
            
            # Store loop for potential cleanup
            self.loop = loop
            
            # Run the coroutine in the event loop
            result = loop.run_until_complete(coro)
            self.finished.emit(result)
            
        except Exception as e:
            print(f"Error in AsyncRunner.run: {e}")
            try:
                self.error.emit(e)
            except RuntimeError as emit_error:
                print(f"Error emitting error signal: {emit_error}")
        finally:
            # Clean up loop if we created a new one
            if self.loop and self.loop != asyncio.get_event_loop():
                try:
                    self.loop.close()
                    print("Closed temporary event loop")
                except Exception as close_error:
                    print(f"Error closing event loop: {close_error}")

def async_callback(func: Callable) -> Callable:
    """
    Decorator to handle async callbacks in Qt slots.
    This ensures proper integration between asyncio and Qt.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> None:
        print(f"async_callback: wrapping {func.__name__}")
        
        # Store the async function as an attribute on the instance 
        # to prevent it from being garbage collected prematurely
        if not hasattr(self, '_async_tasks'):
            self._async_tasks = {}
        
        async def async_func():
            try:
                print(f"Starting async function: {func.__name__}")
                result = await func(self, *args, **kwargs)
                print(f"Completed async function: {func.__name__}")
                
                # Clean up reference
                if hasattr(self, '_async_tasks') and func.__name__ in self._async_tasks:
                    del self._async_tasks[func.__name__]
                    
                return result
            except Exception as e:
                print(f"Error in async function {func.__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # Try to handle the error in the UI if possible
                try:
                    if hasattr(self, 'handle_error'):
                        self.handle_error(e)
                    elif hasattr(self, 'show_error'):
                        self.show_error(e)
                    else:
                        # If no error handler, try to show error in main thread
                        def show_error_dialog():
                            try:
                                from PyQt6.QtWidgets import QMessageBox
                                QMessageBox.critical(
                                    None, 
                                    "Error", 
                                    f"An error occurred: {str(e)}"
                                )
                            except Exception as dialog_e:
                                print(f"Could not show error dialog: {dialog_e}")
                                
                        QTimer.singleShot(0, show_error_dialog)
                except Exception as handler_e:
                    print(f"Error handling exception: {handler_e}")
                
                # Clean up reference
                if hasattr(self, '_async_tasks') and func.__name__ in self._async_tasks:
                    del self._async_tasks[func.__name__]
        
        # Store reference to the task
        task_func = async_func()
        if hasattr(self, '_async_tasks'):
            self._async_tasks[func.__name__] = task_func
        
        # Check if self is a QObject before using as parent
        if isinstance(self, QObject):
            runner = AsyncRunner(self)
        else:
            # Use no parent if self is not a QObject
            runner = AsyncRunner()
        
        # Store reference to the runner
        if not hasattr(self, '_async_runners'):
            self._async_runners = []
        self._async_runners.append(runner)
            
        # Connect signals for tracking
        if hasattr(runner, 'finished'):
            runner.finished.connect(
                lambda result: print(f"Async function {func.__name__} finished with result: {result}")
            )
        if hasattr(runner, 'error'):
            runner.error.connect(
                lambda e: print(f"Async function {func.__name__} failed with error: {str(e)}")
            )
        
        # Start the async function
        try:
            # Use a method that doesn't access the event loop in the lambda
            QTimer.singleShot(0, lambda: runner.run(task_func))
            print(f"Scheduled async function: {func.__name__}")
        except Exception as e:
            print(f"Error scheduling async function {func.__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
        
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