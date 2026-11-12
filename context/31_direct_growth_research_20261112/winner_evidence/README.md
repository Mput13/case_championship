# Winner evidence: AER–SVX and MRV–SVX

Scope is limited to the two profitable model candidates and both directions. The 0/KEEP=[] entries are documented in `route_economics/shortlist.csv` as explicit empty-affected scenarios, not observed service facts.

## Finding

- **AER–SVX:** Red Wings’ current route page identifies Koltsovo and Sochi and gives an average one-way duration of 3h30. This is meaningful route-page evidence, but it does not establish a dated operation, flight number, days, frequency, or service during 7–13 Dec 2026. Keep the operating frequency UNKNOWN until a dated carrier/airport timetable is admitted. The Koltsovo schedule search snippet supports Ural Airlines U6-565 on Sundays in the 14 Jun–13 Sep 2026 season only; it is a competitor, never RW.
- **MRV–SVX:** Red Wings’ current route page explicitly describes the Yekaterinburg–Mineralnye Vody itinerary as connecting in Magnitogorsk. That is evidence of a marketed connecting itinerary, not nonstop WZ service. A direct operating frequency remains UNKNOWN. Do not use the RW connection as direct service or competitor capacity.
- **7–13 Dec 2026:** No primary pair-specific date/frequency proof was admitted for either pair. The RW 27 Oct winter-schedule announcement establishes a season change, not either route.
- **Demand basis:** reused context24 summary figures 785,000 AER and 211,000 MRV for 2025 are bidirectional airport passenger segments/throughput, not endpoint OD or unique city-pair trips. The original primary locator was not recovered in this packet; the assembler should carry the source locator from context24 market_final unchanged. These numbers are not projected into 2027.
- **Model implication:** current KEEP2027 remains an UNKNOWN parameter. Historical service, if verified, belongs only in a separately labeled scenario-transfer case. Do not allow the scenario zero to imply that all passengers are additional. Existing route_economics closure/variant-block material should remain linked to its original source and labeled geometric/scenario evidence, never actual closure.

## Search scope

Reused the candidate shortlist/frequency cases and targeted Red Wings route pages plus Koltsovo airport timetable and RW seasonal announcements. Six narrow page/source checks are logged; no broad route generation, fare shopping, load-factor demand estimation, or external transactions. Failure to retrieve exact dated schedule rows is UNKNOWN, not evidence of no flights.

## Files

`own_RW_service.csv`, `competitors.csv`, `historical_demand_definition.csv`, `sources.csv`, `model_admission.csv`, `validation.json`. Price/frequency fields are empty/UNKNOWN where not evidenced.
