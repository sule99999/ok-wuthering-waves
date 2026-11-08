"""Realm detection must use the team flag, and Daily Task must leave a domain first."""

import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _install_missing_import_stubs():
    """Let this check import the task module where Windows-only packages are absent."""
    if importlib.util.find_spec("ok") is None:
        ok = types.ModuleType("ok")

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
        ok.og = types.SimpleNamespace()
        ok.find_color_rectangles = lambda *_args, **_kwargs: []
        ok.mask_white = lambda *_args, **_kwargs: None

        class Box:
            pass

        class CannotFindException(Exception):
            pass

        ok.Box = Box
        ok.CannotFindException = CannotFindException
        sys.modules["ok"] = ok
    if importlib.util.find_spec("cv2") is None:
        sys.modules["cv2"] = types.ModuleType("cv2")
    if importlib.util.find_spec("numpy") is None:
        numpy = types.ModuleType("numpy")
        numpy.uint8 = "uint8"
        numpy.array = lambda data, dtype=None: data
        sys.modules["numpy"] = numpy


_install_missing_import_stubs()
from src.task.BaseWWTask import BaseWWTask  # noqa: E402


def _function(path, class_name, function_name):
    module = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    class_node = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == function_name)


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

    def test_domain_exit_waits_until_the_realm_flag_clears(self):
        task = self._task()
        task.teleport_timeout = 12
        task.in_realm_value = True
        task.in_realm = lambda: task.in_realm_value
        task.in_team = lambda: (True, 0, 3)
        events = []
        task.send_key = lambda *_args, **_kwargs: events.append("esc")

        def click(*_args, **_kwargs):
            events.append("exit")
            task.in_realm_value = False

        task.wait_click_feature = click
        seen_timeouts = []

        def wait_until(predicate, time_out=None, **_kwargs):
            seen_timeouts.append(time_out)
            self.assertTrue(predicate())

        task.wait_until = wait_until
        task.ensure_main = lambda *_args, **_kwargs: events.append("ensure")

        task.make_sure_in_world()

        self.assertEqual(["esc", "exit"], events)
        self.assertEqual([12], seen_timeouts)

    def test_open_world_startup_still_uses_ensure_main(self):
        task = self._task()
        task.in_realm = lambda: False
        called = []
        task.ensure_main = lambda *_args, **_kwargs: called.append(True)

        task.make_sure_in_world()

        self.assertEqual([True], called)

    def test_daily_task_leaves_a_domain_before_opening_the_guidebook(self):
        run_node = _function("src/task/DailyTask.py", "DailyTask", "run")
        ordered = [
            node.func.attr
            for node in sorted(
                (
                    node for node in ast.walk(run_node)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "self"
                    and node.func.attr in {"make_sure_in_world", "open_daily"}
                ),
                key=lambda node: node.lineno,
            )
        ]

        self.assertLess(ordered.index("make_sure_in_world"), ordered.index("open_daily"))
