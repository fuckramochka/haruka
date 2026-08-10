"""Telegram QR login flow using raw MTProto login tokens."""
from __future__ import annotations
import asyncio, base64, io, time
from pyrogram import Client, raw

class QRLogin:
 def __init__(self,client:Client,api_id:int,api_hash:str): self.client=client; self.api_id=api_id; self.api_hash=api_hash
 async def export(self):
  result=await self.client.invoke(raw.functions.auth.ExportLoginToken(api_id=self.api_id,api_hash=self.api_hash,except_ids=[]))
  if isinstance(result,raw.types.auth.LoginTokenMigrateTo):
   await self.client.storage.dc_id(result.dc_id); await self.client.session.stop(); await self.client.session.start(); result=await self.client.invoke(raw.functions.auth.ImportLoginToken(token=result.token))
  if isinstance(result,raw.types.auth.LoginTokenSuccess): return None,result.authorization
  token=base64.urlsafe_b64encode(result.token).decode().rstrip('='); return f"tg://login?token={token}",None
 async def wait(self,timeout=120,on_token=None):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   link,auth=await self.export()
   if auth: return auth
   if on_token: await on_token(link)
   await asyncio.sleep(2)
  raise TimeoutError("QR login expired")

def qr_png(link:str):
 import qrcode
 out=io.BytesIO(); qrcode.make(link).save(out,format="PNG"); return out.getvalue()
