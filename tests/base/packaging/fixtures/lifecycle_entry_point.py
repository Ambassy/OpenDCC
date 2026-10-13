# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from opendcc.packaging import PackageEntryPoint


def record(filename, event):
    with Path(filename).open("a", encoding="utf-8") as stream:
        stream.write(event + "\n")


class LifecycleEntryPoint(PackageEntryPoint):
    def initialize(self, package):
        self.filename = package.get_attribute("test.event_log")
        self.package_name = package.get_name()
        record(self.filename, "python:init:" + self.package_name)
        if package.get_attribute("test.fail_initialize"):
            raise RuntimeError("Python test initialization failed")

    def uninitialize(self, package):
        record(self.filename, "python:uninit:" + package.get_name())

    def __del__(self):
        if hasattr(self, "filename"):
            record(self.filename, "python:destroy:" + self.package_name)
