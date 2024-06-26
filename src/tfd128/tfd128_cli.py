import optparse
import os
import sys
import time

from tfd128 import Tfd128


def tfd128_main(args):
    p = optparse.OptionParser()
    p.add_option("--debug", "-g", action="store_true", help="for debugging only")
    p.add_option(
        "--device", "-d", action="store", help="Serial device to communicate with"
    )
    p.add_option("--start", "-S", action="store_true", help="start measurement")
    p.add_option("--stop", "-E", action="store_true", help="stop measurement")
    p.add_option(
        "--interval",
        "-i",
        action="store",
        type="choice",
        choices=("1", "5"),
        help="measurement interval, defaults to 5min",
    )
    p.add_option(
        "--mode",
        "-m",
        action="store",
        type="choice",
        choices=("t", "tf", "ft", "th", "ht"),
        help="measurement mode, defaults to temp+humidity",
    )
    p.add_option("--status", "-s", action="store_true", help="print current status")
    p.add_option(
        "--dump-version", "-v", action="store_true", help="print tfd128 version"
    )
    p.add_option(
        "--dump-count",
        "-a",
        action="store_true",
        help="print number of collected data points",
    )
    p.add_option(
        "--dump-values",
        "-r",
        action="store_true",
        help="print data points to ./tfd128-<date>.csv as CSV",
    )
    p.add_option(
        "--output", "-o", action="store", help='modify destination of -r; "-" = stdout'
    )
    p.add_option(
        "--no-progress",
        "-p",
        action="store_true",
        help="disable progress bar when dumping values",
    )
    p.add_option(
        "--dump-info", "-z", action="store_true", help="print data record info"
    )
    p.add_option(
        "--time-fmt",
        action="store",
        help="change time format; see strftime() for values",
    )
    p.add_option("--data-fmt", action="store", help="change output data format")

    p.set_defaults(time_fmt="%d.%m.%Y %H:%M:%S")

    opts, args = p.parse_args(args)

    if len(args) != 0:
        p.error("too many arguments")

    if opts.device is None:
        # TODO: make user specify the device
        # DEPRECATED: we should either find the logger via libusb
        #             or the user must explicitly specify the device
        for device in [
            "/dev/tfd128",  # Linux, preferred
            "/dev/tty.usbserial-3B1",  # Mac OS X
            "/dev/ttyUSB0",  # Linux, fallback
        ]:
            if os.path.exists(device):
                opts.device = device
                break

    if opts.device is None:
        print("No serial TFD 128 device found", file=sys.stderr)
        return 1

    try:
        logger = Tfd128(opts.device)
    except Exception as ex:
        print("%s" % ex, file=sys.stderr)
        return 1

    logger.debug = opts.debug
    logger.time_format = opts.time_fmt

    # The progress bar makes no sense when printing to stdout.
    if opts.output == "-":
        opts.no_progress = True

    # Check whether the logger is busy; in this case, the only allowed
    # commands are 'stop' and 'status'. We save the value, since we might
    # need it again.

    loggerIsBusy = logger.is_busy()

    if loggerIsBusy:
        if not opts.stop and not opts.status:
            print("logger is busy", file=sys.stderr)
            return 1

    if opts.start:
        if not opts.mode or not opts.interval:
            print("--start needs both --mode and --interval", file=sys.stderr)
            return 1
        mode = 0
        # The 'f' is a concession to german users.
        if opts.mode.find("t") >= 0:
            mode |= logger.TEMPERATURE
        if opts.mode.find("f") >= 0:
            mode |= logger.HUMIDITY
        if opts.mode.find("h") >= 0:
            mode |= logger.HUMIDITY
        logger.start(int(opts.interval), mode)
        return 0

    if opts.stop:
        # We choose a failsafe solution here: in case no logging is active,
        # we just ignore the call, i.e. the call should always succeed.
        if loggerIsBusy:
            logger.stop()
        return 0

    # FIXME: this accesses the logger twice, as the same query is used
    # to check whether or not the logger is idle.
    if opts.dump_version:
        print(logger.version())
        return 0

    if opts.dump_count:
        print(logger.params()["count"])
        return 0

    if opts.dump_info:
        params = logger.params()
        if params["stop"] == 0:
            params["stop"] = "<no time recorded>"
        if params["mode"] & logger.HUMIDITY:
            mode = "temperature+humidity"
        else:
            mode = "temperature"
        print("Start : %s" % params["start"])
        print("Stop  : %s" % params["stop"])
        print("Mode  : %s" % mode)
        print("Intvl : %d min" % params["interval"])
        print("Count : %d" % params["count"])
        return 0

    if opts.dump_values:
        if not opts.no_progress:
            from progress import ProgressDisplay
        params = logger.params(True)
        if opts.output == "-":
            output = sys.stdout
        else:
            if opts.output == None:
                filename = time.strftime(
                    "tfd128-%Y%m%d.csv", time.localtime(params["stop"])
                )
                print("Data will be written to file '%s'" % filename)
            else:
                filename = opts.output
            if os.path.exists(filename):
                print("'%s' already exists" % filename, file=sys.stderr)
                return 1
            output = open(filename, "w")
        if not opts.no_progress:
            progress = ProgressDisplay(params["count"])
        hasHumidity = params["mode"] & logger.HUMIDITY

        if opts.data_fmt:
            data_fmt = opts.data_fmt 
        else:
            data_fmt = "%c;%d;%t"
            if hasHumidity:
                data_fmt += ";%h"

        counter = 0
        for values in logger:
            for v in values:
                s = data_fmt
                s = s.replace("%c", "%s" % counter)
                s = s.replace("%d", "%s" % v[0])
                s = s.replace("%t", "%4.1f" % v[1])
                if hasHumidity:
                    s = s.replace("%h", "%d" % v[2])
                s = s.replace("%p", "%")
                output.write(s + "\n")
                counter += 1
            if not opts.no_progress:
                progress += len(values)
        return 0

    if opts.status:
        if loggerIsBusy:
            print("BUSY")
            return 1
        else:
            print("IDLE")
            return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    try:
        sys.exit(tfd128_main(sys.argv[1:]))
    except Exception as ex:
        print("ERROR: %s" % ex)
        sys.exit(1)
