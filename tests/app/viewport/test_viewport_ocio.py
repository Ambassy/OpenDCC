# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import os

from Qt import QtCore, QtWidgets
from pxr import Gf, Usd, UsdGeom
import opendcc.core as core
from image_utils import ImageDiffingTestCase
from viewport_color_utils import (
    FRAME_SIZE,
    CAMERA_APERTURE,
    CAMERA_DISTANCE,
    CUBE_SAMPLE,
    BACKGROUND_SAMPLES,
    PIXEL_TOLERANCE,
    OCIO_BACKGROUND,
    LINEAR_SPACE,
    SRGB_SPACE,
    OCIO_DISPLAY_SCALE,
    OCIO_DISPLAY_OFFSET,
    OCIO_INPUT_SCALE,
    rgb_color,
    sample_rgb,
    color_matches,
)


class TestViewportOcio(ImageDiffingTestCase):
    def setUp(self):
        self.app = core.Application.instance()
        self.assertEqual(
            Path(self.app.get_settings_path()).resolve(),
            Path(os.environ["OPENDCC_SETTINGS_DIR"]).resolve(),
        )
        self.settings = self.app.get_settings()
        for name, kind, value in (
            ("viewport.grid.enable", "bool", False),
            ("viewport.show_camera", "bool", False),
            ("viewport.background.gradient_enable", "bool", False),
            ("viewport.background.color", "double_array", OCIO_BACKGROUND.GetRGB()),
            ("colormanagement.color_management", "string", "disabled"),
            ("colormanagement.ocio_rendering_space", "string", "fixture_linear"),
            ("colormanagement.ocio_view_transform", "string", "FixtureView"),
        ):
            setter = getattr(self.settings, "set_" + kind)
            previous = getattr(self.settings, "get_" + kind)(name, value)
            self.addCleanup(setter, name, previous)
            setter(name, value)
        spaces, views, default_space, default_view = self.app.get_ocio_config()
        self.assertEqual(set(spaces), {"fixture_linear", "fixture_half", "fixture_display"})
        self.assertEqual(list(views), ["FixtureView", "Raw"])
        self.assertEqual((default_space, default_view), ("fixture_linear", "FixtureView"))
        self.app.set_current_viewport_tool(None)
        self.app.clear_prim_selection()
        self.stage = Usd.Stage.CreateInMemory()
        UsdGeom.Cube.Define(self.stage, "/Cube")
        camera = UsdGeom.Camera.Define(self.stage, "/Camera")
        camera.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
        camera.CreateHorizontalApertureAttr(CAMERA_APERTURE)
        camera.CreateVerticalApertureAttr(CAMERA_APERTURE)
        camera.AddTranslateOp().Set(Gf.Vec3d(0, 0, CAMERA_DISTANCE))
        session = self.app.get_session()
        session.set_current_stage(self.stage)
        self.addCleanup(session.close_stage, self.stage)
        self.widget = core.ViewportWidget(self.app.get_main_window())
        self.addCleanup(self.widget.deleteLater)
        self.addCleanup(self.widget.close)
        self.widget.setWindowFlags(QtCore.Qt.Window)
        self.widget.show()
        self.view = self.widget.get_viewport_view()
        self.view.get_widget().setFixedSize(FRAME_SIZE, FRAME_SIZE)
        self.view.look_through(camera.GetPath())
        QtCore.QCoreApplication.processEvents()
        baseline = self.capture_viewport(
            self.view,
            "linear_baseline.png",
            lambda image: sample_rgb(image, CUBE_SAMPLE)
            != sample_rgb(image, BACKGROUND_SAMPLES[0]),
        )
        self.linear_color = rgb_color(sample_rgb(baseline, CUBE_SAMPLE), LINEAR_SPACE)
        self.view.set_color_mode("openColorIO")

    def expected_color(self, raw=False, input_scale=1, exposure=0, gamma=1):
        # Exposure is measured in stops; gamma applies after the fixture's display transform.
        linear = self.linear_color.GetRGB() * (input_scale * 2**exposure)
        display = linear if raw else linear * OCIO_DISPLAY_SCALE + OCIO_DISPLAY_OFFSET
        return rgb_color([value ** (1 / gamma) for value in display])

    def capture_color(self, name, expected, reference=None):
        image = self.capture_viewport(
            self.view, name + ".png", lambda image: color_matches(image, CUBE_SAMPLE, expected)
        )
        for point in BACKGROUND_SAMPLES:
            for actual, value in zip(sample_rgb(image, point), OCIO_BACKGROUND.GetRGB()):
                self.assertAlmostEqual(actual, value, delta=PIXEL_TOLERANCE)
        reference_path = (
            Path(__file__).parent / "baseline" / "ocio" / ((reference or name) + ".png")
        )
        self.assert_images_close(reference_path, name + ".png")

    def test_view_switch_and_restore(self):
        self.capture_color("default", self.expected_color())
        self.view.set_ocio_view("Raw")
        self.assertEqual(self.view.get_ocio_view(), "Raw")
        self.capture_color("raw", self.expected_color(raw=True))
        self.view.set_ocio_view("FixtureView")
        self.capture_color("view_restored", self.expected_color(), "default")

    def test_input_space_change_and_restore(self):
        self.capture_color("default", self.expected_color())
        self.view.set_input_color_space("fixture_half")
        self.assertEqual(self.view.get_input_color_space(), "fixture_half")
        self.capture_color("half_input", self.expected_color(input_scale=OCIO_INPUT_SCALE))
        self.view.set_input_color_space("fixture_linear")
        self.capture_color("input_restored", self.expected_color(), "default")

    def test_exposure_and_restore(self):
        for name, value in (
            ("exposure_minus_one", -1),
            ("exposure_plus_one", 1),
            ("exposure_restored", 0),
        ):
            self.view.set_exposure(value)
            self.assertEqual(self.view.get_exposure(), value)
            self.capture_color(
                name, self.expected_color(exposure=value), "default" if value == 0 else None
            )

    def test_gamma_and_combined_exposure(self):
        self.view.set_gamma(2)
        self.assertEqual(self.view.get_gamma(), 2)
        self.capture_color("gamma_two", self.expected_color(gamma=2))
        self.view.set_exposure(-1)
        self.capture_color("combined", self.expected_color(exposure=-1, gamma=2))
        self.view.set_gamma(1)
        self.view.set_exposure(0)
        self.capture_color("adjustments_restored", self.expected_color(), "default")

    def test_color_modes_and_restore(self):
        self.capture_color("default", self.expected_color())
        self.view.set_color_mode("disabled")
        self.assertEqual(self.view.get_color_mode(), "disabled")
        self.capture_color("disabled", self.linear_color)
        self.view.set_color_mode("sRGB")
        expected = Gf.Color(self.linear_color, SRGB_SPACE)
        self.capture_color("srgb", expected)
        self.view.set_color_mode("openColorIO")
        self.capture_color("mode_restored", self.expected_color(), "default")
