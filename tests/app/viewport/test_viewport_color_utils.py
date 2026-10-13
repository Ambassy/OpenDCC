# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

import unittest

import OpenImageIO as oiio
from viewport_color_utils import PIXEL_TOLERANCE, color_matches, rgb_color, sample_rgb


class TestViewportColorUtils(unittest.TestCase):
    def test_comparison_uses_only_sampled_rgb_and_shared_tolerance(self):
        spec = oiio.ImageSpec(2, 1, 4, oiio.FLOAT)
        spec.x, spec.y = 10, 20
        image = oiio.ImageBuf(spec)
        expected = rgb_color((0.25, 0.5, 0.75))
        point = (spec.x, spec.y)
        image.setpixel(*point, (*expected.GetRGB(), 0))
        image.setpixel(spec.x + 1, spec.y, (1, 0, 0, 1))
        self.assertTrue(color_matches(image, point, expected))
        for difference, matches in (
            (PIXEL_TOLERANCE / 2, True),
            (PIXEL_TOLERANCE, True),
            (PIXEL_TOLERANCE * 2, False),
        ):
            with self.subTest(difference=difference):
                image.setpixel(*point, (0.25 + difference, 0.5, 0.75, 1))
                self.assertEqual(color_matches(image, point, expected), matches)

    def test_samples_outside_data_window_are_rejected(self):
        spec = oiio.ImageSpec(1, 1, 3, oiio.FLOAT)
        spec.x, spec.y = 10, 20
        image = oiio.ImageBuf(spec)
        for point in ((9, 20), (11, 20), (10, 19), (10, 21)):
            for sample in (
                sample_rgb,
                lambda image, point: color_matches(image, point, rgb_color((0, 0, 0))),
            ):
                with self.subTest(point=point, sample=sample):
                    with self.assertRaisesRegex(ValueError, "outside the image data window"):
                        sample(image, point)

    def test_non_rgb_images_are_rejected(self):
        image = oiio.ImageBuf(oiio.ImageSpec(1, 1, 1, oiio.FLOAT))
        for sample in (
            sample_rgb,
            lambda image, point: color_matches(image, point, rgb_color((0, 0, 0))),
        ):
            with self.subTest(sample=sample):
                with self.assertRaisesRegex(ValueError, "at least three image channels"):
                    sample(image, (0, 0))
