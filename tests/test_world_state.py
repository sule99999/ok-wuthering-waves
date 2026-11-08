"""Realm detection must use the team flag, and Daily Task must leave a domain first."""

import importlib
import importlib.machinery
import importlib.util
import sys
import types
import unittest


def _install_missing_import_stubs():
    """Let this check import the task module where Windows-only packages are absent."""
    if importlib.util.find_spec("ok") is None:
        class _OkModule(types.ModuleType):
            def __getattr__(self, name):
                if name.startswith("__"):
                    raise AttributeError(name)
                if name[:1].isupper():
                    value = type(name, (), {"__init__": lambda self, *args, **kwargs: None})
                else:
                    value = lambda *args, **kwargs: None
                setattr(self, name, value)
                return value

        ok = _OkModule("ok")

        class BaseTask:
            pass

        class BaseScene:
            pass

        class Logger:
            @staticmethod
            def get_logger(_name):
                class _Silent:
                    def debug(self, *_args, **_kwargs):
                        pass

                    info = warning = error = debug

                return _Silent()

        ok.BaseTask = BaseTask
        ok.BaseScene = BaseScene
        ok.Logger = Logger
        ok.find_boxes_by_name = lambda *_args, **_kwargs: None
        ok.og = types.SimpleNamespace(my_app=types.SimpleNamespace(logged_in=False))
        ok.find_color_rectangles = lambda *_args, **_kwargs: []
        ok.mask_white = lambda *_args, **_kwargs: None

        class Box:
            pass

        class CannotFindException(Exception):
            pass

        ok.Box = Box
        ok.CannotFindException = CannotFindException
        ok.color_range_to_bound = lambda *args, **kwargs: None
        ok.safe_get = lambda *args, **kwargs: None
        ok.calculate_color_percentage = lambda *args, **kwargs: 0
        ok.TaskDisabledException = type("TaskDisabledException", (Exception,), {})
        ok.get_mask_in_color_range = lambda *args, **kwargs: None
        ok.is_pure_black = lambda *args, **kwargs: False
        ok.Config = type("Config", (), {"__init__": lambda self, *a, **k: None})

        class _IconMeta(type):
            def __getattr__(cls, name):
                return name

        ok.Icon = _IconMeta("Icon", (), {})
        ok.__path__ = []
        sys.modules["ok"] = ok

        class _OkLoader:
            def create_module(self, spec):
                module = _OkModule(spec.name)
                module.__path__ = []
                module.__package__ = spec.name
                if spec.name == "ok.util.GlobalConfig":
                    module.create_basic_options = lambda *args, **kwargs: None
                if spec.name.endswith(".config") or spec.name.endswith("GlobalConfig"):
                    module.Config = ok.Config
                return module

            def exec_module(self, module):
                return None

        class _OkFinder:
            def find_spec(self, fullname, path, target=None):
                if fullname.startswith("ok.") and fullname not in sys.modules:
                    return importlib.machinery.ModuleSpec(fullname, _OkLoader(), is_package=True)
                return None

        sys.meta_path.insert(0, _OkFinder())
    if importlib.util.find_spec("win32api") is None:
        sys.modules["win32api"] = types.ModuleType("win32api")
    if importlib.util.find_spec("cv2") is None:
        sys.modules["cv2"] = types.ModuleType("cv2")
    if importlib.util.find_spec("numpy") is None:
        numpy = types.ModuleType("numpy")
        numpy.uint8 = "uint8"
        numpy.array = lambda data, dtype=None: data
        sys.modules["numpy"] = numpy


_install_missing_import_stubs()
from src.task.BaseWWTask import BaseWWTask  # noqa: E402


class WorldStateTest(unittest.TestCase):
    def _task(self):
        task = BaseWWTask.__new__(BaseWWTask)
        task.treat_as_not_in_realm = False
        task.icons = {}
        task.find_one = lambda name, **_kwargs: task.icons.get(name)
        return task

    def test_realm_and_world_use_the_team_flag_not_the_tuple(self):
        task = self._task()
        task.icons["illusive_realm_exit"] = object()
        task.in_team = lambda: (False, -1, 0)
        self.assertFalse(task.in_realm())

        task.in_team = lambda: (True, 0, 3)
        self.assertTrue(task.in_realm())

        task.icons.clear()
        task.icons["world_earth_icon"] = object()
        task.in_team = lambda: (False, -1, 0)
        self.assertFalse(task.in_world())

        task.in_team = lambda: (True, 0, 3)
        self.assertTrue(task.in_world())

    def _prepare_main_task(self):
        from src.task.BaseWWTask import CannotFindException, og

        if getattr(og, "my_app", None) is None:
            og.my_app = types.SimpleNamespace(logged_in=False)
        task = self._task()
        task.tr = lambda message: message
        task.info_set = lambda *_args, **_kwargs: None
        task.sleep = lambda *_args, **_kwargs: None
        task.send_key = lambda *_args, **_kwargs: None
        task.click = lambda *_args, **_kwargs: None
        task.back = lambda *_args, **_kwargs: None
        task.log_debug = lambda *_args, **_kwargs: None
        task.budgets = []

        def wait_until(predicate, time_out=0, raise_if_not_found=False, **_kwargs):
            task.budgets.append(time_out)
            result = False
            for _ in range(3):
                result = predicate()
                if result:
                    return result
            if raise_if_not_found:
                raise TimeoutError(f"timeout {time_out}")
            return None

        task.wait_until = wait_until
        task.CannotFindException = CannotFindException
        return task

    def test_missing_exit_confirm_raises_without_a_long_wait(self):
        from src.task.BaseWWTask import CannotFindException

        task = self._prepare_main_task()
        task.logged_in = True
        task.in_team_and_world = lambda: True
        task.in_realm = lambda: True
        task.in_team = lambda: (True, 0, 3)
        task.wait_click_feature = lambda *_args, **_kwargs: None
        task.find_one = lambda *_args, **_kwargs: None

        with self.assertRaises(CannotFindException):
            task.ensure_main(time_out=10)

        self.assertEqual([10], task.budgets)

    def test_dialog_confirm_is_used_when_domain_button_is_absent(self):
        task = self._prepare_main_task()
        task.logged_in = True
        task.in_team_and_world = lambda: True
        task.in_realm = lambda: True
        task.in_team = lambda: (True, 0, 3)
        task.wait_click_feature = lambda *_args, **_kwargs: None
        clicked = []
        task.find_one = lambda *_args, **_kwargs: object()
        task.click = lambda *args, **kwargs: clicked.append(args)

        with self.assertRaises(Exception) as caught:
            task.ensure_main(time_out=10)

        self.assertIn("Please start in game world and in team!", str(caught.exception))
        self.assertTrue(clicked)
        self.assertEqual([10], task.budgets)

    def test_domain_button_is_accepted_and_outer_timeout_still_applies(self):
        task = self._prepare_main_task()
        task.logged_in = True
        task.in_team_and_world = lambda: True
        task.in_realm = lambda: True
        task.in_team = lambda: (True, 0, 3)
        clicks = []
        task.wait_click_feature = lambda *_args, **_kwargs: clicks.append("gray") or object()
        task.click_dialog_right_button = lambda: clicks.append("dialog")

        with self.assertRaises(Exception) as caught:
            task.ensure_main(time_out=10)

        self.assertIn("Please start in game world and in team!", str(caught.exception))
        self.assertEqual(["gray"], clicks)
        self.assertEqual([10], task.budgets)

    def test_explicit_timeout_reaches_ensure_main_outside_a_domain(self):
        task = self._task()
        seen = {}

        def ensure_main(time_out=30, esc=True):
            seen["time_out"] = time_out
            seen["esc"] = esc

        task.in_realm = lambda: False
        task.ensure_main = ensure_main

        task.make_sure_in_world(time_out=180)

        self.assertEqual(180, seen["time_out"])

    def test_domain_wait_uses_teleport_timeout_and_reports_failure(self):
        task = self._task()
        task.teleport_timeout = 100
        task.in_realm = lambda: True
        task.in_team = lambda: (True, 0, 3)
        task.send_key = lambda *_args, **_kwargs: None
        task.wait_click_feature = lambda *_args, **_kwargs: None
        task.tr = lambda message: message

        def wait_until(predicate, time_out=0, raise_if_not_found=False, **_kwargs):
            self.assertEqual(100, time_out)
            self.assertTrue(raise_if_not_found)
            self.assertFalse(predicate())
            raise TimeoutError("still in domain")

        task.wait_until = wait_until

        with self.assertRaises(TimeoutError):
            task.make_sure_in_world()

    def test_logged_out_startup_still_extends_the_main_wait(self):
        task = self._prepare_main_task()
        from src.task.BaseWWTask import og

        og.my_app.logged_in = False
        task.in_team_and_world = lambda: False
        task.in_realm = lambda: False
        task.wait_login = lambda: False
        task.handle_monthly_card = lambda: False

        with self.assertRaises(Exception) as caught:
            task.ensure_main(time_out=180)

        self.assertIn("Please start in game world and in team!", str(caught.exception))
        self.assertEqual([600], task.budgets)

    def test_open_world_startup_still_uses_ensure_main(self):
        task = self._task()
        task.in_realm = lambda: False
        called = []
        task.ensure_main = lambda *_args, **_kwargs: called.append(True)

        task.make_sure_in_world()

        self.assertEqual([True], called)

    def test_tacet_daily_and_nightmare_keep_their_startup_budgets(self):
        from src.task.DailyTask import DailyTask
        from src.task.NightmareNestTask import NightmareNestTask
        from src.task.TacetTask import TacetTask
        from src.task.WWOneTimeTask import WWOneTimeTask

        original_parent = WWOneTimeTask.run
        WWOneTimeTask.run = lambda self: None
        try:
            tacet = TacetTask.__new__(TacetTask)
            tacet_calls = []
            tacet.make_sure_in_world = lambda time_out=None: tacet_calls.append(("world", time_out))
            tacet.wait_in_team_and_world = lambda esc=False: tacet_calls.append(("team", esc))
            tacet.farm_tacet = lambda: tacet_calls.append("farm")
            tacet.run()
            self.assertEqual([("world", 180), ("team", True), "farm"], tacet_calls)

            daily = DailyTask.__new__(DailyTask)
            daily.validate_additional_tasks = lambda: None
            daily.make_sure_in_world = lambda time_out=None: (_ for _ in ()).throw(
                RuntimeError(f"world:{time_out}")
            )
            with self.assertRaises(RuntimeError) as caught:
                daily.run()
            self.assertEqual("world:180", str(caught.exception))

            for method_name in ("run", "run_capture_mode"):
                nest = NightmareNestTask.__new__(NightmareNestTask)
                nest._capture_mode = False
                nest._capture_success = False
                nest._unreachable_nests = set()
                nest._nest_deaths = {}
                nest.make_sure_in_world = lambda time_out=None: (_ for _ in ()).throw(
                    RuntimeError(f"world:{time_out}")
                )
                with self.assertRaises(RuntimeError) as caught:
                    getattr(nest, method_name)()
                self.assertEqual("world:30", str(caught.exception))
        finally:
            WWOneTimeTask.run = original_parent
