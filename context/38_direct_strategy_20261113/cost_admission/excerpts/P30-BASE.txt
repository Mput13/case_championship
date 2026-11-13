# Base OMS: costs and support evidence (11 Nov 2026)

## Findings

**Maintenance capability exists as a historical, type-specific capability.** Omsk Airport says its engineering service received an FAP-285 certificate on 31 March 2017 to maintain RRJ-95 / Sukhoi SuperJet 100. Its own news says engineers trained for RRJ-95 and that staff expansion would enable more work and attract other airlines. This supports that OMS had a maintenance authorization and trained personnel at that time. It does not establish present certificate status, permitted work checks/limitations, line vs heavy maintenance scope, 24-hour shifts, spare capacity, current staff, price, airline contract, or readiness for SJ-100 with PD-8. An old Red Wings flight or airport acceptance is not maintenance evidence. The standard ground handling agreement also requires type-specific handling authorization, not maintenance capability.

**Public tariff data provide limited rate anchors, not a base quote.** Airport tariff disclosure lists regulated charges: takeoff/landing 1,220 RUB per tonne MTOW, transport security 845 RUB per tonne MTOW, terminal domestic 127 RUB/passenger, domestic passenger handling 235 RUB/passenger, and parking 8% per hour. Fuel storage and fueling entries are 3,142 and 2,509 RUB/tonne, with listed effective date 2024-01-01. Current disclosure is dated effective 2026-08-21. The table/index excerpt did not establish VAT basis, billing/free-period rules for parking, current validity of older fuel rates, or negotiated base discounts. Keep formulas at the quoted units and reconcile against invoices. Rates may overlap the model's 96,089 / 115,307 RUB per-flight ground basket and its 1,696 RUB/tonne fueling assumption; do not add them until basket line items are known. Passenger terminal and passenger handling are separate tariff headings, but invoice treatment still needs confirmation. Passenger-car parking rates are irrelevant to aircraft stands.

No public primary airline-specific price was established for handling contracts, overnight aircraft stand/apron, rooms/heating, deicing, GSE, crew accommodation/transfer, tools, office/security/IT, spares or rotable pools, engineering shifts, launch/mobilization, or cash deposits. These remain UNKNOWN, not zero. Do not infer full payroll from a vacancy, nor invent rent or fleet lease. Calculator should request itemized offers/contracts and compute recurring cost from activity units only after admission.

## Fuel compensation gates

The model already has `fuel_compensation_rub_per_t` = 32,930 base / 3,024 cautious in `network.csv`. Do not add these amounts again as revenue or subtract again from fuel expense if the route economics already use net fuel cost. Record a single boundary: gross fuel spend = fuel tonnes × modeled fuel price; eligible tax deduction/credit is a separately gated cash/tax benefit; net expense is gross spend less only the admitted period-specific realized benefit. Model must disclose whether its existing per-tonne netting already applies compensation.

Official FNS/MinFin material describes an excise deduction under Tax Code art. 200(21), for qualifying taxpayer included in the civil aviation operator register and holding an operator certificate, and says the right relates to domestic aviation kerosene supply. This is an excise mechanism—not a route/passenger subsidy or automatically a per-tonne payment to each carrier. Exact current coefficients, eligible taxpayer, purchase/use volumes, supporting documents, filing treatment, VAT interaction and cash lag were not resolved. A published FNS 2026 notice reflects amendments by Federal Law 218-FZ, so the currently consolidated statute and period-specific coefficient must be checked. Lack of proof here means UNKNOWN, not legal ineligibility.

Model derivation for 32,930 / 3,024 and the exact cited late-fuel review handoff were not present at their stated path in this checkout; local branch refs are explicitly stale. Thus their precise numerator, coefficient, Jan-Sep averaging method and treatment as gross or net are unverified. Jan-Sep 2026 historical average is not a guarantee for 2027-28: statute/coefficient, eligible fuel mix, operator qualification and realization timing can change. Keep the values as sensitivities, not committed cash.

## Calculator handoff: unresolved inputs

1. Current OMS certificate/approved work scope and shifts; free capacity, agreement and price; confirmation for SJ-100/PD-8.
2. Itemized airline handling and airport invoices; aircraft parking base, free window and effective VAT/tax basis; apron/rooms, heating, deicing and equipment rates.
3. Crew and engineering staffing/rotation, relocation, hotels, transfers, training and reserves; parts/rotable stock and tool list; GSE, IT, office and security offers.
4. One-off launch schedule and amounts; lease/security/utility cash deposits; working-capital and tax-offset timing.
5. Fuel compensation source calculation and exact 2026 rule/coefficient, eligible operator and tonnes, documentation, VAT and tax cash realization. Confirm if model's existing 32,930/3,024 is already netted in unit economics.

No fully loaded OMS base cost can be calculated from public evidence in this pass.
