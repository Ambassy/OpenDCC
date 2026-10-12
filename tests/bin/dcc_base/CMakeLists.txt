opendcc_add_python_test(
    ApplicationCliTests
    SOURCE
    test_cli.py
    STANDALONE
    GUI
    ARGS
    "${_opendcc_test_binary}")

opendcc_add_python_test(ApplicationSettingsPathTests SOURCE test_settings_path.py STANDALONE ARGS
                        "${_opendcc_test_binary}")
