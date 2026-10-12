# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import os

import OpenImageIO as oiio
from Qt import QtCore, QtWidgets
from pxr import Gf, Sdf, Usd, UsdGeom
import opendcc.core as core
from image_utils import ImageDiffingTestCase, compare_images
from viewport_color_utils import (
    FRAME_SIZE,
    CAMERA_APERTURE,
    CAMERA_DISTANCE,
    CUBE_SAMPLE,
    BACKGROUND_INSET,
    BACKGROUND_SAMPLES,
    GRADIENT_ROWS,
    DEFAULT_BACKGROUND,
    DEFAULT_SELECTION_COLOR,
    OCIO_BACKGROUND,
    GRADIENT_DISABLED_BACKGROUND,
    SOLID_COLORS,
    GRADIENT_COLORS,
    SELECTION_COLORS,
    RED_SELECTION,
    BLUE_SELECTION,
    HALF_ALPHA_SELECTION,
    TRANSPARENT_SELECTION,
    MIN_HIGHLIGHT_PIXELS,
    HIGHLIGHT_CHANNEL_MIN,
    OTHER_CHANNEL_MAX,
    LINEAR_SPACE,
    SRGB_SPACE,
    OCIO_DISPLAY_SCALE,
    OCIO_DISPLAY_OFFSET,
    rgb_color,
    sample_rgb,
    color_matches,
    gradient_color,
)


class TestViewportColors(ImageDiffingTestCase):
    def setUp(self):
        self.app = core.Application.instance()
        self.assertEqual(
            Path(self.app.get_settings_path()).resolve(),
            Path(os.environ["OPENDCC_SETTINGS_DIR"]).resolve(),
        )
        self.settings = self.app.get_settings()
        for name, kind, default in (
            ("viewport.grid.enable", "bool", True),
            ("viewport.show_camera", "bool", True),
            ("viewport.background.gradient_enable", "bool", False),
            ("viewport.background.color", "double_array", [0.3] * 3),
            ("viewport.background.gradient_top", "double_array", [1] * 3),
            ("viewport.background.gradient_bottom", "double_array", [0] * 3),
            ("viewport.selection_color", "double_array", DEFAULT_SELECTION_COLOR),
            ("colormanagement.color_management", "string", "openColorIO"),
            ("colormanagement.ocio_rendering_space", "string", ""),
            ("colormanagement.ocio_view_transform", "string", ""),
        ):
            value = getattr(self.settings, "get_" + kind)(name, default)
            self.addCleanup(getattr(self.settings, "set_" + kind), name, value)
        self.addCleanup(self.app.set_selection_mode, self.app.get_selection_mode())
        self.app.set_current_viewport_tool(None)
        self.app.clear_prim_selection()
        self.app.set_selection_mode(core.Application.SelectionMode.PRIMS)
        self.settings.set_bool("viewport.grid.enable", False)
        self.settings.set_bool("viewport.show_camera", False)
        self.settings.set_bool("viewport.background.gradient_enable", False)
        self.settings.set_string("colormanagement.color_management", "sRGB")
        self.settings.set_string("colormanagement.ocio_rendering_space", "fixture_linear")
        self.settings.set_string("colormanagement.ocio_view_transform", "FixtureView")
        self.stage = Usd.Stage.CreateInMemory()
        UsdGeom.Cube.Define(self.stage, "/Cube")
        camera = UsdGeom.Camera.Define(self.stage, "/Camera")
        camera.CreateProjectionAttr(UsdGeom.Tokens.orthographic)
        camera.CreateHorizontalApertureAttr(CAMERA_APERTURE)
        camera.CreateVerticalApertureAttr(CAMERA_APERTURE)
        camera.AddTranslateOp().Set(Gf.Vec3d(0, 0, CAMERA_DISTANCE))
        self.app.get_session().set_current_stage(self.stage)
        self.addCleanup(self.app.get_session().close_stage, self.stage)
        self.addCleanup(self.app.clear_prim_selection)
        self.widget = core.ViewportWidget(self.app.get_main_window())
        self.addCleanup(self.widget.deleteLater)
        self.addCleanup(self.widget.close)
        self.widget.setWindowFlags(QtCore.Qt.Window)
        self.widget.show()
        self.view = self.widget.get_viewport_view()
        self.view.get_widget().setFixedSize(FRAME_SIZE, FRAME_SIZE)
        self.view.look_through(camera.GetPath())
        QtCore.QCoreApplication.processEvents()

    def assert_color_reference(self, name, reference=None):
        reference_path = (
            Path(__file__).parent / "baseline" / "colors" / ((reference or name) + ".png")
        )
        self.assert_images_close(reference_path, name + ".png")

    def capture_color(self, name, color):
        image = self.capture_viewport(
            self.view,
            name + ".png",
            lambda image: color_matches(image, BACKGROUND_SAMPLES[0], color)
            and sample_rgb(image, CUBE_SAMPLE)
            != sample_rgb(image, (BACKGROUND_INSET, CUBE_SAMPLE[1])),
        )
        for x, y in BACKGROUND_SAMPLES + ((BACKGROUND_INSET, CUBE_SAMPLE[1]),):
            self.assertTrue(color_matches(image, (x, y), color), (x, y, image.getpixel(x, y)))
        return image

    def test_solid_background_live_updates(self):
        for index, color in enumerate(SOLID_COLORS):
            with self.subTest(color=color):
                self.settings.set_double_array("viewport.background.color", color.GetRGB())
                self.capture_color("solid_" + str(index), color)
                if color in (DEFAULT_BACKGROUND, OCIO_BACKGROUND):
                    self.assert_color_reference("solid_" + str(index))

    def test_gradient_direction_interpolation_updates_and_toggle(self):
        solid = GRADIENT_DISABLED_BACKGROUND
        self.settings.set_double_array("viewport.background.color", solid.GetRGB())
        for index, (top, bottom) in enumerate(GRADIENT_COLORS):
            self.settings.set_double_array("viewport.background.gradient_top", top.GetRGB())
            self.settings.set_double_array("viewport.background.gradient_bottom", bottom.GetRGB())
            self.settings.set_bool("viewport.background.gradient_enable", True)

            def expected(y):
                return gradient_color(top, bottom, y)

            image = self.capture_viewport(
                self.view,
                "gradient_" + str(index) + ".png",
                lambda image: color_matches(
                    image, BACKGROUND_SAMPLES[0], expected(BACKGROUND_INSET)
                )
                and sample_rgb(image, CUBE_SAMPLE)
                != sample_rgb(image, (BACKGROUND_INSET, CUBE_SAMPLE[1])),
            )
            for y in GRADIENT_ROWS:
                for x in (BACKGROUND_INSET, FRAME_SIZE - BACKGROUND_INSET):
                    self.assertTrue(
                        color_matches(image, (x, y), expected(y)),
                        (x, y, image.getpixel(x, y), expected(y)),
                    )
            self.assert_color_reference("gradient_" + str(index))
        self.settings.set_bool("viewport.background.gradient_enable", False)
        self.capture_color("gradient_disabled", solid)
        self.assert_color_reference("gradient_disabled")
        self.settings.set_double_array("viewport.background.gradient_top", solid.GetRGB())
        self.settings.set_double_array("viewport.background.gradient_bottom", solid.GetRGB())
        self.settings.set_bool("viewport.background.gradient_enable", True)
        self.capture_color("gradient_equal_endpoints", solid)
        self.assert_color_reference("gradient_equal_endpoints", "gradient_disabled")

    def test_selection_rgb_alpha_and_clear(self):
        self.settings.set_double_array("viewport.background.color", DEFAULT_BACKGROUND.GetRGB())
        baseline = self.capture_viewport(
            self.view,
            "selection_baseline.png",
            lambda image: sample_rgb(image, CUBE_SAMPLE)
            != sample_rgb(image, BACKGROUND_SAMPLES[0]),
        )
        self.assert_color_reference("selection_baseline")
        self.app.set_prim_selection([Sdf.Path("/Cube")])
        for name, color, channel in SELECTION_COLORS:
            self.settings.set_double_array("viewport.selection_color", color)
            image = self.capture_viewport(
                self.view,
                "selection_" + name + ".png",
                lambda image: image.getpixel(*CUBE_SAMPLE)[channel] > HIGHLIGHT_CHANNEL_MIN
                and min(sample_rgb(image, CUBE_SAMPLE)) < OTHER_CHANNEL_MAX,
            )
            self.assertGreater(compare_images(baseline, image).nfail, MIN_HIGHLIGHT_PIXELS)
            self.assertTrue(color_matches(image, BACKGROUND_SAMPLES[0], DEFAULT_BACKGROUND))
            self.assert_color_reference("selection_" + name)
        self.settings.set_double_array("viewport.selection_color", HALF_ALPHA_SELECTION)
        half_reference = image
        half = self.capture_viewport(
            self.view,
            "selection_half_alpha.png",
            lambda image: compare_images(image, baseline).nfail > MIN_HIGHLIGHT_PIXELS
            and compare_images(image, half_reference).nfail > MIN_HIGHLIGHT_PIXELS,
        )
        self.assertLess(half.getpixel(*CUBE_SAMPLE)[2], half_reference.getpixel(*CUBE_SAMPLE)[2])
        self.assert_color_reference("selection_half_alpha")

        for channel in (0, 1):
            self.assertGreater(
                half.getpixel(*CUBE_SAMPLE)[channel], half_reference.getpixel(*CUBE_SAMPLE)[channel]
            )
            self.assertLess(
                half.getpixel(*CUBE_SAMPLE)[channel], baseline.getpixel(*CUBE_SAMPLE)[channel]
            )
        self.settings.set_double_array("viewport.selection_color", TRANSPARENT_SELECTION)
        self.capture_viewport(
            self.view,
            "selection_zero_alpha.png",
            lambda image: compare_images(image, baseline).nfail == 0,
        )
        self.assert_color_reference("selection_zero_alpha", "selection_baseline")
        self.settings.set_double_array("viewport.selection_color", RED_SELECTION)
        self.app.clear_prim_selection()
        self.capture_viewport(
            self.view,
            "selection_cleared.png",
            lambda image: compare_images(image, baseline).nfail == 0,
        )
        self.assert_color_reference("selection_cleared", "selection_baseline")

    def test_ocio_selection_color_live_updates(self):
        spaces, views, default_space, default_view = self.app.get_ocio_config()
        self.assertEqual(set(spaces), {"fixture_linear", "fixture_half", "fixture_display"})
        self.assertEqual(list(views), ["FixtureView", "Raw"])
        self.assertEqual(default_space, "fixture_linear")
        self.assertEqual(default_view, "FixtureView")

        def transformed_reference(name):
            path = Path(__file__).parent / "baseline" / "colors" / (name + ".png")
            image = oiio.ImageBuf(str(path))
            self.assertTrue(image.read(), image.geterror())
            linear = Gf.Color(rgb_color(sample_rgb(image, CUBE_SAMPLE), SRGB_SPACE), LINEAR_SPACE)
            return rgb_color(linear.GetRGB() * OCIO_DISPLAY_SCALE + OCIO_DISPLAY_OFFSET)

        self.view.set_color_mode("openColorIO")
        self.settings.set_double_array("viewport.background.color", OCIO_BACKGROUND.GetRGB())
        expected = transformed_reference("selection_baseline")
        self.capture_viewport(
            self.view,
            "ocio_unselected.png",
            lambda image: color_matches(image, CUBE_SAMPLE, expected),
        )
        self.capture_color("ocio_background", OCIO_BACKGROUND)
        self.assert_color_reference("ocio_background")
        self.app.set_prim_selection([Sdf.Path("/Cube")])
        for name, color in (
            ("red", RED_SELECTION),
            ("blue", BLUE_SELECTION),
            ("half_alpha", HALF_ALPHA_SELECTION),
        ):
            self.settings.set_double_array("viewport.selection_color", color)
            expected = transformed_reference("selection_" + name)
            self.capture_viewport(
                self.view,
                "ocio_selection_" + name + ".png",
                lambda image: color_matches(image, CUBE_SAMPLE, expected),
            )
            self.assert_color_reference("ocio_selection_" + name)
        self.app.clear_prim_selection()
        expected = transformed_reference("selection_baseline")
        self.capture_viewport(
            self.view,
            "ocio_selection_cleared.png",
            lambda image: color_matches(image, CUBE_SAMPLE, expected),
        )
        self.assert_color_reference("ocio_selection_cleared", "ocio_background")

        top, bottom = GRADIENT_COLORS[0]
        self.settings.set_double_array("viewport.background.gradient_top", top.GetRGB())
        self.settings.set_double_array("viewport.background.gradient_bottom", bottom.GetRGB())
        self.settings.set_bool("viewport.background.gradient_enable", True)
        self.capture_viewport(
            self.view,
            "ocio_gradient.png",
            lambda image: color_matches(image, CUBE_SAMPLE, expected)
            and color_matches(
                image, BACKGROUND_SAMPLES[0], gradient_color(top, bottom, BACKGROUND_INSET)
            ),
        )
        self.assert_color_reference("ocio_gradient")
