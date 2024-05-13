"""This module contains the sensor entities for the Ecostream integration."""  # noqa: D404

import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities) -> None:
    """Set up the Ecostream sensor entities."""

    api = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            ecostream_qset_control_entity(api, config_entry.entry_id),
            ecostream_sensor_fan_eha_speed(api, config_entry.entry_id),
            ecostream_sensor_fan_sup_speed(api, config_entry.entry_id),
            ecostream_sensor_eco2_eta(api, config_entry.entry_id),
            ecostream_sensor_rh_eta(api, config_entry.entry_id),
            ecostream_sensor_temp_eha(api, config_entry.entry_id),
            ecostream_sensor_temp_eta(api, config_entry.entry_id),
            ecostream_sensor_temp_oda(api, config_entry.entry_id),
            ecostream_sensor_tvoc_eta(api, config_entry.entry_id),
            ecostream_frost_protection(api, config_entry.entry_id),
            ecostream_qset(api, config_entry.entry_id),
            ecostream_mode_time_left(api, config_entry.entry_id),
        ],
        True,
    )


class ecostream_qset_control_entity(NumberEntity):
    """Represents the Ecostream Qset Control entity."""

    def __init__(self, api, entry_id):
        self._api = api
        self._entry_id = entry_id
        self.native_min_value = 60
        self.native_max_value = 150
        self.native_step = 1
        self._attr_name = "ecostream_qset_control_entity"
        self.native_value = 60
        self.mode = "slider"

    @property
    def name(self):
        return "Ecostream Qset Control"

    @property
    def unique_id(self):
        return f"{self._entry_id}_ecostream_qset_control_entity"

    async def async_set_native_value(self, value: float) -> None:
        self.native_value = value
        await self._api.set_man_override(value)

    async def async_update(self):
        data = await self._api.get_data()
        if "status" in data and "qset" in data["status"]:
            self.native_value = data["status"]["qset"]

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Register the service
        self.hass.services.async_register(
            DOMAIN,
            "set_value",
            self.async_set_value_service,
            schema=vol.Schema(
                {
                    vol.Required("value"): vol.Coerce(int),
                }
            ),
        )

    async def async_set_value_service(self, call):
        value = call.data.get("value")
        try:
            await self.async_set_native_value(value)
        except Exception as e:
            _LOGGER.error(f"Error setting value: {e}")
            self._api.reconnect()
            await self.async_set_native_value(value)
            _LOGGER.info(f"Reconnected after excption: {e}")


class ecostream_sensor_fan_eha_speed(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_fan_eha_speed"

    @property
    def name(self):
        return "Ecostream Fan Exhaust Speed"

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:fan"

    @property
    def unit_of_measurement(self):
        return REVOLUTIONS_PER_MINUTE

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "fan_eha_speed" in data["status"]:
            self._state = data["status"]["fan_eha_speed"]


class ecostream_sensor_fan_sup_speed(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_fan_sup_speed"

    @property
    def name(self):
        return "Ecostream Fan Supply Speed"

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:fan"

    @property
    def unit_of_measurement(self):
        return REVOLUTIONS_PER_MINUTE

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "fan_sup_speed" in data["status"]:
            self._state = data["status"]["fan_sup_speed"]


class ecostream_sensor_eco2_eta(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_eco2_eta"

    @property
    def name(self):
        return "Ecostream eCO2 Return"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return CONCENTRATION_PARTS_PER_MILLION

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:molecule-co2"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "sensor_eco2_eta" in data["status"]:
            self._state = data["status"]["sensor_eco2_eta"]


class ecostream_sensor_rh_eta(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_rh_eta"

    @property
    def name(self):
        return "Ecostream Relative Humidity Return"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return "%"

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:molecule-co2"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "sensor_rh_eta" in data["status"]:
            self._state = data["status"]["sensor_rh_eta"]


class ecostream_sensor_temp_eha(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_temp_eha"

    @property
    def name(self):
        return "Ecostream Exhaust Air Temperature"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:temperature-celsius"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "sensor_temp_eha" in data["status"]:
            self._state = data["status"]["sensor_temp_eha"]


class ecostream_sensor_temp_eta(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_temp_eta"

    @property
    def name(self):
        return "Ecostream Return Air Temperature"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:temperature-celsius"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "sensor_temp_eta" in data["status"]:
            self._state = data["status"]["sensor_temp_eta"]


class ecostream_sensor_temp_oda(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_temp_oda"

    @property
    def name(self):
        return "Ecostream Outside Air Temperature"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:temperature-celsius"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "sensor_temp_oda" in data["status"]:
            self._state = data["status"]["sensor_temp_oda"]


class ecostream_sensor_tvoc_eta(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_tvoc_eta"

    @property
    def name(self):
        return "Ecostream Total Volatile Organic Compounds Outside Air"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return CONCENTRATION_PARTS_PER_BILLION

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:air-purifier"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "sensor_tvoc_eta" in data["status"]:
            self._state = data["status"]["sensor_tvoc_eta"]


class ecostream_frost_protection(BinarySensorEntity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_frost_protection"

    @property
    def name(self):
        return "Frost Protection"

    @property
    def is_on(self):
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:snowflake-melt"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "frost_protection" in data["status"]:
            self._state = data["status"]["frost_protection"]


class ecostream_qset(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_qset"

    @property
    def name(self):
        return "Qset"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "qset" in data["status"]:
            self._state = data["status"]["qset"]


class ecostream_mode_time_left(Entity):
    def __init__(self, api, entry_id):
        self.api = api
        self._state = None
        self._entry_id = entry_id

    @property
    def unique_id(self):
        return f"{self._entry_id}_mode_time_left"

    @property
    def name(self):
        return "Mode time left"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return UnitOfTime.SECONDS

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:timer-play"

    async def async_update(self):
        data = await self.api.get_data()
        if "status" in data and "override_set_time_left" in data["status"]:
            self._state = data["status"]["override_set_time_left"]
