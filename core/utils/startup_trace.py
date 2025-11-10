import sys
import threading
import queue
import datetime
import atexit
import os
from pathlib import Path

# --- Configuration ---
LOG_DIRECTORY = "logs"
QUEUE_SIZE = 2000  # Bounded queue to prevent memory exhaustion
SHUTDOWN_MARKER = None

# --- State ---
log_queue = queue.Queue(maxsize=QUEUE_SIZE)
worker_thread = None
project_root = None
trace_initialized = False

def _get_project_root():
    """Determine the project root directory."""
    # sys.argv[0] is the path to the script that was executed.
    # We resolve it to an absolute path and get its parent directory.
    # This works because the main entry scripts are in the project root.
    return Path(sys.argv[0]).resolve().parent

def _log_worker():
    """Worker thread function to process log entries from the queue."""
    global project_root
    if not project_root:
        project_root = _get_project_root()

    log_dir = project_root / LOG_DIRECTORY
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = log_dir / f"startup_trace_{timestamp}.log"

    try:
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(f"--- Startup Trace Log: {datetime.datetime.now()} ---")
            f.write(f"Project Root: {project_root}\n\n")
            while True:
                try:
                    entry = log_queue.get()
                    if entry is SHUTDOWN_MARKER:
                        break
                    f.write(entry + "\n")
                    f.flush()
                except queue.Empty:
                    continue # Should not happen with a blocking get, but as a safeguard.
    except IOError as e:
        print(f"Error: Could not write to log file {log_file_path}. {e}", file=sys.stderr)
    finally:
        # Final write to indicate clean shutdown
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write("\n--- End of Trace ---")


def _trace_function(frame, event, arg):
    """The trace function passed to sys.settrace."""
    if event != 'call':
        return _trace_function

    code = frame.f_code
    filename = code.co_filename
    func_name = code.co_name
    line_no = frame.f_lineno

    # 1. Filter out non-project files.
    # A simple startswith check on the string path is efficient and sufficient.
    if not filename.startswith(str(project_root)):
        return _trace_function

    # 2. Filter out this module's own functions to avoid noise.
    if filename == __file__:
        return _trace_function

    # 3. Format the log entry.
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    try:
        relative_path = Path(filename).relative_to(project_root)
    except ValueError:
        relative_path = filename # Fallback if not relative
    
    log_entry = f"{now} | CALL | {relative_path}:{line_no} | {func_name}()"

    # 4. Enqueue the entry without blocking.
    try:
        log_queue.put_nowait(log_entry)
    except queue.Full:
        # Silently drop if the queue is full to prevent blocking the main thread.
        pass

    return _trace_function

def _shutdown_handler():
    """Gracefully shuts down the tracing."""
    sys.settrace(None)  # Disable the trace function
    if worker_thread and worker_thread.is_alive():
        log_queue.put(SHUTDOWN_MARKER)
        # Wait a couple of seconds for the queue to be processed
        worker_thread.join(timeout=2.0)

def activate():
    """Initializes and starts the tracing system."""
    global worker_thread, project_root, trace_initialized

    # Ensure this runs only once.
    if trace_initialized:
        return
    
    trace_initialized = True
    project_root = _get_project_root()

    # Start the background worker.
    worker_thread = threading.Thread(target=_log_worker, name="StartupTraceWorker", daemon=True)
    worker_thread.start()

    # Register shutdown handler.
    atexit.register(_shutdown_handler)

    # Set the trace function.
    sys.settrace(_trace_function)
