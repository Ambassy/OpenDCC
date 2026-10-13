# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import os
import sys

import opendcc.core as core

app = core.Application.instance()
expected = Path(sys.argv[1]).resolve()
assert Path(app.get_settings_path()).resolve() == expected, app.get_settings_path()
assert app.get_settings_path().endswith("/")
assert app.get_settings().get_string("test.isolation", "missing") == "missing"
app.get_settings().set_string("test.isolation", "isolated")
assert (expected / "settings.json").is_file()
os.environ["OPENDCC_SETTINGS_DIR"] = str(expected / "changed after initialization")
assert Path(app.get_settings_path()).resolve() == expected
assert not (expected / "changed after initialization").exists()
print("isolated settings written", flush=True)
