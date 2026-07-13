import asyncio
import tempfile
import unittest
from pathlib import Path

from haruka.core.config import ConfigOption, ModuleConfig
from haruka.core.loader import Loader
from haruka.core.module import Module, command, watcher
from haruka.core.preferences import PreferenceStore
from haruka.utils import format_file_size, is_url, slugify


class FakeDB:
    def __init__(self):
        self.data = {}
    def get(self, owner, key, default=None):
        return self.data.get((owner, key), default)
    async def set(self, owner, key, value):
        self.data[(owner, key)] = value


class FakeSettings:
    def __init__(self, root):
        self.modules_dir = Path(root) / "modules"


class Good(Module):
    name = "Good"
    @command(aliases=["g"])
    async def hello(self, ctx):
        return None
    @watcher(no_bots=True, no_commands=True)
    async def observe(self, ctx):
        return None


class Broken(Module):
    name = "Broken"
    @command()
    async def broken(self, ctx):
        return None
    async def on_load(self):
        raise RuntimeError("boom")


class EngineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = FakeDB()
        self.loader = Loader(object(), self.db, FakeSettings(self.tmp.name))

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_registration_and_alias(self):
        await self.loader._register(Good(), "user", Path("good.py"), "test_good")
        self.assertEqual(self.loader.find_command("G").module.name, "Good")
        self.assertEqual(len(self.loader.watchers), 1)

    async def test_failed_hook_rolls_back(self):
        with self.assertRaises(RuntimeError):
            await self.loader._register(Broken(), "user", Path("broken.py"), "test_broken")
        self.assertIsNone(self.loader.find_command("broken"))
        self.assertNotIn("Broken", self.loader.modules)

    async def test_feature_gates_persist(self):
        await self.loader._register(Good(), "user", Path("good.py"))
        await self.loader.set_command_enabled("hello", False)
        await self.loader.set_module_enabled("good", False)
        self.assertFalse(self.loader.is_command_enabled("hello"))
        self.assertFalse(self.loader.is_module_enabled("Good"))

    async def test_config_validation(self):
        cfg = ModuleConfig(ConfigOption("count", 1, validator=int))
        saved = {}
        async def persist(key, value): saved[key] = value
        cfg.bind({}, persist)
        await cfg.set("count", "5")
        self.assertEqual(cfg["count"], 5)
        self.assertEqual(saved["count"], 5)

    async def test_engine_preferences(self):
        store = PreferenceStore(self.db)
        self.assertEqual(store.get().style, "aurora")
        await store.cycle_style()
        self.assertEqual(store.get().style, "carbon")
        await store.toggle("compact_help")
        self.assertTrue(store.get().compact_help)


class UtilityTests(unittest.TestCase):
    def test_urls(self):
        self.assertTrue(is_url("https://example.com/mod.py"))
        self.assertFalse(is_url("http://127.0.0.1/mod.py"))
        self.assertFalse(is_url("file:///etc/passwd"))
    def test_formatting(self):
        self.assertEqual(format_file_size(1024), "1.0 KiB")
        self.assertEqual(slugify("Hello, World!"), "hello_world")


if __name__ == "__main__":
    unittest.main()


class PlatformFeatureTests(unittest.IsolatedAsyncioTestCase):
    async def test_translator_switch(self):
        from haruka.i18n import Translator
        db = FakeDB(); tr = Translator(db)
        await tr.set_language("ru")
        self.assertEqual(tr.t("common.saved"), "Сохранено")

    def test_extension_manifest_checksum(self):
        from haruka.ecosystem import ExtensionManifest, compatibility
        import hashlib
        source = b"print(1)"
        manifest = ExtensionManifest(name="Demo", sha256=hashlib.sha256(source).hexdigest())
        self.assertTrue(manifest.verify_source(source))
        self.assertEqual(compatibility(manifest), [])
