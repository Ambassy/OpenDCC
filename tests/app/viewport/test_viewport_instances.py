# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import OpenImageIO as oiio
from Qt import QtCore, QtWidgets
from pxr import Gf, Sdf, Usd
import opendcc.core as core
from image_utils import ImageDiffingTestCase, compare_images
from viewport_utils import project_to_viewport


class TestViewportInstances(ImageDiffingTestCase):
    VIEWPORT_SIZE = (400, 400)
    BACKGROUND_COLOR = [0.36, 0.36, 0.36]
    # Require a visible highlight, rather than a few antialiased edge pixels.
    MIN_HIGHLIGHT_PIXELS = 100

    @classmethod
    def setUpClass(cls):
        cls.widget = core.ViewportWidget(core.Application.instance().get_main_window())
        if not isinstance(cls.widget, QtWidgets.QWidget):
            raise TypeError("ViewportWidget must be a Qt widget")
        cls.addClassCleanup(cls.widget.deleteLater)
        cls.addClassCleanup(cls.widget.close)
        cls.widget.setWindowFlags(QtCore.Qt.Window)
        cls.widget.show()
        cls.view = cls.widget.get_viewport_view()
        QtCore.QCoreApplication.processEvents()

    def setUp(self):
        self.app = core.Application.instance()
        self.assertTrue(self.app.is_ui_available())
        previous_mode = self.app.get_selection_mode()
        self.addCleanup(self.app.set_selection_mode, previous_mode)
        self.app.set_selection_mode(core.Application.SelectionMode.INSTANCES)
        self.app.set_current_viewport_tool(None)
        self.view.get_widget().setFixedSize(*self.VIEWPORT_SIZE)
        QtCore.QCoreApplication.processEvents()
        fixture = Path(__file__).parent / "fixtures" / "point_instancer.usda"
        self.stage = Usd.Stage.Open(str(fixture))
        self.instance_positions = (
            self.stage.GetPrimAtPath("/Instances").GetAttribute("positions").Get()
        )
        self.assertEqual(len(self.instance_positions), 2)
        session = self.app.get_session()
        session.set_current_stage(self.stage)
        self.addCleanup(session.close_stage, self.stage)
        self.addCleanup(self.app.clear_prim_selection)
        self.app.clear_prim_selection()
        self.view.look_through(Sdf.Path("/Camera"))
        settings = self.app.get_settings()
        settings.set_bool("viewport.grid.enable", False)
        settings.set_bool("viewport.show_camera", False)
        settings.set_double_array("viewport.background.color", self.BACKGROUND_COLOR)
        self.instance_pick_mask = int(core.MergeFlags.INSTANCES)

    def capture_instances(self, filename):
        def instances_visible(image):
            # The fixture leaves the top-left corner clear of geometry.
            background_rgb = image.getpixel(0, 0)[:3]
            for position in self.instance_positions:
                screen_position = project_to_viewport(self.view, position)
                x, y = int(screen_position[0]), int(screen_position[1])
                if not (0 <= x < image.spec().width and 0 <= y < image.spec().height):
                    return False
                if image.getpixel(x, y)[:3] == background_rgb:
                    return False
            return True

        return self.capture_viewport(self.view, filename, instances_visible)

    def assert_selected_instances(self, selection, expected_indices):
        self.assertEqual(set(selection.get_selected_paths()), {Sdf.Path("/Instances")})
        data = selection[Sdf.Path("/Instances")]
        self.assertFalse(data.fully_selected)
        self.assertEqual(list(data.instance_indices), expected_indices)
        self.assertEqual(list(data.point_indices), [])
        self.assertEqual(list(data.element_indices), [])

    def capture_comparison(self, baseline, filename, ready):
        try:
            return self.capture_viewport(self.view, filename, ready)
        finally:
            path = Path(filename)
            if path.exists():
                actual = oiio.ImageBuf(str(path.resolve()))
                if actual.read(0, 0, True):
                    difference = oiio.ImageBufAlgo.abs(oiio.ImageBufAlgo.sub(baseline, actual))
                    difference_path = path.with_name(path.stem + ".diff.png")
                    self.assertTrue(difference.write(str(difference_path)), difference.geterror())

    def test_single_instance_picking_and_highlight(self):
        baseline = self.capture_instances("instances_unselected.png")
        width, height = baseline.spec().width, baseline.spec().height
        midpoint = width // 2
        # These are 2D RGB regions; exclude the framebuffer's alpha channel.
        left_half = oiio.ROI(0, midpoint, 0, height, 0, 1, 0, 3)
        right_half = oiio.ROI(midpoint, width, 0, height, 0, 1, 0, 3)
        for side, index, selected_region, neighbor_region in (
            ("left", 0, left_half, right_half),
            ("right", 1, right_half, left_half),
        ):
            with self.subTest(instance=side):
                selection = self.view.pick_single_prim(
                    project_to_viewport(self.view, self.instance_positions[index]),
                    self.instance_pick_mask,
                )
                self.assert_selected_instances(selection, [index])
                self.app.set_selection(selection)
                selected = self.capture_comparison(
                    baseline,
                    "instance_" + str(index) + "_selected.png",
                    lambda image: compare_images(baseline, image, selected_region).nfail
                    > self.MIN_HIGHLIGHT_PIXELS,
                )
                self.assertGreater(
                    compare_images(baseline, selected, selected_region).nfail,
                    self.MIN_HIGHLIGHT_PIXELS,
                )
                self.assertEqual(compare_images(baseline, selected, neighbor_region).nfail, 0)
                self.app.clear_prim_selection()
                cleared = self.capture_comparison(
                    baseline,
                    "instance_" + str(index) + "_cleared.png",
                    lambda image: compare_images(baseline, image).nfail == 0,
                )
                self.assertEqual(compare_images(baseline, cleared).nfail, 0)

    def test_marquee_instances_and_empty_pick(self):
        self.capture_instances("instances_marquee.png")
        _, _, width, height = self.view.get_viewport_dimensions()
        top_left = (0, 0)
        bottom_right = (width, height)
        # Split between the fixture's left and right instances.
        midpoint_top = (width // 2, 0)
        midpoint_bottom = (width // 2, height)
        for region, start, end, indices in (
            ("left half", top_left, midpoint_bottom, [0]),
            ("left half, reversed drag", midpoint_bottom, top_left, [0]),
            ("right half", midpoint_top, bottom_right, [1]),
            ("whole viewport", top_left, bottom_right, [0, 1]),
            ("whole viewport, reversed drag", bottom_right, top_left, [0, 1]),
        ):
            with self.subTest(region=region):
                selection = self.view.pick_multiple_prims(
                    Gf.Vec2f(*start), Gf.Vec2f(*end), self.instance_pick_mask
                )
                self.assert_selected_instances(selection, indices)

        # This small corner patch stays outside both cubes in the fixture.
        empty_corner_size = Gf.Vec2f(20, 20)
        empty_corner_center = empty_corner_size / 2
        self.assertTrue(
            self.view.pick_multiple_prims(
                Gf.Vec2f(*top_left), empty_corner_size, self.instance_pick_mask
            ).empty()
        )
        self.assertTrue(
            self.view.pick_single_prim(empty_corner_center, self.instance_pick_mask).empty()
        )
