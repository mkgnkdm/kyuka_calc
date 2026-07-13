# PythonAnywhere 用 WSGI エントリポイント。
# Web タブの WSGI 設定ファイルからこのファイルを参照する(パスは deploy Skill 参照)。
import sys
from pathlib import Path

project_home = str(Path(__file__).resolve().parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application  # noqa: E402,F401
