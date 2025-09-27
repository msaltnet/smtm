# The original TelegramController has been refactored and moved to the telegram/ directory.
# 기존 TelegramController는 리팩터링되어 telegram/ 디렉토리로 이동되었습니다.
# To use the new structure, import as follows:
# 새로운 구조를 사용하려면 다음을 import하세요:
# from .telegram import TelegramController

# Import the existing class for backward compatibility.
# 하위 호환성을 위해 기존 클래스를 import합니다.
from .telegram.telegram_controller import TelegramController

# Maintain alias for compatibility with existing code.
# 기존 코드와의 호환성을 위해 별칭을 유지합니다.
__all__ = ["TelegramController"]
