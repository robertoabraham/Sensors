import logging
import dragonfly.lens as lens
import dragonfly.camera as camera
import dragonfly.graphics as graphics

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.setLevel(logging.INFO)

def take_and_display_image(exptime=0.1, camera_number=1, filename="/tmp/foobar.fits",
                           lower=2, upper=5, transformation="sqrt"):
    """
    take_and_display_image - takes an image and displays it in the iTerm2 terminal.

    Example 1

        from dragonfly.system import system
        system.set_and_check_focus(18875)

    """
    temporary_png_filename = "/tmp/foobar.png"

    log.info("Taking exposure.")
    camera.expose(camera_number, exptime, filename)
    graphics.create_png(filename, temporary_png_filename, lower, upper, transformation, False)
    graphics.show_png(temporary_png_filename)

def set_focus_and_display_image(focus_value, camera_number=1, exptime=0.1):
    """
    set_focus - set lens focus to value, take a test image, and display it.

    Example 1

        from dragonfly.system import system
        system.set_and_check_focus(18875)

    """
    temporary_fits_filename = "/tmp/foobar.fits"
    temporary_png_filename = "/tmp/foobar.png"

    log.info("Setting focus to {}".format(focus_value))
    lens.set_focus_position(focus_value)

    log.info("Checking focus value.")
    current_focus_position = lens.get_focus_position()
    log.info("Current focus value is {}".format(current_focus_position))

    log.info("Taking test exposure.")
    camera.expose(camera_number, exptime, temporary_fits_filename)
    graphics.create_png(temporary_fits_filename, temporary_png_filename, 2, 5, "sqrt", False)
    graphics.show_png(temporary_png_filename)

def tweak_focus_and_compare_images(focus_shift, camera_number=1, exptime=0.1,
                                   lower=2, upper=5, transformation="sqrt"):
    """
    tweak_focus_and_compare_images - adjust lens focus quasi-dynamically

    This takes and displays an image, shifts focus slightly, then takes and redisplays an image.
    Comparison of the images is a useful way to adjust the focus.

    Example 1

        from dragonfly.system import system
        system.tweak_focus(-50)

    """
    temporary_fits_filename = "/tmp/foobar.fits"
    temporary_png_filename = "/tmp/foobar.png"

    log.info("Taking reference exposure.")
    camera.expose(camera_number, exptime, temporary_fits_filename)
    graphics.create_png(temporary_fits_filename, temporary_png_filename, 2, 5, "sqrt", False)
    graphics.show_png(temporary_png_filename)

    log.info("Changing focus.")
    lens.move_focus_position(focus_shift)

    log.info("Getting current focus value.")
    current_focus_position = lens.get_focus_position()
    log.info("Current focus value is {}".format(current_focus_position))

    log.info("Taking new exposure.")
    camera.expose(camera_number, exptime, temporary_fits_filename)
    graphics.create_png(temporary_fits_filename, temporary_png_filename, lower, upper, transformation, False)
    graphics.show_png(temporary_png_filename)


