opendcc_add_cpp_test(
    CommandPythonBridgeTests
    SOURCE
    test_command_python_bridge.cpp
    TARGET
    py_commands_api
    SUITES
    CommandPythonBridge)
opendcc_add_python_test(CommandPythonTests SOURCE test_commands.py)
