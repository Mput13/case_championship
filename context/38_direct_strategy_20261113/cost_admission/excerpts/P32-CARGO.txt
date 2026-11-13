# RW cargo research — directional data and payload constraints

Checked 2026-11-12. This is a focused independent search for ordinary, non-DGR cargo on candidate return sectors to an SVX base: OMS→SVX, GOJ→SVX, KUF→SVX, with TOF→SVX retained only as a fallback. No inquiries were sent to companies. Search-result absence is not evidence that orders do not exist.

## Findings

- **A real carrier channel exists:** Red Wings publicly offers cargo carriage on its own flights, accepts general cargo, names Omsk, Samara, Nizhny Novgorod and Yekaterinburg among cities, and directs shippers to request a quote with origin, destination, date and shipment details. The published SSJ hold figure is **a maximum compartment specification**, not free capacity.
- **No directional buyer evidence surfaced:** this search found no public route-specific shipper order, tender, postal/corporate contract, or recurring shipment for OMS→SVX, GOJ→SVX, KUF→SVX or TOF→SVX. Accordingly these are UNKNOWN, not zero and not “weak” observed directions. No public route rates or realized net yields were found.
- **Airport facilities do not prove RW acceptance:** Koltsovo’s primary airport pages describe cargo/mail terminal functions and published hours. RW contract, service window on the flight, cutoff, and tariffs remain unconfirmed. For OMS/GOJ/KUF only RW’s broad city channel was found; destination handling evidence was insufficient. TOF branch stopped at UNKNOWN.
- **Aircraft limits:** an EASA RRJ-95B type certificate data sheet copy gives MTOW 45,880 kg, MLW 41,000 kg and MZFW 40,000 kg. It is not an RW aircraft DOW or proof of RRJ-95LR applicability. Actual DOW, exact configuration and approved hold floor/contour/door limits remain UNKNOWN. RW’s 4,200 kg / 20.15 m³ compartment maximum does not establish residual capacity.

## How to interpret capacity

For a consistently defined departure/arrival mass basis, the structural payload ceiling is bounded by `min(MZFW − DOW, MTOW − DOW − departure fuel with dispatch reserves, MLW − DOW − arrival fuel)`. Use approved aircraft-specific dispatch calculations and definitions. Do not subtract only trip fuel. Then deduct passenger mass, baggage, mail and operational/company load exactly once, and enforce hold mass, volume, geometry and floor limits. Actual DOW and fuel are not public here, so this formula is a framework, not an estimate of free kilograms.

Passenger standard weights and a 20 kg checked-bag allowance are scenarios/published entitlements, not actual per-flight mass. Clarify whether operator passenger mass includes cabin baggage before adding baggage separately. Physical kg, volumetric/chargeable kg and billing rounding are distinct. Volume may bind before mass. Cargo receipts require the AWB contract and must be reduced by handling, agent, incremental fuel and any displaced passenger/baggage contribution; each is UNKNOWN. Do not multiply 4,200 kg by an assumed rate.

## What could change the conclusion

Obtain from RW, for each flight/date/direction: dated AWB/order pipeline and shipper commitment; quote/rate sheet including minimum AWB, chargeable-weight divisor and rounding, taxes and mandatory charges; booked physical kg and dimensions; handling/agent/fuel increment; actual aircraft variant and dispatch loading data. For aircraft: operator DOW by tail/configuration, dispatch fuel basis, and approved loading manual/AFM limits. For each destination: cargo operator/contract, general-cargo acceptance window and service tariff. These are data requirements, not requests sent as part of this work.

## Sources and checks

`sources.csv` records source URLs, dates/locators, short source excerpts or paraphrases, evidence class, and what each source does not establish. Other CSVs retain IATA direction, unit, source, publication/check date and explicit UNKNOWN fields. `validation.json` confirms structural CSV width consistency only. It does not validate demand, aircraft dispatch, or economics. Sources S03 is an EASA document hosted on a non-EASA archive; treat as a located copy, not operator-controlled dispatch documentation.
