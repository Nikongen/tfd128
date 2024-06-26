import os
import serial
import time


class Tfd128SerialConnection(object):

    class Busy(Exception):
        pass

    def __init__(self, device):
        if not os.path.exists(device):
            raise RuntimeError("TFD 128 device '%s' not found" % device)
        self._device = device
        self.debug = False
        self.com = None

    def open(self):
        if self.com is None:
            self.com = serial.Serial(
                self._device,
                baudrate=38400,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=5,
            )
            # above might return before the port is actually available
            time.sleep(0.5)

    def xfer(self, cmd, data=()):
        """Transfers the given cmd and data values to and returns the answer
        from the device."""

        # some constants for better readability
        STX, ETX, ENQ, ACK, NAK = 0x02, 0x03, 0x05, 0x06, 0x15
        self.open()
        # send command sequence
        self.com.write(bytearray([STX]))
        self.com.write(bytearray(cmd, "ascii"))
        for c in data:
            if c in (STX, ETX, ENQ):
                self.com.write(bytearray([ENQ]))
                c += 0x80
            self.com.write(bytearray([c]))
        self.com.write(bytearray([ETX]))

        # Answer sequence must start with STX.
        r = ord(self.com.read(1))
        if r != STX:
            raise RuntimeError("internal: expected STX, got %s" % r)

        # Then the command itself.
        r = ord(self.com.read(1))
        if r != ord(cmd):
            raise RuntimeError("internal: expected %s, got %s" % (cmd, r))

        result = []
        while r != ETX:
            r = ord(self.com.read(1))
            if r == ENQ:
                r = ord(self.com.read(1))
                result.append(r - 0x80)
            elif r != ETX:
                result.append(r)

        if self.debug:
            print("%s -> %s" % (cmd, result))

        # FIXME: How do we distinguish an error from the busy state? In both
        # cases, the device will just send NAK.
        if result == [NAK]:
            raise self.Busy

        if data and result[0] != ACK:
            raise RuntimeError("internal: expected ACK; got %s" % result[0])

        return result


class Tfd128Connection(Tfd128SerialConnection):
    pass


class Tfd128(object):

    # These are the mask values used by the logger internally.
    HUMIDITY = 0x01
    TEMPERATURE = 0x02

    class Busy(Exception):
        pass

    def __init__(self, device=None):
        self._dev = Tfd128Connection(device)
        self._params = None
        self._debug = False
        self.time_format = None

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value
        self._dev.debug = value

    def __xfer(self, cmd, data=()):
        try:
            return self._dev.xfer(cmd, data)
        except self._dev.Busy:
            raise self.Busy

    # Return the current date and time as a list of octets in the
    # format the logger expects.

    def __now(self):
        from datetime import datetime

        now = datetime.now()
        return [
            now.year & 0xFF,
            now.year >> 8,
            now.month - 1,
            now.day,
            now.hour,
            now.minute,
            now.second,
        ]

    def __parse_date(self, date, rawtime):
        """
        Parse a date list in the internal logger format and create a value.

        :param[in] date: A date list in the internal logger format.
        :param[in] rawtime: If 'rawtime' is False, format the time value
           according to the currently active format string.
        :return: The resulting date.
        """
        if self._debug:
            print("__parse_date in: %s" % date)
        if date:
            date = [date[0] + (date[1] << 8), date[2] + 1] + date[3:7] + [0, 1, -1]
            date = time.mktime(tuple(date))
            if self.time_format is not None and not rawtime:
                date = time.strftime(self.time_format, time.localtime(date))
        else:
            # No stop time recorded (memory full or battery drained).
            date = 0
        if self._debug:
            print("__parse_date out: %s" % date)
        return date

    def __make_temp(self, temp):
        """
        Convert two octets into a temperature value.

        :param[in]: tuple containing the low and high parts of the temperature.
        :return: The temperature in degrees Celsius.
        """
        lo, hi = temp
        temp = lo + (hi << 8)
        # Sign extend negative values.
        temp = temp - ((temp & 0x8000) << 1)
        # Values are stored in 1/10 degrees celsius.
        return temp / 10.0

    def __get_block(self, cmd):
        """
        Return a data block from the device.

        :param[in] cmd: Depending on the 'cmd' value (see protocol description),
           either the first data block, or the next data block will be
           retrieved.
        :return: A list of tuples. In case of temperature only logging, each
           tuple consists of the timepoint and the temperature. Otherwise, each
           tuple consists of the timepoint, the temperature and the humidity
           value.
        """
        if not self._params["count"]:
            return []
        result = self.__xfer(cmd)
        r = []
        # Due to the USB protocol being block oriented, the last block
        # returned may contain more values than logged, so we need to count.
        while result and self._params["count"]:
            t = self._params["start"] + self._actual * self._delta
            if self.time_format is not None:
                t = time.strftime(self.time_format, time.localtime(t))
            if self._params["mode"] & self.HUMIDITY:
                value = (t, self.__make_temp(result[:2]), result[2])
                del result[:3]
            else:
                value = (t, self.__make_temp(result[:2]))
                del result[:2]
            r.append(value)
            self._params["count"] -= 1
            self._actual += 1
        return r

    def __fixstop(self, params):
        """
        As the device only stores measurement points in fixed intervals, the
        last stored measurement point may be 1 or 5 minutes (minus 1s) before
        the stored end time; we therefore need to round down the stop time.
        Additionally, it calculates the end time if it is not provided by
        the logger (e.g. in case of battery failure).

        :param[in] params: Hash with the parameters.
        :return: The corrected stop time.
        """
        seconds = params["interval"] * 60
        if params["stop"]:
            from math import floor

            delta = params["stop"] - params["start"]
            params["stop"] = params["start"] + floor(delta / seconds) * seconds
        else:
            # no stop time (battery failure or eeprom full)
            params["stop"] = params["start"] + (params["count"] - 1) * seconds
        return params

    # The following three methods make the class iterable. Thus, the data
    # values can simply be retrieved via:
    #
    #    logger = Tfd128()
    #    for values in logger:
    #       for v in values:
    #         <do domething with measurement point 'v'>

    def __iter__(self):
        return self

    def __start_iteration(self):
        self._params = self.__fixstop(self.params(rawtime=True))
        self._actual = 0
        self._start = True
        if self._params["count"] == 1:
            self._delta = 0
        else:
            self._delta = (self._params["stop"] - self._params["start"]) / (
                self._params["count"] - 1
            )

    def __next__(self):
        if self._params is None:
            self.__start_iteration()
        elif self._params["count"] == 0:
            self._params = None
            raise StopIteration
        if self._start:
            data = self.__get_block("R")
            self._start = False
        else:
            data = self.__get_block("N")
        return data

    def data(self):
        """
        The data() method is an alternative to the iteration. It returns *all*
        stored data points. Usage:

        logger = Tfd128()
        for v in logger.data():
           <do domething with measurement point 'v'>
        """
        values = []
        for block in self:
            values += block
        return values

    def is_idle(self):
        """Return True if the logger is idle, else return False."""
        try:
            self.__xfer("V")
            return True
        except self.Busy:
            return False

    def is_busy(self):
        """Return True if the logger is busy, else return False."""
        return not self.is_idle()

    def start(self, interval, mode):
        """Start logging."""
        if not interval in (1, 5):
            raise ValueError
        if mode & ~(self.TEMPERATURE | self.HUMIDITY):
            raise ValueError
        # Failsafe: always add temperature flag.
        mode |= self.TEMPERATURE
        self.__xfer("S", self.__now() + [mode, interval])

    def stop(self):
        """Stop logging."""
        self.__xfer("E", self.__now())

    def params(self, rawtime=False):
        """Return a dictionary with the stored logger parameters."""
        result = self.__xfer("Z")
        assert len(result) == 9 or len(result) == 16
        params = {}
        params["start"] = self.__parse_date(result[:7], rawtime)
        params["mode"], params["interval"] = result[7:9]
        params["stop"] = self.__parse_date(result[9:], rawtime)
        lo, hi = self.__xfer("A")
        params["count"] = lo + (hi << 8)
        return params

    def version(self):
        """Return the version number."""
        lo, hi = self.__xfer("V")
        return lo + (hi << 8)
