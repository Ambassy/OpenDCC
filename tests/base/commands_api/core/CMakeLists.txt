opendcc_add_cpp_test(
    CommandBlockTests
    SOURCE
    test_block.cpp
    TARGET
    commands_api
    SUITES
    "CommandBlock/UndoCommandBlock")

opendcc_add_cpp_test(
    CommandRegistryTests
    SOURCE
    test_command_registry.cpp
    TARGET
    commands_api
    SUITES
    CommandRegistry)
