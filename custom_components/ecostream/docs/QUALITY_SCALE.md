# Status van de integratie

## Bronze

*** ✅ VOLDAAN (14/18)

- [-] `action-setup` - Service actions are registered in async_setup
- [-] `appropriate-polling` - If it's a polling integration, set an appropriate polling interval
- [ ] `brands` - Has branding assets available for the integration
- [X] `common-modules` - Place common patterns in common modules
- [ ] `config-flow-test-coverage` - Full test coverage for the config flow
- [X] `config-flow` - Integration needs to be able to be set up via the UI
  - [ ] Uses `data_description` to give context to fields
  - [ ] Uses `ConfigEntry.data` and `ConfigEntry.options` correctly
- [X] `dependency-transparency` - Dependency transparency
- [-] `docs-actions` - The documentation describes the provided service actions that can be used
- [X] `docs-high-level-description` - The documentation includes a high-level description of the integration brand, product, or service
- [X] `docs-installation-instructions` - The documentation provides step-by-step installation instructions for the integration, including, if needed, prerequisites
- [ ] `docs-removal-instructions` - The documentation provides removal instructions
- [X] `entity-event-setup` - Entity events are subscribed in the correct lifecycle methods
- [X] `entity-unique-id` - Entities have a unique ID
- [X] `has-entity-name` - Entities use has_entity_name = True
- [X] `runtime-data` - Use ConfigEntry.runtime_data to store runtime data
- [X] `test-before-configure` - Test a connection in the config flow
- [X] `test-before-setup` - Check during integration initialization if we are able to set it up correctly
- [X] `unique-config-entry` - Don't allow the same device or service to be able to be set up twice

action-setup: exempt
appropriate-polling: exempt
docs-actions: exempt

exempt — 3 regels niet van toepassing (geen polling, geen service actions)
todo — 1 regel nog open: brands (echte logo/icon assets ontbreken in de brand/ map). Even kijken hoe dat gaat na HA2026.3 en de brand map die geintroduceerd is. Anders via de oude weg (brands repo

## Silver

- [-] `action-exceptions` - Service actions raise exceptions when encountering failures
- [X] `config-entry-unloading` - Support config entry unloading
- [X] `docs-configuration-parameters` - The documentation describes all integration configuration options
- [X] `docs-installation-parameters` - The documentation describes all integration installation parameters
- [X] `entity-unavailable` - Mark entity unavailable if appropriate
- [X] `integration-owner` - Has an integration owner
- [ ] `log-when-unavailable` - If internet/device/service is unavailable, log once when unavailable and once when back connected
- [ ] `parallel-updates` - Number of parallel updates is specified
- [X] `reauthentication-flow` - Reauthentication needs to be available via the UI
- [ ] `test-coverage` - Above 95% test coverage for all integration modules

❌ ONTBREEKT (3/10)

1. log-when-unavailable De websocket_api.py logt bij verbindingsproblemen via_LOGGER.warning (reconnect) en _LOGGER.info (connected), maar dit voldoet niet volledig aan de eis: er moet precies één keer gelogd worden bij unavailable en één keer bij terugkeer. Nu wordt er bij elke reconnect-poging opnieuw gelogd door de backoff-loop.

2. parallel-updates PARALLEL_UPDATES is nergens gedefinieerd in de platform-bestanden (sensor.py, fan.py, switch.py, number.py, valve.py). Voor een push-integratie met CoordinatorEntity moet dit op 0 gezet worden om aan te geven dat updates parallel mogen lopen (coördinator beheert dit zelf).

3. test-coverage Er is momenteel alleen een testbestand voor de config flow. Silver vereist >95% dekking over alle modules (coordinator.py, websocket_api.py, sensor.py, fan.py, switch.py, number.py, valve.py, diagnostics.py). Dit is het meest omvangrijke punt.

Conclusie: 7/10 Silver-regels voldaan. 3 punten moeten nog worden opgelost.

parallel-updates is in een uur opgelost, log-when-unavailable is een dag werk, de volledige testdekking is het zwaarste punt.

## Gold

- [X] `devices` - The integration creates devices
- [X] `diagnostics` - Implements diagnostics
- [X] `discovery-update-info` - Integration uses discovery info to update network information
- [X] `discovery` - Devices can be discovered
- [ ] `docs-data-update` - The documentation describes how data is updated
- [ ] `docs-examples` - The documentation provides automation examples the user can use.
- [X] `docs-known-limitations` - The documentation describes known limitations of the integration (not to be confused with bugs)
- [ ] `docs-supported-devices` - The documentation describes known supported / unsupported devices
- [ ] `docs-supported-functions` - The documentation describes the supported functionality, including entities, and platforms
- [ ] `docs-troubleshooting` - The documentation provides troubleshooting information
- [ ] `docs-use-cases` - The documentation describes use cases to illustrate how this integration can be used
- [ ] `dynamic-devices` - Devices added after integration setup
- [ ] `entity-category` - Entities are assigned an appropriate EntityCategory
- [X] `entity-device-class` - Entities use device classes where possible
- [ ] `entity-disabled-by-default` - Integration disables less popular (or noisy) entities
- [ ] `entity-translations` - Entities have translated names
- [ ] `exception-translations` - Exception messages are translatable
- [ ] `icon-translations` - Entities implement icon translations
- [ ] `reconfiguration-flow` - Integrations should have a reconfigure flow
- [ ] `repair-issues` - Repair issues and repair flows are used when user intervention is needed
- [ ] `stale-devices` - Stale devices are removed

Voortgang:
icon-translations ⚠️ icons.json heeft een entities blok, maar gebruikt hardcoded entity-ID's i.p.v. de HA-standaard services/entity structuur met translation_key

❌ ONTBREEKT (14/21)

Documentatie (5 regels):

docs-data-update — README noemt "local push" maar beschrijft het WebSocket-mechanisme, update-cadans en throttling niet
docs-examples — Geen automatiseringsvoorbeelden in de README
docs-supported-devices — Geen lijst van ondersteunde/niet-ondersteunde apparaten of firmwareversies
docs-supported-functions — Geen gestructureerde tabel van entities, platforms en wat ze doen
docs-use-cases — Geen gebruiksscenario's beschreven ("boost bij hoge CO₂", "schema voor nacht", enz.)
docs-troubleshooting — Alleen debug logging beschreven, geen echte probleemoplossing
Code (8 regels):

entity-category — Geen enkele entity heeft EntityCategory.DIAGNOSTIC of CONFIG toegewezen (WiFi RSSI, uptime, filter datum zijn duidelijke DIAGNOSTIC-candidates)
entity-disabled-by-default — Minder relevante entities (WiFi SSID, RSSI, uptime, efficiëntie) zijn niet standaard uitgeschakeld via entity_registry_enabled_default = False
entity-translations — Entiteitnamen zijn hardcoded strings (name="Bypass Position" enz.), geen translation_key met vertalingen in en.json
exception-translations — Foutmeldingen in CannotConnect en flows zijn plain strings, niet vertaalbaar via strings.json
reconfiguration-flow — Geen async_step_reconfigure in config_flow.py
repair-issues — Geen gebruik van homeassistant.helpers.issue_registry voor herstelbare problemen (bijv. verloren verbinding, verouderd filter)
stale-devices — Geen opruiming van verouderde devices bij herconfiguratie
dynamic-devices — Niet van toepassing voor deze integratie (1 vast apparaat), maar formeel ontbreekt de implementatie

Conclusie: 7/21 Gold-regels voldaan.

De zwaarste openstaande punten zijn entity-translations, entity-category, entity-disabled-by-default en de ontbrekende documentatiesecties. De reconfiguration-flow en icon-translations (correcte structuur) zijn relatief snel op te lossen.

## Platinum

- [X] `async-dependency` - Dependency is async
- [ ] `inject-websession` - The integration dependency supports passing in a websession
- [ ] `strict-typing` - Strict typing

1. async-dependency ✅ Voldaan — De integratie heeft geen externe bibliotheek (requirements: []). Alle communicatie loopt via aiohttp dat rechtstreeks uit Home Assistant's eigen stack komt. Volledig async.

2. inject-websession ❌ Niet voldaan — De regel vereist dat de externe afhankelijkheid het injecteren van een websession ondersteunt. In websocket_api.py:39 wordt de sessie intern opgehaald via async_get_clientsession(hass) en opgeslagen als self._session. De klasse accepteert geen session parameter van buiten — de hass instantie wordt meegegeven en de sessie wordt intern aangemaakt. Voor Platinum moet de sessie van buitenaf injecteerbaar zijn, zodat HA de volledige controle heeft over de HTTP-sessie-lifecycle.

3. strict-typing ❌ Niet voldaan — Er zijn meerdere # type: ignore annotaties aanwezig:

fan.py:23 — # type: ignore[name-defined]
fan.py:40 — # type: ignore[name-defined]
switch.py:185 — # type: ignore[attr-defined]
Daarnaast ontbreekt een mypy.ini of pyrightconfig.json met strict-modus configuratie, en is er geen py.typed marker aanwezig. Strict typing vereist dat de code zonder type: ignore volledig typeveilig doorkomt.

Conclusie: 1/3 Platinum-regels voldaan.

De twee ontbrekende punten zijn overzichtelijk:

inject-websession: EcostreamWebsocket.__init__ uitbreiden met een optionele session parameter
strict-typing: de 3 type: ignore gevallen oplossen (met name de name-defined fouten in fan.py die ontstaan door een circulaire import-constructie) en een strict mypy-configuratie toevoegen