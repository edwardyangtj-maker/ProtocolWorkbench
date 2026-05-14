import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_IM_MODULE", "compose")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

try:
    import qasync
    from qasync import QEventLoop
    HAS_QASYNC = True
except ImportError:
    HAS_QASYNC = False


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    from protocol_workbench.app.main_window import MainWindow
    from protocol_workbench.app.theme import DARK_THEME_QSS

    app.setStyleSheet(DARK_THEME_QSS)

    window = MainWindow()
    window.show()

    if HAS_QASYNC:
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        with loop:
            loop.run_forever()
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        _original_create_task = asyncio.create_task

        async def _process_async():
            stopped = []
            for task in list(asyncio.all_tasks(loop)):
                if task.done():
                    try:
                        task.result()
                    except Exception:
                        pass
                    stopped.append(task)
            for task in stopped:
                task.cancel()
            try:
                loop.run_until_complete(asyncio.sleep(0.001))
            except Exception:
                pass

        timer = QTimer()
        timer.setInterval(50)
        timer.timeout.connect(lambda: _process_async())
        timer.start()

        def _patched_create_task(coro):
            return loop.create_task(coro)

        asyncio.create_task = _patched_create_task

        sys.exit(app.exec())


if __name__ == "__main__":
    main()
