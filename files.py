

class KeyProvider:
    def __init__(self):
        self.filepath = "keys.txt"
        self._keys = []
        self._load_keys()

    def _load_keys(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self._keys = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"ВНИМАНИЕ: Файл с ключами {self.filepath} не найден!")
            self._keys = []
    #
    # def get_key(self) -> str:
    #     # if not self._keys:
    #     #     raise ValueError("Нет доступных ключей для Gemini!")
    #     key = self.keys.pop(0)
    #     self.keys.append(key)
    #     return key

    @property
    def keys(self):
        if not self._keys:
            raise ValueError("Нет доступных ключей для Gemini!")
        return self._keys