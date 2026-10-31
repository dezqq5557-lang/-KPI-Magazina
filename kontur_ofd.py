"""
Адаптер Контур.ОФД.
Не содержит секретов. URL и ключ передаются при запуске/через защищённые настройки.

Перед боевым подключением нужно сопоставить методы с действующей документацией
Контур.ОФД и получить официальный API-доступ.
"""
import requests

class KonturOFD:
    def __init__(self, base_url, api_key, timeout=30):
        self.base_url=base_url.rstrip("/")
        self.s=requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {api_key}",
                               "Accept":"application/json"})
        self.timeout=timeout

    def get(self, path, params=None):
        r=self.s.get(self.base_url+"/"+path.lstrip("/"),params=params,timeout=self.timeout)
        r.raise_for_status()
        return r.json()
