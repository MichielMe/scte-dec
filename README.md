# SCTE decoder repo
## Introductie
Omstreeks 2023 heeft de VRT een samenwerkingsverband aangegaan met Telenet en Proximus om SCTE-markeringen in het signaal in te voegen om advertisement blokken "un-skippable" te maken (met opt-out optie).

Eén van de grote redenen is dat deze un-skippable blokken een hogere commerciëele waarde hebben voor adverteerders. En zo vloeien er onrechtstreeks meer reclame inkomsten terug naar de VRT.
## Documentatie SCTE-standaarden
Confluence pagina:

https://vrt-prod.atlassian.net/wiki/spaces/TVUZS/pages/16091094/Beschrijving+SCTE-standaard+en+implementatie+op+VRT

## Technische monitoring
De SCTE-signalisatie zit in de VANC van het signaal en moet dus gemeten worden. Deze repo bevat enkele scripts om dit proces te vereenvoudigen.

De repo kan in drie grote blokken worden ingedeeld:

1) SCTE analyse op basis van een opname in het MXF-formaat

Op basis van MXFDecoder.py kan er een opname worden uitgelezen. De VANC met SCTE-104 signalisatie zit in een aparte data track van de MXF, we lezen deze uit via ffprobe.
Omdat deze opnames voornamelijk gebruikt wordt om de frame accuraatheid van de SCTE markeringen te meten, zit er ook functionaliteit in die de "frame boundaries" markeert rond de SCTE-triggers. De "announcement" frames worden gemarkeerd, en de "frame boundary"-frames worden gemarkeerd. 

Deze frames worden aan de hand van ffmpeg geexporteerd naar een aparte submap, op basis van de bestandsnaam van de opname. De SCTE informatie wordt hierop gewatermarked.

Gebruik:
`MXFDecoder.py SCTE_opname.mxf`

2) SCTE analyse op basis van de Morpheus "KernelDiags" logs

Dit script kan gebruikt worden om de "KernelDiags" logs vanuit Morpheus te verwerken, om te kijken welke SCTE berichten er zijn verstuurd vanuit de automatisatie driver naar de injector kaart.

Gebruik:
`MorpheusLogDecoder.py KernelDiags.log.2025-02-26`

3) SCTE analyse aan de hand van de Phabrix API

Via dit script kan er verbonden worden op een Phabrix met API functionaliteit (zoals de RX200 in technisch lokaal 1G11) om live de triggers uit te meten. 

Van zodra een Phabrix de juiste VANC data ontvangt, wordt de VANC data uitgelezen en via de gemeenschappelijke Tooling scripts uitgelezen in een voor de mens leesbaar formaat.


Gebruik:
`PhabrixDecoder.py`

In de code kan je nog "one-shot" True of False zetten, voor éénmalige uitlezing bij de eerste trigger of in loop.

4) In Tools/ zitten gemeenschappelijke functies en libraries om de SCTE-triggers te kunnen uitlezen.
