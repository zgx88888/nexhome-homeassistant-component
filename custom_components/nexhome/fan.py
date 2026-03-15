from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.const import Platform
from .utils import get_value_by_identifier
import asyncio
from .const import TIME_NUMBER, DEVICES, DOMAIN, PowerSwitch, IP_CONFIG, SN_CONFIG, Windspeed, FAN_MODEL_MAP
from .nexhome_entity import NexhomeEntity
from .header import ServiceTool
from .nexhome_device import NEXHOME_DEVICE
from .nexhome_coordinator import NexhomeCoordinator
from homeassistant.config_entries import ConfigEntryState

import logging
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    IP = config_entry.data.get(IP_CONFIG)
    SN = config_entry.data.get(SN_CONFIG)
    Tool = ServiceTool(IP, SN)
    devices = hass.data[DOMAIN][DEVICES]
    if devices:
        fans = []
        for device in devices:
            device_key = device.get("device_type_id")
            device_address = device.get("address")
            if device_key in NEXHOME_DEVICE:
                for entity_key, config in NEXHOME_DEVICE[device_key]["entities"].items():
                    if config["type"] == Platform.FAN:
                        identifiers = config["identifiers"]
                        params = [{'identifier': item, 'address': device_address} for item in identifiers]
                        coordinator = NexhomeCoordinator(hass, Tool, params)
                        if config_entry.state == ConfigEntryState.SETUP_IN_PROGRESS:
                            await coordinator.async_config_entry_first_refresh()
                        if device_key == '10':
                            fans.append(NexhomeFan10(device, entity_key, Tool, coordinator, hass))
                        elif device_key == '133':
                            fans.append(NexhomeFan133(device, entity_key, Tool, coordinator, hass))
        async_add_entities(fans)


class NexhomeFan(NexhomeEntity, FanEntity):

    def __init__(self, device, entity_key, tool, coordinator, hass):
        super().__init__(device, entity_key, coordinator)
        self._tool = tool
        self.hass = hass

    @property
    def is_on(self) -> bool:
        return self._device.get(PowerSwitch) == '1'

    async def async_turn_on(self, **kwargs):
        data = {'identifier': PowerSwitch, 'value': '1'}
        await self.hass.async_add_executor_job(self._tool.device_control, data, self._device['address'])

    async def async_turn_off(self, **kwargs):
        data = {'identifier': PowerSwitch, 'value': '0'}
        await self.hass.async_add_executor_job(self._tool.device_control, data, self._device['address'])


class NexhomeFan10(NexhomeFan):
    def __init__(self, device, entity_key, tool, coordinator, hass):
        super().__init__(device, entity_key, tool, coordinator, hass)
        self._attr_supported_features = (
            FanEntityFeature.PRESET_MODE | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        )
        self._attr_preset_modes = list(FAN_MODEL_MAP.values())
        self._attr_preset_mode = None  # 当前模式

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs):
        data = {'identifier': PowerSwitch, 'value': '1'}
        await self.hass.async_add_executor_job(self._tool.device_control, data, self._device['address'])
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)

    async def async_set_preset_mode(self, preset_mode: str):
        reverse_map = {v: k for k, v in FAN_MODEL_MAP.items()}
        if preset_mode not in reverse_map:
            return
        data = {'identifier': Windspeed, 'value': reverse_map[preset_mode]}
        await self.hass.async_add_executor_job(self._tool.device_control, data, self._device['address'])

    @property
    def preset_mode(self) -> str | None:
        speed_value = self._device.get(Windspeed)
        return FAN_MODEL_MAP.get(speed_value, None)


class NexhomeFan133(NexhomeFan):
    def __init__(self, device, entity_key, tool, coordinator, hass):
        super().__init__(device, entity_key, tool, coordinator, hass)
        self._attr_supported_features = (
            FanEntityFeature.PRESET_MODE | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        )
        self._attr_preset_modes = ["低速", "高速"]
        self._attr_preset_mode = None  # 当前模式

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs):
        data = {'identifier': PowerSwitch, 'value': '1'}
        await self.hass.async_add_executor_job(self._tool.device_control, data, self._device['address'])
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)

    async def async_set_preset_mode(self, preset_mode: str):
        if preset_mode == "低速":
            backend_value = '1'
        elif preset_mode == "高速":
            backend_value = '3'
        else:
            return
        data = {'identifier': Windspeed, 'value': backend_value}
        await self.hass.async_add_executor_job(self._tool.device_control, data, self._device['address'])

    @property
    def preset_mode(self) -> str | None:
        speed_value = self._device.get(Windspeed)
        if speed_value == '1':
            return "低速"
        elif speed_value == '3':
            return "高速"
        return None
