✅ BRONZE-niveau (core minimum quality)
✔️ action-setup

We registreren service-achtige actions via websocket‐commando’s, maar nog geen echte HA-services.
→ gedeeltelijk, maar formeel ❌

✔️ appropriate-polling

Je integration is push-only (WebSocket) → correct.
→ ✔️

⚠️ brands

Je hebt icons in const.py, maar nog geen brands/ assets.
→ ❌

✔️ common-modules

We gebruiken aparte modules: coordinator.py, websocket_api.py, sensor.py, etc.
→ ✔️

❌ config-flow-test-coverage

Geen test coverage.

⚠️ config-flow

Je hebt een config flow, maar:

geen data_description

kein test before configure (ping/test connect)

options flow is basic
→ gedeeltelijk, maar formeel ❌

✔️ dependency-transparency

We gebruiken alleen aiohttp, geen verstopt libs.
→ ✔️

❌ docs-actions

Geen officiële HA-documentatiepagina.

❌ docs-high-level-description

Nog niet.

❌ docs-installation-instructions

Nog niet.

❌ docs-removal-instructions

Nog niet.

✔️ entity-event-setup

Entities luisteren naar de coordinator via _handle_coordinator_update.
→ ✔️

✔️ entity-unique-id

Alle entiteiten gebruiken entry.entry_id_<key>.
→ ✔️

✔️ has-entity-name

Al je entities hebben _attr_has_entity_name = True.
→ ✔️

✔️ runtime-data

Je gebruikt entry.runtime_data ✔️

⚠️ test-before-configure

Er wordt nog geen connectiviteitstest gedaan in de config flow.
→ ❌

⚠️ test-before-setup

We starten WebSocket meteen in async_setup_entry, maar we testen niet eerst of het werkt →
→ ❌

✔️ unique-config-entry

Je hebt controle op dubbele hosts.
→ ✔️

⭐️ BRONZE SCORE:

11 gehaald / 17 → Je zit bijna op Bronze, maar formsle documentatie & config-flow test ontbreekt.

🥈 SILVER-niveau (robustness & correctness)
❌ action-exceptions

De Boost actions geven geen HA‐exceptions terug bij fouten.

✔️ config-entry-unloading

Je implementeert async_unload_entry() correct.
→ ✔️

❌ docs-configuration-parameters

Nog niet.

❌ docs-installation-parameters

Nog niet.

⚠️ entity-unavailable

Momenteel blijven sensors “vast” als de WS wegvalt → je markeert ze nog niet unavailable.
→ ❌

❌ integration-owner

Heeft een maintainer nodig.

⚠️ log-when-unavailable

Je logt elke heartbeat, dat is te veel. Moet exact 1x offline / 1x online.
→ ❌

❌ parallel-updates

Niet toegepast (zeldzaam nodig voor push integrations).

❌ reauthentication-flow

Nog niet.

❌ test-coverage

Geen tests.

⭐️ SILVER SCORE:

1 gehaald / 10 → WIP

🥇 GOLD-niveau (UX, docs, completeness)

Hier zitten vooral documentatie-eisen en grote features.

✔️ devices

Je maakt een DeviceInfo → ✔️

⚠️ diagnostics

Je moet een diagnostics.py toevoegen.
→ ❌

❌ discovery

Geen SSDP/Zeroconf.

❌ discovery-update-info
❌ docs-*

Veel ontbreekt nog.

✔️ entity-device-class

Je hebt keurige device classes voor temp, humidity, CO₂. ✔️

❌ entity-category
❌ entity-disabled-by-default
❌ entity-translations
❌ exception-translations
❌ reconfiguration-flow
❌ repair-issues
⚠️ stale-devices

We verwijderen devices nog niet als host wegvalt.
→ ❌

⭐️ GOLD SCORE:

2 gehaald / 18

🏆 PLATINUM (deep integration quality)
❌ async-dependency

We hebben geen externe dependency maar websockets — OK maar niet Platinum.

✔️ inject-websession

We injecteren aiohttp session correct. ✔️

⚠️ strict-typing

Gedeeltelijk, maar niet overal → ❌

⭐️ PLATINUM SCORE:

1 gehaald / 3

📊 Samenvatting per niveau
Niveau	Vereisten gehaald	Status
Bronze	11 / 17	⚠️ bijna!
Silver	1 / 10	❌ ver weg
Gold	2 / 18	❌
Platinum	1 / 3	❌