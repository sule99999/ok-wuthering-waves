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

    def _clocked_task(self, realm_clears_at=None, task_class=None):
        from src.task.BaseWWTask import og

        if getattr(og, "my_app", None) is None:
            og.my_app = types.SimpleNamespace(logged_in=False)
        task_class = task_class or BaseWWTask
        task = task_class.__new__(task_class)
        task.tr = lambda message: message
        task.info_set = lambda *_args, **_kwargs: None
        task.sleep = lambda *_args, **_kwargs: None
        task.send_key = lambda *_args, **_kwargs: None
        task.back = lambda *_args, **_kwargs: None
        task.log_debug = lambda *_args, **_kwargs: None
        task.logged_in = True
        task.clock = 0
        task.budgets = []
        task.clicks = []
        task.in_team_and_world = lambda: True
        task.in_team = lambda: (True, 0, 3)

        def in_realm():
            return realm_clears_at is None or task.clock < realm_clears_at

        task.in_realm = in_realm

        def wait_until(predicate, time_out=0, raise_if_not_found=False, **_kwargs):
            task.budgets.append(time_out)
            started = task.clock
            while task.clock - started <= time_out:
                result = predicate()
                if result:
                    return result
                task.clock += 1
            if raise_if_not_found:
                raise TimeoutError(f"timeout {time_out}")
            return None

        task.wait_until = wait_until
        return task

    def test_missing_exit_confirm_raises_without_waiting_out_the_load(self):
        from src.task.BaseWWTask import CannotFindException

        task = self._clocked_task()
        task.wait_click_feature = lambda *_args, **_kwargs: None
        task.find_one = lambda *_args, **_kwargs: None

        with self.assertRaises(CannotFindException):
            task.make_sure_in_world(time_out=30)

        self.assertEqual([], [budget for budget in task.budgets if budget >= 100])
        self.assertEqual(0, task.clock)

    def test_dialog_only_exit_survives_past_the_menu_timeout(self):
        task = self._clocked_task(realm_clears_at=45)
        task.wait_click_feature = lambda *_args, **_kwargs: None
        task.find_one = lambda *_args, **_kwargs: object()
        task.click = lambda *args, **_kwargs: task.clicks.append(args)

        task.make_sure_in_world(time_out=30)

        self.assertTrue(task.clicks)
        self.assertIn(120, task.budgets)
        self.assertNotIn(30, task.budgets)
        self.assertGreaterEqual(task.clock, 45)
        self.assertLess(task.clock, 120)
        self.assertFalse(task.in_realm())

    def test_domain_button_does_not_also_require_the_dialog(self):
        task = self._clocked_task(realm_clears_at=5)
        task.wait_click_feature = lambda *_args, **_kwargs: task.clicks.append("gray") or object()
        task.click_dialog_right_button = lambda: task.clicks.append("dialog")

        task.make_sure_in_world(time_out=30)

        self.assertEqual(["gray"], task.clicks)
        self.assertIn(120, task.budgets)

    def test_failed_exit_is_bounded_by_the_load_budget_not_the_menu_timeout(self):
        task = self._clocked_task()
        task.wait_click_feature = lambda *_args, **_kwargs: object()

        with self.assertRaises(TimeoutError) as caught:
            task.make_sure_in_world(time_out=30)

        self.assertIn("timeout 120", str(caught.exception))
        self.assertGreaterEqual(task.clock, 120)
        self.assertLess(task.clock, 140)

    def test_ensure_main_domain_exit_is_not_cut_off_by_its_menu_timeout(self):
        task = self._clocked_task(realm_clears_at=45)
        task.wait_click_feature = lambda *_args, **_kwargs: None
        task.find_one = lambda *_args, **_kwargs: object()
        task.click = lambda *args, **_kwargs: task.clicks.append("dialog")

        task.ensure_main(time_out=10)

        self.assertIn("dialog", task.clicks)
        self.assertIn(120, task.budgets)
        self.assertGreaterEqual(task.clock, 45)
        self.assertFalse(task.in_realm())

    def test_domain_task_load_budget_stays_at_teleport_timeout(self):
        task = self._clocked_task()
        task.teleport_timeout = 100
        task.wait_click_feature = lambda *_args, **_kwargs: object()

        with self.assertRaises(TimeoutError) as caught:
            task.make_sure_in_world()

        self.assertIn("timeout 100", str(caught.exception))
        self.assertNotIn(120, task.budgets)

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

    def test_logged_out_startup_still_extends_the_main_wait(self):
        from src.task.BaseWWTask import og

        task = self._clocked_task(realm_clears_at=0)
        og.my_app.logged_in = False
        task.logged_in = False
        task.in_team_and_world = lambda: False
        task.wait_login = lambda: False
        task.handle_monthly_card = lambda: False

        with self.assertRaises(Exception) as caught:
            task.ensure_main(time_out=180)

        self.assertIn("Please start in game world and in team!", str(caught.exception))
        self.assertIn(600, task.budgets)
        self.assertNotIn(180, task.budgets)

    def test_open_world_startup_still_uses_ensure_main(self):
        task = self._task()
        task.in_realm = lambda: False
        called = []
        task.ensure_main = lambda *_args, **_kwargs: called.append(True)

        task.make_sure_in_world()

        self.assertEqual([True], called)

    def test_startup_callers_use_the_real_exit_and_keep_menu_budgets(self):
        from src.task.DailyTask import DailyTask
        from src.task.NightmareNestTask import NightmareNestTask
        from src.task.TacetTask import TacetTask
        from src.task.WWOneTimeTask import WWOneTimeTask

        original_parent = WWOneTimeTask.run
        WWOneTimeTask.run = lambda self: None
        try:
            tacet = self._clocked_task(realm_clears_at=45, task_class=TacetTask)
            tacet.wait_click_feature = lambda *_args, **_kwargs: None
            tacet.find_one = lambda *_args, **_kwargs: object()
            tacet.click = lambda *args, **_kwargs: tacet.clicks.append("dialog")
            tacet.wait_in_team_and_world = lambda esc=False: tacet.clicks.append(("team", esc))
            tacet.farm_tacet = lambda: tacet.clicks.append("farm")
            TacetTask.run(tacet)
            self.assertIn("dialog", tacet.clicks)
            self.assertIn("farm", tacet.clicks)
            self.assertIn(120, tacet.budgets)
            self.assertGreaterEqual(tacet.clock, 45)

            open_world = self._clocked_task(realm_clears_at=0, task_class=TacetTask)
            seen = {}

            def ensure_main(time_out=30, esc=True):
                seen["time_out"] = time_out

            open_world.ensure_main = ensure_main
            open_world.in_realm = lambda: False
            open_world.farm_tacet = lambda: None
            open_world.wait_in_team_and_world = lambda esc=False: None
            TacetTask.run(open_world)
            self.assertEqual(180, seen["time_out"])

            nest = self._clocked_task(realm_clears_at=45, task_class=NightmareNestTask)
            nest._capture_mode = False
            nest._capture_success = False
            nest._unreachable_nests = set()
            nest._nest_deaths = {}
            nest.wait_click_feature = lambda *_args, **_kwargs: None
            nest.find_one = lambda *_args, **_kwargs: object()
            nest.click = lambda *args, **_kwargs: nest.clicks.append("dialog")
            nest._init_queue = lambda: nest.clicks.append("queue")
            nest.log_info = lambda *_args, **_kwargs: None
            nest.get_nest_to_go = lambda: None
            nest.ensure_main = lambda time_out=30, esc=True: nest.clicks.append(("menu", time_out))
            NightmareNestTask.run(nest)
            self.assertIn("dialog", nest.clicks)
            self.assertIn("queue", nest.clicks)
            self.assertIn(120, nest.budgets)
            self.assertGreaterEqual(nest.clock, 45)

            daily = self._clocked_task(realm_clears_at=45, task_class=DailyTask)
            daily.validate_additional_tasks = lambda: None
            daily.config = {}
            daily.wait_click_feature = lambda *_args, **_kwargs: None
            daily.find_one = lambda *_args, **_kwargs: object()
            daily.click = lambda *args, **_kwargs: daily.clicks.append("dialog")
            daily.open_daily = lambda: (_ for _ in ()).throw(RuntimeError("opened-after-exit"))
            with self.assertRaises(RuntimeError) as caught:
                DailyTask.run(daily)
            self.assertEqual("opened-after-exit", str(caught.exception))
            self.assertIn("dialog", daily.clicks)
            self.assertIn(120, daily.budgets)
            self.assertGreaterEqual(daily.clock, 45)
        finally:
            WWOneTimeTask.run = original_parent
