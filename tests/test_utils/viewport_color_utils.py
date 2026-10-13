# Copyright Contributors to the OpenDCC project
# SPDX-License-Identifier: Apache-2.0

from pxr import Gf
import OpenImageIO as oiio
from image_utils import PIXEL_TOLERANCE, compare_images

FRAME_SIZE = 400
# The orthographic cube covers the center; inset corner pixels contain only background.
BACKGROUND_INSET = 10
CUBE_SAMPLE = (FRAME_SIZE // 2, FRAME_SIZE // 2)
BACKGROUND_SAMPLES = tuple(
    (x, y)
    for x in (BACKGROUND_INSET, FRAME_SIZE - BACKGROUND_INSET)
    for y in (BACKGROUND_INSET, FRAME_SIZE - BACKGROUND_INSET)
)
GRADIENT_ROWS = (
    BACKGROUND_INSET,
    FRAME_SIZE // 4,
    FRAME_SIZE // 2,
    3 * FRAME_SIZE // 4,
    FRAME_SIZE - BACKGROUND_INSET,
)
# A 100 mm orthographic aperture frames ten scene units around the two-unit cube.
CAMERA_APERTURE = 100
CAMERA_DISTANCE = 10

IDENTITY_SPACE = Gf.ColorSpace("identity")
LINEAR_SPACE = Gf.ColorSpace("lin_rec709_scene")
SRGB_SPACE = Gf.ColorSpace("srgb_rec709_scene")


def rgb_color(rgb, color_space=IDENTITY_SPACE):
    """Label RGB values with a color space; this constructor does not convert them."""
    return Gf.Color(Gf.Vec3f(*rgb), color_space)


def _pixel_roi(image, point):
    x, y = point
    spec = image.spec()
    if spec.nchannels < 3:
        raise ValueError("Color samples require at least three image channels")
    if not (spec.x <= x < spec.x + spec.width and spec.y <= y < spec.y + spec.height):
        raise ValueError("Color sample is outside the image data window: " + str(point))
    return oiio.ROI(x, x + 1, y, y + 1, 0, 1, 0, 3)


def sample_rgb(image, point):
    """Read RGB at an absolute image coordinate, excluding alpha."""
    _pixel_roi(image, point)
    return Gf.Vec3f(*image.getpixel(*point)[:3])


def color_matches(image, point, expected):
    """Compare encoded RGB values with the golden-image tolerance, without color conversion."""
    roi = _pixel_roi(image, point)
    spec = oiio.ImageSpec(1, 1, 3, oiio.FLOAT)
    # Keep the reference pixel at the framebuffer coordinate so the ROI selects both images.
    spec.x, spec.y = point
    reference = oiio.ImageBuf(spec)
    reference.setpixel(*point, tuple(expected.GetRGB()))
    return compare_images(image, reference, roi).nfail == 0


def gradient_color(top, bottom, row):
    """Interpolate display-encoded fixture colors at a framebuffer row."""
    # Raster interpolation samples the center of each pixel, half a pixel below its top edge.
    fraction = (row + 0.5) / FRAME_SIZE
    return rgb_color(top.GetRGB() * (1 - fraction) + bottom.GetRGB() * fraction)


DEFAULT_BACKGROUND = rgb_color((0.36,) * 3)
OCIO_BACKGROUND = rgb_color((0.15, 0.4, 0.75))
SOLID_COLORS = (DEFAULT_BACKGROUND, OCIO_BACKGROUND, rgb_color((0,) * 3), rgb_color((1,) * 3))
DEFAULT_SELECTION_COLOR = (1, 1, 0, 0.5)
GRADIENT_DISABLED_BACKGROUND = rgb_color((0.2, 0.3, 0.4))
GRADIENT_COLORS = tuple(
    (rgb_color(top), rgb_color(bottom))
    for top, bottom in (((0.8, 0.2, 0.1), (0.1, 0.3, 0.9)), ((0.1, 0.7, 0.3), (0.6, 0.1, 0.4)))
)
RED_SELECTION = (1, 0, 0, 1)
BLUE_SELECTION = (0, 0, 1, 1)
SELECTION_COLORS = (("red", RED_SELECTION, 0), ("blue", BLUE_SELECTION, 2))
HALF_ALPHA_SELECTION = (0, 0, 1, 0.5)
TRANSPARENT_SELECTION = (0, 0, 1, 0)
# Require a substantial highlight, rather than a few antialiased edge pixels.
MIN_HIGHLIGHT_PIXELS = 100
HIGHLIGHT_CHANNEL_MIN = 0.9
OTHER_CHANNEL_MAX = 0.4

# These are the matrix scale/offset and input-space scale in fixtures/colors.ocio.
OCIO_DISPLAY_SCALE = 0.5
OCIO_DISPLAY_OFFSET = Gf.Vec3f(0.1, 0.2, 0.3)
OCIO_INPUT_SCALE = 2
