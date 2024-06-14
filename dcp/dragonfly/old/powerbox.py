import time
import logging

log = logging.getLogger('team_dragonfly')
log.addHandler(logging.NullHandler())

# If you want to see information messages in iPython interactive sessions:
# import logging
# log = logging.getLogger('team_dragonfly')
# log.setLevel(logging.INFO)


class PowerControllerError(Exception):
    "Raised when an error occurs during communication with a power controller."
    pass


def quadport_on(pegasus):
    "Turns the power controller on."
    log.info("Turning the power controller on.")
    powerbox_command = "P1:1"
    result = run_command(pegasus, powerbox_command)
    return result


def quadport_off(pegasus):
    "Turns the power controller off."
    log.info("Turning the power controller off.")
    powerbox_command = "P1:0"
    result = run_command(pegasus, powerbox_command)
    return result


def adjport_on(pegasus):
    "Turns the power controller on."
    log.info("Turning the power controller on.")
    powerbox_command = "P2:1"
    result = run_command(pegasus, powerbox_command)
    return result


def adjport_off(pegasus):
    "Turns the power controller off."
    log.info("Turning the power controller off.")
    powerbox_command = "P2:0"
    result = run_command(pegasus, powerbox_command)
    return result


def status(pegasus):
    "Reports status of the power controller."
    log.info("Getting power controller status.")
    powerbox_command = "PA"
    result = run_command(pegasus, powerbox_command)
    log.info(result)
    return result


def run_command(pegasus, command, verbose=False):
    "Runs a low-level power controller command."
    if command is not None:
        command = command + '\n'
        command = command.upper()
        pegasus.flush()
        pegasus.write(command.encode())
        line = ""
        lines = []
        while True:
            if pegasus.inWaiting() > 0:
                time.sleep(0.01)
                c = pegasus.read().decode()
                if c == '\n':
                    lines.append(line)
                    if verbose:
                        print("  Received: {}".format(line.lstrip().rstrip()))
                    break
                line = line + c
        pegasus.flush()
        return lines

