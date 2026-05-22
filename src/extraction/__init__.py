"""旧版资料提取兼容门面。

新代码优先使用 src.understanding；这里保留给已有调用方平滑迁移。
"""

from src.extraction.engine import ExtractionEngine

__all__ = ["ExtractionEngine"]
