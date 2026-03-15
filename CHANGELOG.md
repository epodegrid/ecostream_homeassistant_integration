# Changelog

Alle noemenswaardige wijzigingen in deze repository worden hier bijgehouden.

## [Unreleased]

### Sensors

- Verplaatst van `sensor` naar `binary_sensor`:
  - `frost_protection_active`
  - `schedule_enabled`
  - `summer_comfort_enabled`
- Sensorbeschrijvingen opgeschoond in `custom_components/ecostream/sensor.py`:
  - bovenstaande booleans verwijderd uit `SENSOR_DESCRIPTIONS`
- Nieuwe binary sensor mapping toegevoegd in `custom_components/ecostream/binary_sensor.py`:
  - nieuwe `BINARY_SENSOR_DESCRIPTIONS`
  - setup uitgebreid zodat deze entities worden aangemaakt naast `filter_replacement_warning`
- Vertalingen bijgewerkt in:
  - `custom_components/ecostream/translations/en.json`
  - `custom_components/ecostream/translations/nl.json`
  - keys voor bovenstaande entities verplaatst naar `entity.binary_sensor`
- Dashboardtemplate bijgewerkt:
  - `custom_components/ecostream/docs/dashboard.yaml` gebruikt nu:
    - `binary_sensor.ecostream_frost_protection_active`
    - `binary_sensor.ecostream_schedule_enabled`
    - `binary_sensor.ecostream_summer_comfort_enabled`
- Tests bijgewerkt:
  - `tests/test_binary_sensor.py`: nieuwe tests voor de 3 verplaatste booleans en setup-count
  - `tests/test_sensor.py`: verwijderde bool-helper tests/imports die niet meer van toepassing zijn

### Notes

- Dit is een domeinmigratie (`sensor` -> `binary_sensor`) voor bovengenoemde entities.
- Bestaande dashboards/automations met oude `sensor.ecostream_*` entity IDs moeten worden aangepast.
