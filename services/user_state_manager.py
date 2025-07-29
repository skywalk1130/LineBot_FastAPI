from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class UserStateManager:
    """
    一個具備 TTL (Time-To-Live) 功能的用戶狀態管理器。
    它會在記憶體中儲存用戶狀態，並在狀態過期後自動清理，防止記憶體洩漏。
    """
    def __init__(self, default_ttl_seconds: int = 300):
        """
        初始化用戶狀態管理器。
        :param default_ttl_seconds: 狀態的默認存活時間（秒）。預設為 5 分鐘。
        """
        self._states: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = timedelta(seconds=default_ttl_seconds)

    def _is_expired(self, user_id: str) -> bool:
        """檢查指定用戶的狀態是否已過期。"""
        if user_id not in self._states:
            return True
        
        last_updated = self._states[user_id].get("last_updated")
        if not last_updated:
            logger.warning(f"State for user {user_id} has no timestamp. Considering it expired.")
            return True

        return datetime.now() > last_updated + self.default_ttl

    def set_user_state(self, user_id: str, state: Dict[str, Any]):
        """設置或更新用戶的狀態，並記錄時間戳。"""
        self._states[user_id] = {
            "data": state,
            "last_updated": datetime.now()
        }
        logger.debug(f"State set for user {user_id}: {state}")

    def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """獲取用戶的狀態。如果狀態已過期，則清除並返回 None。"""
        if self._is_expired(user_id):
            self.clear_user_state(user_id)
            return None
        return self._states[user_id].get("data")

    def clear_user_state(self, user_id: str):
        """從管理器中清除用戶的狀態。"""
        if user_id in self._states:
            del self._states[user_id]
            logger.info(f"Cleared state for user {user_id}.")

# 創建一個全域單例，方便在應用程式各處使用
user_state_manager = UserStateManager(default_ttl_seconds=300)

def set_user_state(user_id: str, state: dict):
    user_state_manager.set_user_state(user_id, state)

def get_user_state(user_id: str) -> dict:
    state = user_state_manager.get_user_state(user_id)
    return state if state is not None else {}

def clear_user_state(user_id: str):
    user_state_manager.clear_user_state(user_id)