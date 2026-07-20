"""统一设置项目根目录到 sys.path，所有测试文件无需单独处理"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
