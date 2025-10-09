#gui/logging_handlers.py
import logging
from queue import Empty, Queue
import sys
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import QObject, Signal, QTimer

class QtLogHandler(logging.Handler, QObject):
    logSignal = Signal(str)
    
    def __init__(self, text_edit):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.text_edit = text_edit
        self.queue = Queue()
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_queue)
        self.timer.start(100)  # Process queue every 100ms
        self._handling = False
        
    def process_queue(self):
        try:
            while True:
                record = self.queue.get_nowait()
                self._process_record(record)
        except Empty:
            pass
            
    def _process_record(self, record):
        try:
            msg = self.format(record)
            # Determine color based on level
            if record.levelno == logging.DEBUG:
                color = "gray"
            elif record.levelno == logging.INFO:
                color = "black"
            elif record.levelno == logging.WARNING:
                color = "orange"
            elif record.levelno == logging.ERROR:
                color = "red"
            elif record.levelno == logging.CRITICAL:
                color = "red; font-weight:bold; text-decoration: underline;"
            else:
                color = "black"
            
            html_msg = f'<span style="color:{color};">{msg}</span>'
            self.text_edit.setReadOnly(False)
            self.text_edit.append(html_msg)
            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.setReadOnly(True)
        except Exception as e:
            print(f"Error processing log record: {e}")

    def emit(self, record):
        try:
            self.queue.put(record)
        except Exception:
            self.handleError(record)

class BackgroundThreadHandler(logging.Handler, QObject):
    logReceived = Signal(object)
    
    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)
        self._handling = False  # Prevent recursive handling

    def emit(self, record):
        if self._handling:
            return
        try:
            self._handling = True
            # Ensure record can be formatted later
            if record.exc_info:
                record.exc_text = logging.Formatter().formatException(record.exc_info)
            if record.args:
                record.msg = record.msg % record.args
                record.args = None
            self.logReceived.emit(record)
        except Exception as e:
            print(f"Error emitting log record: {e}", file=sys.stderr)
            self.handleError(record)
        finally:
            self._handling = False