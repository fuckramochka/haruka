"""Engine localization with runtime language switching and fallbacks."""
from __future__ import annotations
from typing import Mapping

PACKS: dict[str, dict[str, str]] = {
 "en": {"engine.online":"Engine is online","common.saved":"Saved","common.close":"Close","common.back":"Back","help.title":"Command Atlas"},
 "ru": {"engine.online":"Движок запущен","common.saved":"Сохранено","common.close":"Закрыть","common.back":"Назад","help.title":"Атлас команд"},
 "uk": {"engine.online":"Рушій запущено","common.saved":"Збережено","common.close":"Закрити","common.back":"Назад","help.title":"Атлас команд"},
 "ja": {"engine.online":"エンジンはオンラインです","common.saved":"保存しました","common.close":"閉じる","common.back":"戻る","help.title":"コマンド一覧"},
 "de": {"engine.online":"Engine ist online","common.saved":"Gespeichert","common.close":"Schließen","common.back":"Zurück","help.title":"Befehlsatlas"},
 "fr": {"engine.online":"Le moteur est en ligne","common.saved":"Enregistré","common.close":"Fermer","common.back":"Retour","help.title":"Atlas des commandes"},
 "es": {"engine.online":"El motor está activo","common.saved":"Guardado","common.close":"Cerrar","common.back":"Atrás","help.title":"Atlas de comandos"},
}

class Translator:
 def __init__(self, db): self.db=db
 @property
 def language(self): return self.db.get("core","language","en")
 async def set_language(self, code: str):
  if code not in PACKS: raise ValueError(f"Unsupported language: {code}")
  await self.db.set("core","language",code)
 def t(self,key: str,default: str|None=None,**values):
  value=PACKS.get(self.language,{}).get(key,PACKS["en"].get(key,default or key))
  return value.format(**values)
 def extend(self,code: str,items: Mapping[str,str]): PACKS.setdefault(code,{}).update(items)
