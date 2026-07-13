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


class SupplyChainTests(unittest.TestCase):
    def test_blocks_typosquats_and_known_bad(self):
        from haruka.core.metadata import screen_requirements
        blocked, _ = screen_requirements(["pyrogramm", "pyrogran", "requests==2.31.0"])
        self.assertIn("pyrogramm", blocked)
        self.assertIn("pyrogran", blocked)
        self.assertNotIn("requests==2.31.0", blocked)

    def test_allows_trusted_and_warns_unpinned(self):
        from haruka.core.metadata import screen_requirements
        blocked, warnings = screen_requirements(["kurigram", "httpx"])
        self.assertEqual(blocked, [])
        self.assertIn("httpx", warnings)
        self.assertNotIn("kurigram", warnings)


class PluginSystemTests(unittest.IsolatedAsyncioTestCase):
    def _manager(self):
        import types as _types
        from haruka.core.plugins import PluginManager
        core = _types.SimpleNamespace(loader=None, client=None)
        return PluginManager(core, FakeDB())

    async def test_outgoing_transform_runs_in_priority_order(self):
        from haruka.core.plugins import Plugin

        class A(Plugin):
            name = "A"
            priority = 10
            async def transform_outgoing(self, text, ctx=None):
                return text + "[A]"

        class B(Plugin):
            name = "B"
            priority = 20
            async def transform_outgoing(self, text, ctx=None):
                return text + "[B]"

        m = self._manager()
        await m._register(B(), "user", None)
        await m._register(A(), "user", None)
        self.assertEqual(await m.apply_outgoing("x", None), "x[A][B]")

    async def test_before_command_veto(self):
        from haruka.core.plugins import Plugin

        class Veto(Plugin):
            name = "Veto"
            async def before_command(self, ctx):
                return False

        m = self._manager()
        await m._register(Veto(), "user", None)
        self.assertFalse(await m.run_before_command(None))

    async def test_disabled_plugin_is_skipped(self):
        from haruka.core.plugins import Plugin

        class Sig(Plugin):
            name = "Sig"
            async def transform_outgoing(self, text, ctx=None):
                return text + "!"

        m = self._manager()
        await m._register(Sig(), "user", None)
        await m.set_enabled("Sig", False)
        self.assertEqual(await m.apply_outgoing("x", None), "x")
        await m.set_enabled("Sig", True)
        self.assertEqual(await m.apply_outgoing("x", None), "x!")

    async def test_plugin_options_override(self):
        from haruka.core.plugins import Plugin

        class Opt(Plugin):
            name = "Opt"
            options = {"text": "default"}

        m = self._manager()
        await m._register(Opt(), "user", None)
        inst = m._find("Opt").instance
        self.assertEqual(inst.option("text"), "default")
        await inst.set_option("text", "custom")
        self.assertEqual(inst.option("text"), "custom")


class HikkaRelativeImportTests(unittest.TestCase):
    def test_relative_import_module_loads(self):
        """A Heroku-style module using ``from .. import loader, utils`` must load
        under the synthetic compat package without the "no known parent
        package" error."""
        import importlib.util
        import sys
        import tempfile
        from pathlib import Path
        from haruka.compat.hikka_runtime import (
            USER_MODULE_PACKAGE,
            install_hikka_runtime,
        )

        install_hikka_runtime()
        self.assertIn("heroku.loader", sys.modules)
        self.assertIn("heroku.utils", sys.modules)

        source = (
            "from .. import loader, utils\n"
            "from . import loader as loader2\n"
            "RESULT = (loader is loader2)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "relmod.py"
            path.write_text(source, encoding="utf-8")
            import_name = f"{USER_MODULE_PACKAGE}.relmod_test"
            spec = importlib.util.spec_from_file_location(import_name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            try:
                spec.loader.exec_module(mod)  # must not raise
                self.assertTrue(mod.RESULT)
                self.assertTrue(hasattr(mod.loader, "Module"))
            finally:
                sys.modules.pop(spec.name, None)
