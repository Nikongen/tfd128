# tfd128 python package

Based on [TFD128 v2.1.5](http://projects.nesrada.de/tfd128/index.html) by Andreas Engel with a few changes for packaging and documentation.
Most of the work was done by the original author

**Homepage:** http://projects.nesrada.de/tfd128/

# First steps:
**See installation steps below**

# Commandline usage
## Quick start
Start recording, 5min interval, temperature only:
```bash
./tfd128 --start --interval 5 --mode t
```

Start recording, 1min interval, temperature and humidity:
```bash
   ./tfd128 --start --interval 1 --mode th
```

Stop recording:
```bash
   ./tfd128 --stop
```

Write recorded data points to a file, using the time and date
format of the current locale. The filename will be automatically
determined from the recorded data:
```bash
   ./tfd128 --dump-values --time-fmt "%c"
```

Write recorded data points to file 'data.txt', using the default
date/time format, but change the data format to
"<date><tab><temperature><tab><humidity>" instead of the original csv
format (which is "%c;%d;%t;%h"):
```bash
   ./tfd128 --dump-values --output data.txt --data-fmt="%d\t%t\t%h"
```

## Full commandline documentation
In the following, all options are described. Some of them have a short
alternative. See output of `--help` for a complete list.

- `--help`: Print some help.
- `--device <device>`: The device to be used. Use this when the device is not found on
      `/dev/tfd128` or `/dev/ttyUSB0`.
- `--start`: Start recording. Uses the current date and time as starting
      time. Requires both '--mode' and '--interval' to be specified.
- `--stop`: Stop recording. Uses the current date and time as stop time.
- `--interval <value>`: Required with `--start`, ignored otherwise. Specifies the
      recording interval in minutes. Valid values are 1 and 5.
- `--mode <value>`: Required with `--start`, ignored otherwise. Specifies the
      recording mode. Valid values are:
    - `t`  temperature only
    - `th` temperature plus humidity
- `--version`: Print the device's internal version number.
- `--status`: Prints `BUSY` and exits with 1 if the device is currently
      recording. Else prints 'IDLE' and exits with 0.
- `--dump-count`: Print number of recorded data points.
- `--dump-info`: Print info on the recorded data set.
- `--dump-values`: Dump recorded data values into a file or to standard output.
- `--output <filename>` To be used with `--dump-values`. Use given filename for output
      data. Use `-`' as filename to print the data to standard
      output. The default filename if this option is omitted is
      "tfd128-YYYYMMDD.csv" where "YYYYMMDD" is the stop date of the
      recorded data.
- `--no-progress` To be used with `--dump-values`. Suppresses the progress bar
      when reading the recorded data values. The progress bar will be
      suppressed automatically when reading the data to standard
      output.
- `--time-fmt <value>`: To be used with `--dump-values` or `--dump-info`. Changes the
      output format of date/time values. The specified value will be
      directly passed to `time.strftime()`, so see its documentation for
      valid values.
      The default if this option is omitted is "%d.%m.%Y %H:%M:%S".
- `--data-fmt <value>`: To be used with `--dump-values`. Changes the output format for
      data point values. The default value if this option is omitted is "%c;%d;%t" for
      temperature only recordings and `"%c;%d;%t;%h"` for recordings
      with temperature and humidity. The following is a list of special values to
      be used in the format string:
    - %p      will be replaced with a single percent sign
    - %c      the number of the data point; starts with zero
    - %d      the date/time of the data point
    - %t      temperature value
    - %h      humidity value
- `--debug`: Prints some debugging info when accessing the device.

See `./tfd128.py --help` for an up-to-date list of all available
command line options.

# Class usage
## `Tfd128(device)`
Create a Tfd128 device. `device` must be the full pathname to the
      serial device.

### Attributes:
- time_format: The time format to be used for all returned time/date
      values. This value is unset initially, meaning to use the number
      of seconds since epoch. The value will be directly passed to
      time.strftime(), so see it's documentation for valid values.
- debug: If this value is set to true, some debugging data will be
      printed when communicating with the device.
### Methods:
- `data()`: Return a list of all stored data points. Each list element is a
      tuple of either two or three values. The first value is the time
      of the measurement point, the second is the temperature in
      degrees celsius. The third value - if available - is the
      humidity in percent. **Note** that since the data is read via a slow serial port,
      depending on the number of stored data points this method may
      take some time before it returns (worst case ~45s). If you want
      to give some user feedback, consider iterating over the
      instance, which splits reading the data points into smaller
      chunks.
    - Raises Tfd128.Busy if the logger is currently recording.

Example: if `logger` is an instance of class `Tfd128`, you can
read the data values via:
```python
for values in logger:
    print "Processing next data block..."
    for value in values:
    print value
```
- `is_idle()`: Return true if the logger is idle and false if the logger is
      busy.

- `is_busy()`: Return true if the logger is busy and false if the logger is
      idle.
- `start(interval, mode)`:Start recording using the current time as starting time.
      'interval' must be either 1 or 5, indicating the number of
      minutes between each measurement point. `mode` is a bit-mask of
      `Tfd128.TEMPERATURE` and `Tfd128.HUMIDITY` (with `Tfd128.TEMPERATURE` 
      always being set implicitly).

    - Raises `ValueError` if the parameters are not valid.
    -  Raises `Tfd128.Busy` if the logger is currently recording.
- `stop()`: Stop recording using the current time as end time.

- `params(rawtime=False)`:Return a dictionary with the device's last recording
      parameters. The valid keys are `start`, `stop`, `mode`',
      `interval` and `count`. If 'rawtime' is specified and True, the
      start and stop time values are always returned as number of
      seconds since epoch, regardless of the current setting of
      `time_format`.
    - Raises Tfd128.Busy is the device is currently recording.
- `version()`: Return the device's internal version number.
    -  Raises Tfd128.Busy is the device is currently recording.

# Installation Notes
**Note**: Most are for very old OS version. I will just update instructions for the systems I am using.
Feel free to add instructions for more operation systems

## Linux (OpenSuse 10.2)
Add the following entry to `/etc/modprobe.conf.local`:
```
options ftdi_sio vendor=0x0403 product=0xe0ec
```
Add the following entries to `/etc/udev/rules.d/10-private.rules`:
```
SUBSYSTEM=="usb_device", ACTION=="add", ATTRS{product}=="ELV TFD 128", \
    RUN+="/sbin/modprobe ftdi_sio"
KERNEL=="ttyUSB*", ATTRS{product}=="ELV TFD 128", SYMLINK+="tfd128"
```

## Linux (OpenSuse 10.3)
Add the following entry to `/etc/modprobe.conf.local`:
```
options ftdi_sio vendor=0x0403 product=0xe0ec
```
Add the following entries to `/etc/udev/rules.d/10-private.rules`:
```
SUBSYSTEM=="usb", ACTION=="add", ATTR{product}=="ELV TFD 128", \
    RUN+="/sbin/modprobe ftdi_sio"
KERNEL=="ttyUSB*", ATTR{product}=="ELV TFD 128", SYMLINK+="tfd128"
```

## Linux (Debian 4.0)
Add the following entry to `/etc/modprobe.d/ftdi_sio`:
```
options ftdi_sio vendor=0x0403 product=0xe0ec
```
Add the following entries to `/etc/udev/rules.d/10-private.rules`:
```
SUBSYSTEM=="usb_device", ACTION=="add", ATTRS{product}=="ELV TFD 128", \
    RUN+="/sbin/modprobe ftdi_sio"
KERNEL=="ttyUSB*", ATTRS{product}=="ELV TFD 128", SYMLINK+="tfd128"
```

## Linux (Ubuntu 9.04)
Add the following entry to `/etc/modprobe.d/ftdi_sio`:
```
alias usb:v0403pE0ECd*dc*dsc*dp*ic*isc*ip* ftdi_sio
options ftdi_sio vendor=0x0403 product=0xe0ec
```
Add the following entries to `/etc/udev/rules.d/10-private.rules`:
```
KERNEL=="ttyUSB*", ATTRS{product}=="ELV TFD 128", SYMLINK+="tfd128"
```

## Mac OS X
(from: Pascal Bihler <bihler@iai.uni-bonn.de>)

1. Install the FTDIUSB Mac OS X driver from http://www.ftdichip.com/Drivers/VCP.htm
2. Copy the following lines to the file
``` 
/System/Library/Extensions/FTDIUSBSerialDriver.kext/Contents/Info.plist
at the appropriate position (e.g. behind the other ELV-Entries):

<key>ELV TFD 128</key>
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.FTDI.driver.FTDIUSBSerialDriver</string>
    <key>IOClass</key>
    <string>FTDIUSBSerialDriver</string>
    <key>IOProviderClass</key>
    <string>IOUSBInterface</string>
    <key>bConfigurationValue</key>
    <integer>1</integer>
    <key>bInterfaceNumber</key>
    <integer>0</integer>
    <key>idProduct</key>
    <integer>57580</integer>
    <key>idVendor</key>
    <integer>1027</integer>
</dict>
```
3. Delete `/System/Library/Extensions.kextcache` and `/System/Library/Extensions.mkext`
4. Reboot the system

### Uninstall:
To remove the drivers from Mac OS X, the user must be logged on as
root. Root is a reserved username that has the privileges required to
access all files.
Start a Terminal session (Go > Applications > Utilities > Terminal)
and enter the following commands at the command prompt:
```
cd /System/Library/Extensions
rm -r FTDIUSBSerialDriver.kext
cd /Library/Receipts
rm -r FTDIUSBSerialDriver.pkg
```
The driver will then be removed from the system.

To remove the port from the system, run the application
SystemPreferences and select Network. Selecting Network Port
Configurations from the Show menu will display the port as greyed
out. Select the uninstalled port and click Delete.  Confirm the
deletion to remove the port.
