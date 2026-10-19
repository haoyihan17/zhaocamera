"""通用后台线程：把耗时的 OCR / 翻译放到子线程，避免卡 UI。"""
from PyQt5.QtCore import QThread, pyqtSignal


class Worker(QThread):
    """在子线程执行 fn(*args, **kwargs)，通过信号回传结果/错误。"""

    result = pyqtSignal(object)
    error = pyqtSignal(str)
    done = pyqtSignal()

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.result.emit(res)
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))
        finally:
            self.done.emit()
