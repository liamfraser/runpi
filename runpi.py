#!/usr/bin/env python2

# Copyright (c) 2013, Liam Fraser <liam@liamfraser.co.uk>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Liam Fraser nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL LIAM FRASER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import os
import pylcd
import datetime
sys.path.append('/root/garmin-activities')
import garmin

class runpi:
    """A daemon that displays data about running activities on a 4x20 character
    LCD connected to a Raspberry Pi"""

    def _parse_config(self):
        """Parse a very simple config file with 2 lines. The first is a Garmin
        Connect username and the second is a Garmin Connect password."""

        # Get current working directory
        pwd = os.path.dirname(__file__)
        cfg_file = '{0}/config'.format(pwd)
        lines = []

        try:
            with open(cfg_file, 'r') as f:
                for line in f:
                    lines.append(line.strip())
        except IOError:
            sys.exit("Unable to open config file")

        if len(lines) == 2:
            self._username = lines[0]
            self._password = lines[1]
        else:
            sys.exit("Bad config file")

    def _init_lcd(self):
        """Initialize the LCD"""

        PINMAP = {
            'RS': 7,
            'E': 8,
            'D4': 17,
            'D5': 18,
            'D6': 21,
            'D7': 22,
        }

        self._display = pylcd.hd44780.Display(backend = pylcd.hd44780.GPIOBackend,
                                              pinmap = PINMAP,
                                              lines = 4,
                                              columns = 20,
                                              enable_backlight = False)
        self._display.clear()
        self._display.home()
        self._ui = pylcd.hd44780.DisplayUI(self._display,
                                           pylcd.NoInput)

    def message(self, msg, start_line = 0):
        """Write a short message to the LCD"""

        if start_line == 0:
            # Do it the easy way
            self._ui.message(msg)
        else:
            # We'll have to split it manually
            char_count = 0
            line = start_line
            for char in msg:
                if char_count <= 19:
                    self._display.set_cursor_position(line = line,
                                                      column = char_count)
                    self._display.write(char)
                    char_count += 1
                else:
                    line += 1
                    char_count = 0
                    self._display.set_cursor_position(line = line,
                                                      column = char_count)
                    self._display.write(char)
                    char_count += 1

    def __init__(self):
        """Initialize the LCD, parse the config file and then log into Garmin
        Connect"""

        self._parse_config()
        self._init_lcd()
        self.message("Authenticating with Garmin Connect")
        try:
            self._activities = garmin.activities(self._username,
                                                 self._password)
            self.message("Authenticated")
        except:
            msg = "Failed to authenticate"
            self.message(msg)
            sys.exit(msg)
        
    def _do_latest(self):
        """Display the latest activity on the LCD"""

        latest = self._activities.get_latest()

        self._display.write("Latest:")

        self._display.set_cursor_position(line = 0, column = 8)
        self._display.write("{0} {1}".format(latest.distance_short,
                                             latest.short_unit))

        self._display.set_cursor_position(line = 1, column = 0)
        self._display.write("{0}:{1:0>2}:{2}".format(latest.duration.hour,
                                                 latest.duration.minute,
                                                 latest.duration.second))

        self._display.set_cursor_position(line = 1, column = 8)
        self._display.write("{0}:{1:0>2} {2}".format(latest.pace.minute,
                                                     latest.pace.second,
                                                     latest.pace_unit))
    
    def _do_week(self):
        """Display the weekly summary on the LCD"""

        week = self._activities.get_week()

        if len(week) == 0:
            self.message("You've not ran this week. Go for a run!",
                         start_line = 2)
            return

        # Running totals
        distance = 0
        pace_distance = 0
        duration_seconds = 0

        for a in week:
            duration_seconds += a.duration_seconds
            pace_distance += a.distance
            distance += a.distance_short
        
        pace = garmin.activity.pace_calculator(duration_seconds, pace_distance)

        # Convert seconds into hours, minutes and seconds
        hours = int(duration_seconds / 60 / 60)
        duration_seconds -= hours * 60 * 60
        minutes = int(duration_seconds / 60)
        duration_seconds -= minutes * 60
        seconds = duration_seconds

        self._display.set_cursor_position(line = 2, column = 0)
        self._display.write("Week:")

        self._display.set_cursor_position(line = 2, column = 8)
        self._display.write("{0} {1}".format(distance,
                                             week[0].short_unit))

        self._display.set_cursor_position(line = 3, column = 0)
        self._display.write("{0}:{1:0>2}:{2}".format(hours,
                                                 minutes,
                                                 seconds))

        self._display.set_cursor_position(line = 3, column = 8)
        self._display.write("{0}:{1:0>2} {2}".format(pace.minute,
                                                     pace.second,
                                                     week[0].pace_unit))

    def update(self):
        """Update the activities on the LCD"""

        self._display.clear()
        self._display.home()

        self._do_latest()
        self._do_week()

if __name__ == "__main__":
    daemon = runpi()
    daemon.update() 
