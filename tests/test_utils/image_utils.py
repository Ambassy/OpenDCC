# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import time
import unittest

import OpenImageIO as oiio
from Qt import QtCore

# PNG channels are normalized to [0, 1]; allow two 8-bit levels of rounding noise.
PIXEL_TOLERANCE = 2 / 255


def compare_images(before, after, roi=oiio.ROI.All):
    # Use the same failure and warning thresholds because callers only inspect nfail.
    return oiio.ImageBufAlgo.compare(before, after, PIXEL_TOLERANCE, PIXEL_TOLERANCE, roi=roi)


class ImageDiffingTestCase(unittest.TestCase):
    def capture_viewport(self, view, path, ready=None, timeout=10):
        """Capture a stable expected image; the default 10-second timeout bounds redraw waits."""
        path = Path(path).resolve()
        previous = None
        stable_frames = 0
        deadline = time.monotonic() + timeout
        # Selection changes and redraws are queued. Let Qt render before reading the framebuffer.
        while time.monotonic() < deadline:
            loop = QtCore.QEventLoop()
            # Give queued redraws 25 ms between samples without blocking Qt's event loop.
            QtCore.QTimer.singleShot(25, loop.quit)
            loop.exec_()
            image = view.grab_framebuffer()
            self.assertFalse(image.isNull(), "Viewport framebuffer is empty")
            self.assertTrue(image.save(str(path)), "Could not save " + str(path))
            current = oiio.ImageBuf(str(path))
            # Each capture overwrites the same file; bypass OIIO's cached pixels.
            self.assertTrue(current.read(0, 0, True), current.geterror())
            if previous is not None and (ready is None or ready(current)):
                result = compare_images(previous, current)
                stable_frames = stable_frames + 1 if result.nfail == 0 else 0
                # Require two matching comparisons (three captures), not just one quiet frame.
                if stable_frames == 2:
                    return current
            else:
                stable_frames = 0
            previous = current
        self.fail("Viewport did not reach the expected stable state: " + str(path))

    def assert_images_close(self, reference_path, actual_path, max_mean_error=1e-4):
        """Limit mean RGB error beyond PNG rounding noise (0.01% by default).

        Sparse highlights also need local pixel checks because this mean covers the whole image.
        """
        reference_path = Path(reference_path).resolve()
        actual_path = Path(actual_path).resolve()
        difference_path = actual_path.with_name(actual_path.stem + ".diff.png")
        if difference_path.exists():
            difference_path.unlink()
        reference = oiio.ImageBuf(str(reference_path))
        actual = oiio.ImageBuf(str(actual_path))
        self.assertTrue(reference.read(0, 0, True, oiio.FLOAT), reference.geterror())
        self.assertTrue(actual.read(0, 0, True, oiio.FLOAT), actual.geterror())
        self.assertEqual(
            (reference.spec().width, reference.spec().height),
            (actual.spec().width, actual.spec().height),
            "Image dimensions differ",
        )
        self.assertIn(reference.spec().nchannels, (3, 4), "Expected an RGB or RGBA reference")
        self.assertIn(actual.spec().nchannels, (3, 4), "Expected an RGB or RGBA capture")
        # Framebuffer alpha availability varies by platform; selection affects RGB.
        reference = oiio.ImageBufAlgo.channels(reference, (0, 1, 2))
        actual = oiio.ImageBufAlgo.channels(actual, (0, 1, 2))
        difference = oiio.ImageBufAlgo.abs(oiio.ImageBufAlgo.sub(reference, actual))
        excess_error = oiio.ImageBufAlgo.max(
            oiio.ImageBufAlgo.sub(difference, (PIXEL_TOLERANCE,) * 3), (0.0,) * 3
        )
        statistics = oiio.ImageBufAlgo.computePixelStats(excess_error)
        mean_error = sum(statistics.avg) / len(statistics.avg)
        if mean_error > max_mean_error:
            self.assertTrue(difference.write(str(difference_path)), difference.geterror())
        self.assertLessEqual(
            mean_error,
            max_mean_error,
            "Images differ:\n  {}\n  {}".format(reference_path, actual_path),
        )
