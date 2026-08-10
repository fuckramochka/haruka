"""Reusable inline forms, lists and galleries for native extensions."""
from __future__ import annotations
import asyncio, secrets, time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

Handler=Callable[[object],Awaitable[None]]
@dataclass
class InlineUnit:
 id: str
 owner_id: int
 created_at: float
 expires_at: float
 kind: str
 payload: dict=field(default_factory=dict)
 callbacks: dict[str,Handler]=field(default_factory=dict)

class InlineUnitManager:
 def __init__(self,bot,owner_id:int,ttl:int=900): self.bot=bot; self.owner_id=owner_id; self.ttl=ttl; self.units={}; self._task=None
 async def start(self): self._task=asyncio.create_task(self._reaper())
 async def stop(self):
  if self._task:
   self._task.cancel()
   await asyncio.gather(self._task, return_exceptions=True)
   self._task=None
 def _new(self,kind,payload,ttl=None):
  uid=secrets.token_urlsafe(6); now=time.time(); unit=InlineUnit(uid,self.owner_id,now,now+(ttl or self.ttl),kind,payload); self.units[uid]=unit; return unit
 def form(self,text:str,buttons:list[list[tuple[str,Handler]]],ttl=None):
  unit=self._new("form",{"text":text},ttl); rows=[]
  for row in buttons:
   rendered=[]
   for label,handler in row:
    key=secrets.token_hex(3); unit.callbacks[key]=handler; rendered.append(InlineKeyboardButton(label,callback_data=f"unit:{unit.id}:{key}"))
   rows.append(rendered)
  return unit,InlineKeyboardMarkup(rows)
 def pager(self,title:str,items:list[str],page_size:int=8,ttl=None):
  return self._new("list",{"title":title,"items":items,"page_size":page_size,"page":0},ttl)
 def gallery(self,items:list[dict],ttl=None): return self._new("gallery",{"items":items,"index":0},ttl)
 async def dispatch(self,query):
  parts=(query.data or "").split(":",2)
  if len(parts)!=3: return False
  unit=self.units.get(parts[1])
  if not unit or unit.expires_at<time.time(): await query.answer("Expired",show_alert=True); return True
  if not query.from_user or query.from_user.id!=unit.owner_id: await query.answer("Not allowed",show_alert=True); return True
  handler=unit.callbacks.get(parts[2])
  if handler: await handler(query)
  return True
 async def _reaper(self):
  while True:
   await asyncio.sleep(30); now=time.time(); self.units={k:v for k,v in self.units.items() if v.expires_at>now}
