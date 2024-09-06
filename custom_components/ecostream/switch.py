from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_state_change

from . import EcostreamWebsocketsAPI
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the custom switch entity."""
    ws_client: EcostreamWebsocketsAPI = hass.data[DOMAIN]["ws_client"]
    switch = EcostreamSwitch(ws_client, hass)
    async_add_entities([switch], True)

    sensor_entity_id = "sensor.ecostream_qset" 

    async_track_state_change(
        hass, sensor_entity_id, switch.async_check_sensor_value
    )

class EcostreamSwitch(SwitchEntity):
    """Representation of a custom switch for the Ecostream integration."""

    def __init__(self, ws_client: EcostreamWebsocketsAPI, hass: HomeAssistant):
        """Initialize the switch."""
        self._ws_client = ws_client
        self._is_on = False
        self._hass = hass

    @property
    def name(self):
        """Return the name of the switch."""
        return "Ecostream Max Ventilation"

    @property
    def is_on(self):
        """Return the state of the switch."""
        return self._is_on

    @property
    def entity_category(self):
        """Return the entity category, such as CONFIG or DIAGNOSTIC."""
        return EntityCategory.CONFIG

    async def async_turn_on(self, **kwargs):
        """Turn the switch on and send a payload via WebSocket."""
        payload = {
            "config": {
                "man_override_set": 140,
                "man_override_set_time": 1800
            }
        }
        await self._ws_client.send_json(payload)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off and send a payload via WebSocket."""
        payload = {
            "config": {
                "man_override_set": 60,
                "man_override_set_time": 1800
            }
        }
        await self._ws_client.send_json(payload)
        self._is_on = False
        self.async_write_ha_state()

    @callback
    async def async_check_sensor_value(self, entity_id, old_state, new_state):
        """Check sensor value and turn off switch if condition is met."""
        if new_state and new_state.state >= "100": 
            await self.async_turn_off()

