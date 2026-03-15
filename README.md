# BUVA EcoStream - Home Assistant Integration

![HA Compatibility](https://img.shields.io/badge/Home%20Assistant-2024.12+-blue.svg)
![HACS Default](https://img.shields.io/badge/HACS-Custom-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

Quality scale: **Platinum**

A **full-featured, modern and high-performance** Home Assistant integration
for the **BUVA EcoStream** balanced ventilation unit.
Supports *live push updates*, *fan control*, *boost automation*,
*bypass switch control*, *diagnostics*, *WiFi info*, and an
**Apple Home-style dashboard**.

![dashboard](custom_components/ecostream/docs/dashboard.png)
---

## ✨ Features

### 🔧 Core Functionality

- Local push updates (no polling required)
- Automatic WebSocket reconnect
- Eco-friendly throttled update model
- One unified device in the device registry
- Full diagnostics + debug logging

### 🌬 Ventilation Control

- Modern HA FanEntity API
- Preset-based control (low / mid / high)
- Fast-mode window after manual control actions

### 🚀 Advanced Boost Mode

- Configurable duration (5/10/15/30/60 min)
- Uses `setpoint_high` as boost setpoint source
- Remaining override time via sensor (`mode_time_left`)
- Visual dashboard tile (optional Apple-style card)

### 🔁 Bypass Control

- Bypass is exposed as a binary switch (`open` / `closed`)
- Includes a diagnostic sensor for current bypass position

### 🌡 Sensors (rounded & refined)

- CO₂ (ppm, whole numbers)
- TVOC (ppb, whole numbers)
- Humidity (%)
- ETA, EHA, ODA temperature (1 decimal)
- RPM supply/exhaust
- Qset (m³/h)
- Uptime (`Xd Yh Zm`)
- WiFi RSSI / SSID / IP

### 🔘 Buttons

- Reset filter timer

---

## 📦 Supported Devices

| Device            | Supported | Notes                 |
| ----------------- | --------- | --------------------- |
| BUVA EcoStream    | ✅ Yes     | All firmware versions |
| BUVA EcoStream+   | ✅ Yes     | All firmware versions |
| Other BUVA models | ❌ No      | Different protocol    |

### Firmware Notes

- All known EcoStream firmware versions are supported.
- On some older firmware versions, TVOC data may not be present.
  In that case, the sensor will show `unavailable` rather than an error.
- The device does not expose a native WebSocket endpoint.
  This integration uses a safe emulated stream model compatible
  with all firmware versions.

---

## 📋 Supported Functions

### Sensors

| Entity                   | Unit | Description                             | Enabled by default |
| ------------------------ | ---- | --------------------------------------- | ------------------ |
| eCO₂ Return              | ppm  | CO₂ level in return air                 | ✅                  |
| TVOC Return              | ppb  | Total VOC in return air                 | ✅                  |
| Humidity Return          | %    | Relative humidity in return air         | ✅                  |
| Temperature ETA          | °C   | Extract air temperature                 | ✅                  |
| Temperature EHA          | °C   | Exhaust air temperature                 | ✅                  |
| Temperature ODA          | °C   | Outside air temperature                 | ✅                  |
| Bypass Position          | %    | Current bypass valve position           | ✅                  |
| Qset                     | m³/h | Active ventilation flow setpoint        | ✅                  |
| Heat Recovery Efficiency | %    | Calculated heat recovery efficiency     | ✅                  |
| Mode Time Left           | s    | Remaining time for active override mode | ✅                  |
| Fan Exhaust Speed        | rpm  | Exhaust fan speed                       | ✅                  |
| Fan Supply Speed         | rpm  | Supply fan speed                        | ✅                  |
| Summer Comfort Temp      | °C   | Summer comfort temperature threshold    | ✅                  |
| Filter Replacement Date  | date | Date of last filter reset               | ✅ (diagnostic)     |
| Uptime                   | -    | Device uptime formatted as `Xd Yh Zm`   | ✅ (diagnostic)     |
| WiFi IP                  | -    | Device IP address                       | ✅                  |
| WiFi SSID                | -    | Connected WiFi network name             | ✅                  |
| WiFi RSSI                | dBm  | WiFi signal strength                    | ✅                  |
| Setpoint Low             | m³/h | Configured low airflow preset           | ✅ (diagnostic)     |
| Setpoint Mid             | m³/h | Configured mid airflow preset           | ✅ (diagnostic)     |
| Setpoint High            | m³/h | Configured high airflow preset          | ✅ (diagnostic)     |
| External CO₂             | ppm  | External CO₂ sensor value               | ✅                  |

### Controls

| Entity         | Platform | Description                                       |
| -------------- | -------- | ------------------------------------------------- |
| Ventilation    | Fan      | Preset control (`low` / `mid` / `high`)           |
| Preset Low     | Switch   | Activate low preset override                      |
| Preset Mid     | Switch   | Activate mid preset override                      |
| Preset High    | Switch   | Activate high preset override                     |
| Bypass Valve   | Switch   | Open or close bypass override                     |
| Schedule       | Switch   | Enable or disable the ventilation schedule        |
| Summer Comfort | Switch   | Enable or disable summer comfort mode             |
| Boost          | Switch   | Start or stop boost mode                          |
| Boost Duration | Select   | Configure boost duration (5 / 10 / 15 / 30 / 60)  |
| Reset Filter   | Button   | Reset filter replacement date (if option enabled) |

### Binary Sensors

| Entity                     | Device class | Description                                | Enabled by default |
| -------------------------- | ------------ | ------------------------------------------ | ------------------ |
| Filter Replacement Warning | problem      | Primary trigger entity for overdue filters | ✅ (diagnostic)     |
| Frost Protection Active    | -            | Whether frost protection is active         | ✅                  |
| Schedule Enabled           | -            | Whether a schedule is active               | ✅                  |
| Summer Comfort Enabled     | -            | Whether summer comfort mode is active      | ✅                  |

---

## 🔄 Data Updates

This integration uses a **local push** model.
The EcoStream device sends data to Home Assistant over a persistent
HTTP long-poll connection (emulated WebSocket stream), without
Home Assistant polling the device.

### How It Works

1. On startup, the coordinator opens a persistent connection to the device's HTTP endpoint.
2. The device streams JSON state updates whenever its internal state changes.
3. The coordinator receives each update and immediately notifies all entities.
4. There is no fixed polling interval - updates arrive as fast as the device sends them.

### Throttling

To avoid excessive entity writes during rapid changes
(e.g., when adjusting fan speed), the integration applies
two throttle windows:

| Mode                 | Default | When active                  |
| -------------------- | ------- | ---------------------------- |
| Normal push interval | 10 s    | Idle / steady state          |
| Fast-mode window     | 5 s     | After manual control actions |

These are currently fixed in the integration code.

### Reconnection

If the connection to the device is lost, the coordinator will
automatically attempt to reconnect using exponential back-off.
Entities are marked `unavailable` until the connection is restored.

---

## 🎯 Use Cases

### Ventilate on high CO₂

Automatically increase ventilation when CO₂ levels are elevated and return to normal when air quality improves.

### Night-time schedule

Use the Schedule switch to let the device follow its built-in
time schedule overnight, then override to a fixed low level
during quiet hours via automation.

### Boost after cooking or shower

Trigger a timed boost when a motion sensor or humidity spike is
detected in kitchen or bathroom, and let it auto-cancel when
CO₂ drops back to baseline.

### Filter maintenance reminder

Use the Filter Replacement Warning binary sensor to send a
notification when filter replacement is overdue, or create a
persistent notification that clears when the filter is reset.

### Summer bypass automation

Monitor the outdoor temperature sensor and toggle Summer Comfort mode
automatically when conditions are suitable for free cooling
via the bypass valve.

---

## 📦 Installation

### 🔹 Option A - HACS (Custom Repository)

1. Go to **HACS -> Integrations -> Custom repositories**
2. Add: `https://github.com/epodegrid/ecostream_homeassistant_integration`
3. Category: **Integration**
4. Install & restart Home Assistant

### 🔹 Option B - Manual

Copy the folder: custom_components/ecostream/
Into: /config/custom_components/ecostream/

Restart Home Assistant.

---

## 🚀 Adding the Integration

### 🔍 Discovery

Home Assistant will automatically find the device via:

- Zeroconf (`_http._tcp`)
- DHCP hostname patterns
- MAC address prefix

- When a BUVA EcoStream is detected on the network:
  - Home Assistant will show a "BUVA EcoStream discovered" notification.
  - The config flow opens with the IP address pre-filled.
  - You only need to click Submit.
- If auto-discovery does not work, unplug your EcoStream unit for 10 seconds and then plug it back in.
  Home Assistant should discover it within 2 minutes. If needed, add it manually using the IP address.
  A fixed IP is preferred. In practice, the EcoStream usually keeps the same IP address unless it has been
  offline from your network for an extended period.

Click the discovered device -> **the IP address will now be pre-filled automatically** (see section below).

### 🧩 Manual setup

1. Go to **Settings -> Devices & Services**
2. Click **Add Integration**
3. Search for **EcoStream**
4. Enter the **IP address**, if not discovered automatically

---

## 📊 Dashboard Setup (Optional)

The repository includes a ready-to-use Lovelace dashboard template:

- `custom_components/ecostream/docs/dashboard.yaml`

### Can this dashboard be added automatically during integration install?

Short answer: **not reliably in a supported way**.

Home Assistant custom integrations are not intended to auto-create
or auto-inject complete Lovelace dashboards during install.
Dashboards are user-owned UI configuration (YAML or storage mode),
so setup is normally a manual one-time step.

### Requirements

For `dashboard.yaml` to render correctly, install these Lovelace frontend packages/resources:

1. `mini-graph-card`
2. `button-card`
3. `Mushroom` (for `mushroom-title-card`)
4. `card-mod`

Recommended install method: **HACS -> Frontend**.

Also ensure:

1. The EcoStream integration is installed and entities exist.
2. You are on a modern Home Assistant version (the dashboard uses `sections` view layout).
3. Theme `ios-light-mode` is optional; if missing, remove/replace the `theme:` line.

### Install dashboard.yaml Manually

1. Copy `custom_components/ecostream/docs/dashboard.yaml` to your HA config folder, for example:
   - `/config/dashboards/ecostream.yaml`
2. Add a Lovelace dashboard entry to `configuration.yaml`:

```yaml
lovelace:
  dashboards:
    ecostream:
      mode: yaml
      title: EcoStream
      icon: mdi:fan
      show_in_sidebar: true
      filename: dashboards/ecostream.yaml
```

3. Restart Home Assistant (or reload Lovelace/resources where applicable).

### Add Required Frontend Resources

If HACS did not auto-register resources, add them manually in **Settings -> Dashboards -> Resources**:

1. `/hacsfiles/mini-graph-card/mini-graph-card-bundle.js` (type: `module`)
2. `/hacsfiles/button-card/button-card.js` (type: `module`)
3. `/hacsfiles/lovelace-mushroom/mushroom.js` (type: `module`)
4. `/hacsfiles/lovelace-card-mod/card-mod.js` (type: `module`)

Note: if you use a custom icon set for `far:sun`,
make sure that icon pack is installed.
Otherwise replace it with an `mdi:` icon.

---

## 🗑 Removing the Integration

1. Go to **Settings -> Devices & Services**
2. Find **BUVA EcoStream** and click on it
3. Click the **⋮ menu** (three dots) in the top right
4. Select **Delete**
5. Confirm the removal
6. Restart Home Assistant

If you installed manually, also delete the folder `config/custom_components/ecostream/`.

---

## ⚙️ Options

### Available Options

You can configure:

- Filter replacement interval (days)
- Preset override duration (minutes)
- Boost duration (minutes)
- Summer comfort target temperature (15-30 C)
- Allow override filter date

---

## 🔧 Troubleshooting

### Device Not Discovered

- Unplug the EcoStream for 10 seconds and plug it back in. HA should detect it within 2 minutes.
- Make sure Home Assistant and the EcoStream are on the same network/VLAN.
- If discovery still fails, add the integration manually using the device IP address.
- Assign a static IP address to the device in your router's DHCP settings to prevent future IP changes.

### Entities Show "Unavailable"

- The integration lost connection to the device. Check that the device is reachable on your network.
- Go to **Settings -> Devices & Services -> EcoStream** and check the integration status.
- Enable debug logging (see below) and look for connection errors in the logs.
- Restart Home Assistant. The coordinator will attempt to reconnect automatically.

### TVOC Sensor Always Unavailable

- This is expected on some older EcoStream firmware versions that do not expose TVOC data.

### Fan Control Has No Effect

- Ensure the Schedule switch is **off** - an active schedule may override manual control.
- Check if Boost mode is active; boost takes priority over manual fan control.

### Boost Does Not Stop Automatically

- Boost runs for the configured boost duration.
- You can stop it manually with `switch.ecostream_boost`.

### Enable Debug Logging

Add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ecostream: debug
```

Then restart Home Assistant and check **Settings -> Logs** for detailed log output.

### Download Diagnostics

Go to **Settings -> Devices & Services -> BUVA EcoStream -> Download Diagnostics**
for a full state snapshot including connection info,
current data, and sanitized WiFi details.

---

## 💡 Automation Examples

### Boost on high CO₂

```yaml
alias: EcoStream - Boost on high CO₂
trigger:
  - platform: numeric_state
    entity_id: sensor.ecostream_eco2_return
    above: 1000
condition:
  - condition: state
    entity_id: switch.ecostream_boost
    state: "off"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.ecostream_boost
```

### Notify on Filter Overdue

Home Assistant UI steps:

1. Go to **Settings -> Automations & Scenes -> Create Automation**.
2. Choose **Start with an empty automation**.
3. For **Trigger**, choose **Device**.
4. Select your **BUVA EcoStream** device.
5. Select trigger type **Filter Replacement Warning turns on**.
6. Add an action, for example **Notifications: Send a notification via mobile_app**.
7. Save the automation.

YAML example (device trigger):

```yaml
alias: EcoStream - Filter replacement reminder
description: Notify when filter replacement becomes overdue.
trigger:
  - platform: device
    domain: binary_sensor
    device_id: YOUR_ECOSTREAM_DEVICE_ID
    entity_id: binary_sensor.ecostream_filter_replacement_warning
    type: turned_on
condition: []
action:
  - service: notify.mobile_app
    data:
      title: Filter replacement needed
      message: The EcoStream filter is overdue for replacement.
mode: single
```

Alternative YAML example (entity state trigger):

```yaml
alias: EcoStream - Filter replacement reminder (state trigger)
trigger:
  - platform: state
    entity_id: binary_sensor.ecostream_filter_replacement_warning
    to: "on"
action:
  - service: notify.mobile_app
    data:
      title: Filter replacement needed
      message: The EcoStream filter is overdue for replacement.
```

### Enable Summer Comfort on Warm Days

```yaml
alias: EcoStream - Summer comfort on warm days
trigger:
  - platform: numeric_state
    entity_id: sensor.ecostream_temperature_oda
    above: 22
action:
  - service: switch.turn_on
    target:
      entity_id: switch.ecostream_summer_comfort
```

### Low Ventilation at Night

```yaml
alias: EcoStream - Low ventilation at night
trigger:
  - platform: time
    at: "23:00:00"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.ecostream_preset_low
```

### Set Custom Qset from Automation

```yaml
alias: EcoStream - Set custom Qset
trigger:
  - platform: time
    at: "18:00:00"
action:
  - service: fan.set_qset
    target:
      entity_id: fan.ecostream_ventilation
    data:
      qset: 140
      override_minutes: 30
```

Use `override_minutes` only when you want to override the default preset override duration from integration options.

Note: `fan.set_qset` is a custom EcoStream fan entity service, not a built-in Home Assistant fan service.

---

## 🛠 Diagnostics

A full snapshot is available under:
**Device -> … -> Download Diagnostics**

This includes:

- Current data
- Connection state
- Push intervals
- Metadata
- Sanitized WiFi info (password removed)

---

## 📑 Known Limitations

- The unit does **not** expose a real WebSocket endpoint
  -> the integration uses a safe emulated stream model
- Some older firmware versions may omit TVOC data

---

## ❤️ Credits

- Original integration architecture and (reverse) engineering: @epodegrid
- Rewrite and quality-scale improvements plus Apple-style UI: @Uber1337NL
- Thanks to contributors and testers: @bartw91, @jelle514 and @ricohageman
- Special thanks to the HA community for guidance

---

## 📜 License

MIT License - see LICENSE file

