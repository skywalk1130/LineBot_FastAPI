# 範例：使用簡單字典 (不持久化，僅供示範)
user_states = {} # {user_id: {"command": "query", "step": 1, ...}}

def set_user_state(user_id: str, state: dict):
    user_states[user_id] = state

def get_user_state(user_id: str) -> dict:
    return user_states.get(user_id, {})

def clear_user_state(user_id: str):
    if user_id in user_states:
        del user_states[user_id]