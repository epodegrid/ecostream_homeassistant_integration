# Buva Ecostream Home Assistant Integration

This integration allows you to control your Buva Ecostream HRV unit, from Home Assistant. It connects to your local unit, 
using Python WebSockets and can set the fan speed from a slider input in HASS.

More controls to be added later.

## Usage
1. Copy the repository to custom components in Home Assistant.
2. Copy the following into configuration.yaml
```
input_number:
  ecostream_control_slider:
    name: Ecostream Qset Override
    initial: 60
    min: 60
    max: 150
    step: 1
```
3. Copy the following to assistant.yaml
- alias: "Set Ecostream Value"
  trigger:
    platform: state
    entity_id: input_number.ecostream_control_slider
  action:
    service: ecostream.set_value
    data:
      value: "{{ states('input_number.ecostream_control_slider') | int }}"
