"""Support for sensors from the Draytek Vigor 130."""
from datetime import timedelta
import logging
import telnetlib
import re

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

ATTRIBUTE_DS_ACTUAL = "dsactual"
ATTRIBUTE_US_ACTUAL = "usactual"
ATTRIBUTE_DS_ATTAINABLE = "dsattainable"
ATTRIBUTE_US_ATTAINABLE = "usattainable"
ATTRIBUTE_DS_PATHMODE = "dspathmode"
ATTRIBUTE_US_PATHMODE = "uspathmode"
ATTRIBUTE_DS_INTERLEAVE_DEPTH = "dsinterleavedepth"
ATTRIBUTE_US_INTERLEAVE_DEPTH = "usinterleavedepth"
ATTRIBUTE_ATTENUATION = "attenuation"
ATTRIBUTE_SNR_MARGIN = "snrmargin"
ATTRIBUTE_UPTIME = "uptime"
ATTRIBUTE_CRC = "crc"
ATTRIBUTE_FEC = "fec"
ATTRIBUTE_HEC = "hec"

ATTRIBUTES = {
    ATTRIBUTE_DS_ACTUAL: ("dsactual", "Downstream Actual", None, "mdi:cloud-download"),
    ATTRIBUTE_US_ACTUAL: ("usactual", "Upstream Actual", None, "mdi:cloud-upload"),
    ATTRIBUTE_DS_ATTAINABLE: ("dsattainable", "Downstream Attainable", None, None),
    ATTRIBUTE_US_ATTAINABLE: ("usattainable", "Upstream Attainable", None, None),
    ATTRIBUTE_DS_PATHMODE: ("dspathmode", "Downstream Path Mode", None, None),
    ATTRIBUTE_US_PATHMODE: ("uspathmode", "Upstream Path Mode", None, None),
    ATTRIBUTE_DS_INTERLEAVE_DEPTH: (
        "dsinterleavedepth",
        "Downstream Interleave Depth",
        None,
        None,
    ),
    ATTRIBUTE_US_INTERLEAVE_DEPTH: (
        "usinterleavedepth",
        "Upstream Interleave Depth",
        None,
        None,
    ),
    ATTRIBUTE_ATTENUATION: ("attenuation", "Attenuation", None, None),
    ATTRIBUTE_SNR_MARGIN: ("snrmargin", "SNR Margin", None, None),
    ATTRIBUTE_UPTIME: ("uptime", "Uptime", None, None),
    ATTRIBUTE_CRC: ("crc", "CRC Errors", None, None),
    ATTRIBUTE_FEC: ("fec", "FEC Corrected", None, None),
    ATTRIBUTE_HEC: ("hec", "HEC", None, None),
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Draytek sensors."""
    async_add_entities([DraytekSensor(config)])


class DraytekSensor(Entity):
    """Representation of a Dovado sensor."""

    def __init__(self, config):
        """Initialize the sensor."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]

        self._state = None
        self._attributes = {}

    async def async_update(self):
        """Compute the state of the sensor."""
        try:
            tn = telnetlib.Telnet(self.host)
            tn.read_until(b"Account:")
            tn.write(self.username.encode("ascii") + b"\n")
            tn.read_until(b"Password:")
            tn.write(self.password.encode("ascii") + b"\n")
            tn.read_until(b"Vigor> ")
            tn.write(b"vdsl status\n")
            output = str(tn.read_until(b"Vigor> "))
            tn.write(b"vdsl status counts\n")
            output += str(tn.read_until(b"\n [ Counters: 15Min ]"))
            tn.write(b"\x1d")

            data = {}
            x = 1
            for item in output.split("\\r\\n"):
                line = re.split(":| bps|   US|dB|       FE", item)
                if x == 4:
                    data["dsactual"] = line[1].strip()
                    data["usactual"] = line[4].strip()
                if x == 5:
                    data["dsattainable"] = line[1].strip()
                    data["usattainable"] = line[4].strip()
                if x == 6:
                    data["dspathmode"] = line[1].strip()
                    data["uspathmode"] = line[3].strip()
                if x == 7:
                    data["dsinterleavedepth"] = line[1].strip()
                    data["usinterleavedepth"] = line[3].strip()
                if x == 8:
                    data["attenuation"] = line[1].strip()
                    data["snrmargin"] = line[3].strip()
                if x == 23:
                    data["uptime"] = re.search(r"\d+", line[1]).group()
                if x == 24:
                    data["crc"] = re.search(r"\d+", line[1]).group()
                if x == 25:
                    data["fec"] = re.search(r"\d+", line[1]).group()
                if x == 26:
                    data["hec"] = re.search(r"\d+", line[1]).group()
                x += 1

            for attribute in ATTRIBUTES:
                self._attributes[attribute] = data[attribute]

            self._state = len(self._attributes)

        except EOFError:
            _LOGGER.exception("Unexpected response from router")
            return
        except ConnectionRefusedError:
            _LOGGER.exception("Connection refused by router. Telnet enabled?")
            return

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Draytek"

    @property
    def state(self):
        """Return the sensor state."""
        return self._state

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return "mdi:cloud-download"

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes
