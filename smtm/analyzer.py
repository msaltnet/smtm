# The original Analyzer has been refactored and moved to the analyzer/ directory.
# 기존 Analyzer는 리팩터링되어 analyzer/ 디렉토리로 이동되었습니다.
# To use the new structure, import as follows:
# 새로운 구조를 사용하려면 다음을 import하세요:
# from .analyzer import Analyzer

# Import the existing class for backward compatibility.
# 하위 호환성을 위해 기존 클래스를 import합니다.
from .analyzer.analyzer import Analyzer

# Maintain alias for compatibility with existing code.
# 기존 코드와의 호환성을 위해 별칭을 유지합니다.
__all__ = ["Analyzer"]
