# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

import unittest

from opendcc import cmds


class TestCommands(unittest.TestCase):
    COMMAND_NAME = "test_python_registration"

    def register_echo(self):
        calls = []

        class Echo(cmds.Command):
            def execute(self, text, *, repeat=1):
                calls.append((text, repeat))
                return cmds.CommandResult(cmds.SUCCESS, text * repeat)

        cmds.Registry.register_command(self.COMMAND_NAME, "str", ("str",), {"repeat": "int"}, Echo)
        self.addCleanup(cmds.Registry.unregister_command, self.COMMAND_NAME)
        return calls

    def test_register_call_and_unregister(self):
        calls = self.register_echo()
        function = getattr(cmds, self.COMMAND_NAME)
        result = function("hello", repeat=2)
        self.assertTrue(result.is_successful())
        self.assertEqual(result.get_status(), cmds.SUCCESS)
        self.assertEqual(result.get_result(), "hellohello")
        self.assertEqual(function("hello").get_result(), "hello")
        self.assertEqual(calls, [("hello", 2), ("hello", 1)])
        self.doCleanups()
        self.assertFalse(hasattr(cmds, self.COMMAND_NAME))
        with self.assertRaises(TypeError):
            function("hello")

    def test_invalid_arguments_do_not_execute(self):
        calls = self.register_echo()
        function = getattr(cmds, self.COMMAND_NAME)
        for case, arguments, options in (
            ("missing text", (), {}),
            ("extra positional argument", ("hello", "extra"), {}),
            ("invalid text type", (object(),), {}),
            ("unknown option", ("hello",), {"unknown": 1}),
            ("invalid repeat type", ("hello",), {"repeat": object()}),
        ):
            with self.subTest(case=case):
                with self.assertRaises(TypeError):
                    function(*arguments, **options)
        self.assertEqual(calls, [])

    def test_unknown_converter_rejects_registration(self):
        for parameter, result_type, arguments, options in (
            ("result", "test.unknown_type", (), {}),
            ("positional argument", None, ("test.unknown_type",), {}),
            ("keyword argument", None, (), {"option": "test.unknown_type"}),
        ):
            with self.subTest(parameter=parameter):
                with self.assertRaises(TypeError):
                    cmds.Registry.register_command(
                        self.COMMAND_NAME, result_type, arguments, options, lambda: None
                    )
                self.assertFalse(hasattr(cmds, self.COMMAND_NAME))

    def test_command_without_arguments_or_result(self):
        class NoResult(cmds.Command):
            def execute(self):
                return cmds.CommandResult(cmds.SUCCESS)

        cmds.Registry.register_command(self.COMMAND_NAME, None, (), {}, NoResult)
        self.addCleanup(cmds.Registry.unregister_command, self.COMMAND_NAME)
        result = getattr(cmds, self.COMMAND_NAME)()
        self.assertTrue(result.is_successful())
        self.assertIsNone(result.get_result())


if __name__ == "__main__":
    unittest.main()
