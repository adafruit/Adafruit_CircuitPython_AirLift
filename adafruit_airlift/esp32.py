# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2020 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_airlift.esp32`
================================================================================

ESP32 Adapter Support

* Author(s): Dan Halbert
"""

import time

import board
import busio
import digitalio


class ESP32:
    """Class to manage ESP32 running NINA firmware for Wifi or Bluetooth."""

    NOT_IN_USE = 0
    """Not currently being used."""
    BLUETOOTH = 1
    """HCI Bluetooth mode."""
    WIFI = 2
    """Wifi mode."""

    def __init__(
        self,
        *,
        esp_reset=board.ESP_RESET,
        esp_gpio0=board.ESP_GPIO0,
        esp_busy=board.ESP_BUSY,
        esp_cs=board.ESP_CS,
        esp_tx=board.ESP_TX,
        esp_rx=board.ESP_RX,
        spi=None,
        reset_high=False,
    ):
        """Create an ESP32 instance, passing the pins needed to reset and communicate
        with the adapter.
        """
        self._mode = ESP32.NOT_IN_USE

        self._spi = board.SPI() if spi is None else spi

        self._reset_high = reset_high

        self._reset = digitalio.DigitalInOut(esp_reset)
        self._reset.switch_to_output(reset_high)

        self._gpio0_and_rts = digitalio.DigitalInOut(esp_gpio0)
        self._busy_and_cts = digitalio.DigitalInOut(esp_busy)
        self._chip_select = digitalio.DigitalInOut(esp_cs)
        self._uart = busio.UART(
            esp_tx, esp_rx, baudrate=115200, timeout=0, receiver_buffer_size=512
        )

    def _reset_esp32(self):
        # Reset by toggling reset pin for 100ms
        self._reset.value = self._reset_high
        time.sleep(0.1)
        self._reset.value = not self._reset_high

        #  Wait 1 second for startup.
        time.sleep(1.0)

        startup_message = b""
        while self._uart.in_waiting:  # pylint: disable=no-member
            more = self._uart.read()
            if more:
                startup_message += more

        return startup_message

    def start_bluetooth(self, debug=False):
        """Set up the ESP32 in HCI Bluetooth mode, if it is not already doing something else.
        Return a _bleio.Adapter.
        """
        # Will fail with ImportError if _bleio is not on the board.
        # That exception is probably good enough.
        # pylint: disable=import-outside-toplevel
        import _bleio

        if self._mode == ESP32.BLUETOOTH:
            return _bleio.adapter
        if self._mode == ESP32.WIFI:
            raise RuntimeError("ESP32 is in Wifi mode")
        self._mode = ESP32.BLUETOOTH

        # Boot ESP32 from SPI flash.
        self._gpio0_and_rts.switch_to_output(True)

        # Choose Bluetooth mode.
        self._chip_select.switch_to_output(False)

        startup_message = self._reset_esp32()
        if not startup_message:
            raise RuntimeError("ESP32 did not respond with a startup message")
        if debug:
            try:
                print(startup_message.decode("utf-8"))
            except UnicodeError:
                raise RuntimeError("Garbled ESP32 startup message") from UnicodeError

        # pylint: disable=no-member
        # pylint: disable=unexpected-keyword-arg
        return _bleio.Adapter(uart=self._uart, rts=self._gpio0_and_rts, cts=self._cts)

    def stop_bluetooth(self):
        """Stop Bluetooth on the ESP32."""
        if self._mode != ESP32.BLUETOOTH:
            return
        self._reset_esp32()

    def start_wifi(self):
        """Start Wifi on the ESP32."""
        raise NotImplementedError

    def stop_wifi(self):
        """Stop Wifi on the ESP32."""
        raise NotImplementedError
