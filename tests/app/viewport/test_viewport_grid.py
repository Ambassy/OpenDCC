# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

import OpenImageIO as oiio
from Qt import QtCore
from pxr import Gf, Usd, UsdGeom
import opendcc.core as core
from image_utils import ImageDiffingTestCase, compare_images
from viewport_utils import project_to_viewport


class TestViewportGrid(ImageDiffingTestCase):
    def setUp(self):
        self.app = core.Application.instance()
        settings = self.app.get_settings()
        settings.set_bool("viewport.grid.enable", False)
        settings.set_double("viewport.grid.min_step", 1.0)
        settings.set_double_array("viewport.grid.lines_color", [0.8, 0.8, 0.8, 1.0])
        settings.set_double_array("viewport.background.color", [0.1, 0.1, 0.1])
        settings.set_bool("viewport.show_camera", False)
        self.app.set_current_viewport_tool(None)

        self.stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(self.stage, UsdGeom.Tokens.y)
        session = self.app.get_session()
        self.addCleanup(session.close_stage, self.stage)
        session.set_current_stage(self.stage)
        self.camera = UsdGeom.Camera.Define(self.stage, "/Camera")
        self.camera.CreateHorizontalApertureAttr(80)
        self.camera.CreateVerticalApertureAttr(80)
        self.camera.CreateClippingRangeAttr(Gf.Vec2f(0.1, 1000))
        self.camera_transform = self.camera.AddTransformOp()

        self.viewport = core.ViewportWidget()
        self.addCleanup(self.viewport.deleteLater)
        self.addCleanup(self.viewport.close)
        self.viewport.setWindowFlags(QtCore.Qt.Window)
        self.view = self.viewport.get_viewport_view()
        self.view.get_widget().setFixedSize(256, 256)
        self.set_camera()
        self.view.look_through(self.camera.GetPath())
        self.viewport.show()

    def set_camera(self, up_axis="Y", perspective=False, offset=0):
        UsdGeom.SetStageUpAxis(self.stage, up_axis)
        target = Gf.Vec3d(offset, 0, 0)
        if up_axis == "Y":
            eye = target + Gf.Vec3d(0, 10, 5 if perspective else 0)
            up = Gf.Vec3d(0, 0, -1)
        else:
            eye = target + Gf.Vec3d(0, 5 if perspective else 0, 10)
            up = Gf.Vec3d(0, 1, 0)
        projection = UsdGeom.Tokens.perspective if perspective else UsdGeom.Tokens.orthographic
        self.camera.GetProjectionAttr().Set(projection)
        self.camera_transform.Set(Gf.Matrix4d().SetLookAt(eye, target, up).GetInverse())

    def capture(self, name):
        return self.capture_viewport(self.view, name + ".png")

    def set_enabled(self, enabled):
        self.app.get_settings().set_bool("viewport.grid.enable", enabled)

    def pixel_delta(self, before, after, position):
        point = project_to_viewport(self.view, position)
        x, y = int(point[0]), int(point[1])
        self.assertGreaterEqual(x, 1)
        self.assertGreaterEqual(y, 1)
        self.assertLess(x, after.spec().width - 1)
        self.assertLess(y, after.spec().height - 1)
        # Search adjacent pixels because a projected grid line may straddle pixel centers.
        return max(
            abs(after.getpixel(px, py)[channel] - before.getpixel(px, py)[channel])
            for px in range(x - 1, x + 2)
            for py in range(y - 1, y + 2)
            for channel in range(3)
        )

    def test_enable_and_disable(self):
        disabled = self.capture("disabled")
        self.set_enabled(True)
        enabled = self.capture("enabled")
        self.assertGreater(compare_images(disabled, enabled).nfail, 100)
        self.assertGreater(self.pixel_delta(disabled, enabled, (1, 0, 0.5)), 0.05)
        self.assertLess(self.pixel_delta(disabled, enabled, (1.5, 0, 0.5)), 2 / 255)
        self.set_enabled(False)
        restored = self.capture("disabled_again")
        self.assertEqual(compare_images(disabled, restored).nfail, 0)

    def test_up_axis_and_projection(self):
        for up_axis in ("Y", "Z"):
            for perspective in (False, True):
                with self.subTest(up_axis=up_axis, perspective=perspective):
                    self.set_enabled(False)
                    self.set_camera(up_axis, perspective)
                    # The grid's up axis is refreshed when a stage becomes current.
                    self.app.get_session().set_current_stage(self.stage)
                    self.view.look_through(self.camera.GetPath())
                    name = "{}_{}".format(up_axis, "perspective" if perspective else "ortho")
                    disabled = self.capture(name + "_disabled")
                    self.set_enabled(True)
                    enabled = self.capture(name)
                    position = (1, 0, 0.5) if up_axis == "Y" else (1, 0.5, 0)
                    self.assertGreater(self.pixel_delta(disabled, enabled, position), 0.05)
                    self.assertGreater(compare_images(disabled, enabled).nfail, 100)

    def test_minimum_step_changes_line_spacing(self):
        disabled = self.capture("spacing_disabled")
        self.set_enabled(True)
        fine = self.capture("spacing_one")
        self.app.get_settings().set_double("viewport.grid.min_step", 2.0)
        coarse = self.capture("spacing_two")
        self.assertGreater(self.pixel_delta(disabled, fine, (1, 0, 0.5)), 0.05)
        self.assertLess(self.pixel_delta(disabled, coarse, (1, 0, 0.5)), 2 / 255)
        self.assertGreater(self.pixel_delta(disabled, coarse, (2, 0, 0.5)), 0.05)

    def test_grid_stays_anchored_to_world_when_camera_moves(self):
        self.set_camera(offset=0.375)
        disabled = self.capture("pan_disabled")
        self.set_enabled(True)
        enabled = self.capture("pan_enabled")
        self.assertGreater(self.pixel_delta(disabled, enabled, (1, 0, 0.5)), 0.05)
        self.assertLess(self.pixel_delta(disabled, enabled, (1.5, 0, 0.5)), 2 / 255)

    def test_color_and_alpha(self):
        disabled = self.capture("color_disabled")
        settings = self.app.get_settings()
        settings.set_double_array("viewport.grid.lines_color", [1, 0, 0, 1])
        self.set_enabled(True)
        red = self.capture("color_red")
        point = project_to_viewport(self.view, (1, 0, 0.5))
        pixels = [
            red.getpixel(x, y)
            for x in range(int(point[0]) - 1, int(point[0]) + 2)
            for y in range(int(point[1]) - 1, int(point[1]) + 2)
        ]
        self.assertGreater(max(pixel[0] - max(pixel[1:3]) for pixel in pixels), 0.1)
        settings.set_double_array("viewport.grid.lines_color", [1, 0, 0, 0])
        transparent = self.capture("color_transparent")
        self.assertEqual(compare_images(disabled, transparent).nfail, 0)

    def test_perspective_grid_fades_at_grazing_angle(self):
        self.set_camera(perspective=True)
        disabled = self.capture("angle_disabled")
        self.set_enabled(True)
        enabled = self.capture("angle_enabled")
        self.assertGreater(self.pixel_delta(disabled, enabled, (1, 0, 0.5)), 0.05)
        normal_error = compare_images(disabled, enabled).meanerror

        self.set_enabled(False)
        eye = Gf.Vec3d(0, 0.001, 10)
        self.camera_transform.Set(
            Gf.Matrix4d().SetLookAt(eye, Gf.Vec3d(0), Gf.Vec3d(0, 1, 0)).GetInverse()
        )
        disabled = self.capture("grazing_disabled")
        self.set_enabled(True)
        grazing = self.capture("grazing_enabled")
        # Allow residual antialiasing at the horizon, while requiring a strong fade.
        self.assertLess(compare_images(disabled, grazing).meanerror, normal_error / 100)

    def test_geometry_occludes_grid(self):
        mesh = UsdGeom.Mesh.Define(self.stage, "/Occluder")
        mesh.CreatePointsAttr([(-1.5, 1, -1.5), (-1.5, 1, 1.5), (1.5, 1, 1.5), (1.5, 1, -1.5)])
        mesh.CreateFaceVertexCountsAttr([4])
        mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        mesh.CreateDoubleSidedAttr(True)
        mesh.CreateDisplayColorAttr([Gf.Vec3f(0.8, 0.2, 0.2)])
        for perspective in (False, True):
            with self.subTest(perspective=perspective):
                self.set_enabled(False)
                self.set_camera(perspective=perspective)
                name = "occluded_" + ("perspective" if perspective else "ortho")
                disabled = self.capture_viewport(
                    self.view,
                    name + "_disabled.png",
                    lambda image: image.getpixel(128, 128)[:3] != image.getpixel(0, 0)[:3],
                )
                self.set_enabled(True)
                enabled = self.capture(name + "_enabled")
                interior = oiio.ROI(116, 140, 116, 140, 0, 1, 0, 3)
                self.assertEqual(compare_images(disabled, enabled, interior).nfail, 0)
                self.assertGreater(self.pixel_delta(disabled, enabled, (2, 0, 0.5)), 0.05)
