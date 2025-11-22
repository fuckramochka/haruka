import asyncio
import os
from system.engine import Engine

# Check Python version
import sys
if sys.version_info < (3, 8):
    print("❌ Haruka requires Python 3.8 or newer!")
    exit(1)

if __name__ == "__main__":
    try:
        core = Engine()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(core.start())
    except KeyboardInterrupt:
        print("\n👋 Haruka is turned off. Goodbye!")
    except Exception as e:
        print(f"\n❌ Critical startup error: {e}")
        input("Press Enter to exit...")