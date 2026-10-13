# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
import sys

profile = Path(os.environ["OPENDCC_SETTINGS_DIR"])
assert profile.is_dir()
assert not (profile / "settings.json").exists()
(profile / "settings.json").write_text("test preferences")
print("PROFILE=" + str(profile), flush=True)
sys.exit(int(sys.argv[1]))
