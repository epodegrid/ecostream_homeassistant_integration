# Buva Ecostream Home Assistant Integration

This integration allows you to control your Buva Ecostream HRV unit, from Home Assistant. It connects to your local unit, 
using Python WebSockets and can set the fan speed from a slider input in HASS.

More controls are to be added later.

## Disclaimer

This project is not affiliated with or endorsed by Buva.

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
```
- alias: "Set Ecostream Value"
  trigger:
    platform: state
    entity_id: input_number.ecostream_control_slider
  action:
    service: ecostream.set_value
    data:
      value: "{{ states('input_number.ecostream_control_slider') | int }}"
```

## Notice

The use of this Project is subject to the following terms:

- The project is provided on an "as-is" basis, without any warranties or conditions, express or implied.
- The user of the project assumes all responsibility and risk for its use.
- The project contributors disclaim all liability for any damages, direct or indirect, resulting from the use of the project.
