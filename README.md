# BUVA EcoStream — Home Assistant Integration  

![HA Compatibility](https://img.shields.io/badge/Home%20Assistant-2024.12+-blue.svg)  
![HACS Default](https://img.shields.io/badge/HACS-Custom-orange.svg)  
![License](https://img.shields.io/badge/License-MIT-green.svg)

A **full-featured, modern and high-performance** Home Assistant integration for the **BUVA EcoStream** balanced ventilation unit.
Supports *live push updates*, *fan control*, *boost automation*, *bypass valve*, *diagnostics*, *WiFi info*, and an **Apple Home-style dashboard**.

![dashboard](https://github.com/Uber1337NL/ecostream_homeassistant_integration/blob/v2.0/custom_components/ecostream/docs/dashboard.png)

---

## ✨ Features

### 🔧 Core Functionality

- Local push updates (no polling required)
- Automatic WebSocket reconnect
- Eco-friendly throttled update model
- 1 unified device in the device registry
- Full diagnostics + debug logging

### 🌬 Ventilation Control

- Modern HA FanEntity API  
- Percentage-based control (Qset)
- Fast-mode when adjusting ventilation  
- Automatic restoration after Boost mode  

### 🚀 Advanced Boost Mode

- Configurable duration (5/10/15/30 min)  
- Automatic CO₂-based cancellation  
- Countdown sensor (`boost_time_remaining`)  
- Visual dashboard tile (optional Apple-style card)

### 🔁 Bypass Valve

- Supports:
  - `OPEN`
  - `CLOSE`
  - `SET_POSITION (0–100%)`  
- Reports exact valve position

### 🌡 Sensors (rounded & refined)

- CO₂ (ppm, whole numbers)
- TVOC (ppb, whole numbers)
- Humidity (%)
- ETA, EHA, ODA temperature (1 decimal)
- RPM supply/exhaust
- Qset (%)
- Uptime (`Xd Yh Zm`)
- WIFI RSSI / SSID / IP

### 🔘 Buttons

- Reset filter timer  

---

## 📦 Installation

### 🔹 Option A — HACS (Custom Repository)

1. Go to **HACS → Integrations → Custom repositories**
2. Add:  [](https://github.com/epodegrid/ecostream_homeassistant_integration)
3. Category: **Integration**
4. Install & restart Home Assistant

### 🔹 Option B — Manual

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
  - Home Assistant will show a “BUVA EcoStream discovered” notification.
  - The config flow opens with the IP address pre-filled.
  - You only need to click Submit.
- If auto-discovery doesn't work, unplug your Ecostream unit for 10 seconds and then plug it in.
  Home Assistant should discover it within 2 minutes. If you're handy and know (how to find) the IP-address,
  then fill it in manually. Fixed IP is preferred! But since the Ecostream will normally never disconnect
  longer than 1 hour on the network, the IP-address will always be the same.

Click the discovered device → **the IP address will now be pre-filled automatically** (see section below).

### 🧩 Manual setup

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **EcoStream**
4. Enter the **IP address**, if not discovered automatically

---

## 🗑 Removing the Integration

1. Go to **Settings → Devices & Services**
2. Find **BUVA EcoStream** and click on it
3. Click the **⋮ menu** (three dots) in the top right
4. Select **Delete**
5. Confirm the removal
6. Restart Home Assistant

If you installed manually, also delete the folder `config/custom_components/ecostream/`.

---

## ⚙️ Options

### Update intervals

You can adjust:

- Normal push interval
- Fast push interval during manual control

These settings are available in **Options → Integration settings**.

---

## 🛠 Diagnostics

A full snapshot is available under:
**Device → … → Download Diagnostics**

This includes:

- Current data
- Connection state
- Push intervals
- Metadata
- Sanitized WiFi info (password removed)

## 🐛 Debugging

Enable debug logging for this integration:

logger:
  default: info
  logs:
    custom_components.ecostream: debug

You can also use the built-in diagnostics from:
Settings → Devices & Services → BUVA EcoStream → Diagnostics

---

## 📑 Known Limitations

- The unit does **not** expose a real WebSocket endpoint  
  → the integration uses a safe emulated stream model  
- Some older firmware versions may omit TVOC data  

---

## ❤️ Credits

- Original integration engineering: @epodegrid
- Rewrite to Bronze level and Apple-style UI: @Uber1337NL
- Thanks to contributers: @ricohageman and @jelle514
- Special thanks to the HA community for guidance

---

## 📜 License

MIT License — see LICENSE file
