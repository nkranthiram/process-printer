"""One-off script: builds data/aami_claims.json from the REAL parsed spans of the
AAMI PDS, so every raw_quote is guaranteed to be an actual substring of the source
document rather than a hand-retyped (and therefore error-prone / unverifiable)
string. This is the "manual-agent-pass-v1" extraction run — see
skills/claim-extraction/SKILL.md and architecture.md for why no automated LLM call
was used here.

Run once; output is checked into data/aami_claims.json and loaded by extraction.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.pipeline.ingestion import parse_pdf

AAMI_PDF = Path(__file__).parent.parent.parent.parent.parent / "docs" / "aami-comprehensive-car-insurance-pds.pdf"
OUT_PATH = Path(__file__).parent.parent.parent / "data" / "aami_claims.json"

EXTRACTOR_VERSION = "manual-agent-pass-v1"


def _normalize(s: str) -> str:
    """PyMuPDF emits real ligature glyphs (e.g. U+FB01 'ﬁ') for typographic
    ligatures like "fi" — so a plain-ASCII anchor like "certificate" won't
    substring-match the extracted text unless both sides are normalized the same
    way. Matching happens on normalized text; the stored raw_quote is still sliced
    from the ORIGINAL (unnormalized) span text, so it stays truly verbatim."""
    return (
        s.lower()
        .replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
        .replace("’", "'")
        .replace("‘", "'")
    )


def find_span(spans, page: int, contains: str):
    """Find a span on a given page containing a substring, case-insensitive.
    Fails loudly (not silently) if not found — a claim referencing a span that
    doesn't exist is exactly the fabrication this script exists to prevent."""
    contains_norm = _normalize(contains)
    for s in spans:
        if s.page == page and contains_norm in _normalize(s.text):
            return s
    raise ValueError(f"No span found on page {page} containing: {contains!r}")


def extract_quote(span_text: str, contains: str, max_len: int = 320) -> str:
    """Return a verbatim substring of the ORIGINAL span_text, centred on `contains`
    (matched against normalized text — see _normalize), capped in length so
    raw_quote stays a readable citation rather than a whole paragraph."""
    idx = _normalize(span_text).find(_normalize(contains))
    if idx == -1:
        raise ValueError(f"substring not found: {contains!r}")
    start = max(0, idx - 20)
    end = min(len(span_text), idx + len(contains) + max_len)
    quote = span_text[start:end]
    return quote.strip()


def main():
    pdf_bytes = AAMI_PDF.read_bytes()
    parsed = parse_pdf(pdf_bytes, title_hint="AAMI Comprehensive Car Insurance PDS")
    spans = parsed.spans

    claims = []

    def add(claim_type, subject, predicate, modality, statement, page, anchor, conditions=None, confidence=0.9, explicit=True):
        span = find_span(spans, page, anchor)
        quote = extract_quote(span.text, anchor)
        claims.append({
            "claim_type": claim_type,
            "subject": subject,
            "predicate": predicate,
            "modality": modality,
            "statement": statement,
            "raw_quote": quote,
            "page": page,
            "section_path": span.section_path,
            "conditions": conditions or [],
            "extraction_confidence": confidence,
            "extractor_version": EXTRACTOR_VERSION,
            "explicit": explicit,
        })

    # --- What's covered: the basics -----------------------------------------
    add("rule", "accidental_damage_cover", "car_covered_for_accidental_loss_or_damage", "covers",
        "The policy covers accidental loss or damage to the car caused by an incident during the period of insurance, including hail, storm, flood, fire, theft or attempted theft, malicious damage, vandalism, collision and impact.",
        26, "We cover accidental loss or damage to your car caused by an incident")

    add("rule", "third_party_property_damage", "legal_liability_for_other_peoples_property", "covers",
        "The policy covers the policyholder's legal liability for accidental damage to other people's property arising from use of the car, up to $20 million per incident including legal costs.",
        27, "The most we will pay for all claims from any one incident for legal liability")

    add("definition", "car_cover_scope_definition", "accessories_and_modifications_included", "defines",
        "Cover for the car includes accessories and modifications fitted to it, as described on the certificate of insurance.",
        16, "We cover your car as described on your certificate of insurance")

    add("exclusion", "car_cover_scope_exclusion", "fuel_lubricants_keys_excluded", "excludes",
        "Fuel/lubricants, baby capsules and child seats (except under the specific benefit), and lost car keys are not covered under the base car-cover benefit.",
        16, "fuel or lubricants")

    # --- General exclusions (Section 3) -------------------------------------
    add("exclusion", "driver_impairment", "excluded_if_driver_under_influence", "excludes",
        "No cover for an incident where the driver was under the influence of, or had judgement affected by, alcohol/drugs/medication, was over the legal limit, or refused a test — unless the vehicle was stolen (cover still applies to the owner, not the driver), or it can be shown the intake was not a contributing factor.",
        18, "was under the in", conditions=["driver_impairment_at_time_of_incident"])

    add("exclusion", "environmental_hazard", "excluded_asbestos_biological_nuclear", "excludes",
        "No cover for loss/damage involving asbestos, or biological/chemical/nuclear release, related looting/rioting, or public-authority action to remedy such a release.",
        18, "asbestos, asbestos")

    add("exclusion", "mechanical_failure", "excluded_wear_tear_mechanical_failure", "excludes",
        "No cover for structural, mechanical, electrical or electronic failure/breakdown (except specific AAMI Roadside Assist benefits), or for mould, mildew, wear, tear, rust, corrosion or depreciation, or for a car that was already damaged, unsafe or un-roadworthy at the time of the incident.",
        19, "any structural, mechanical, electrical or electronic failure")

    add("exclusion", "unsafe_continued_driving", "excluded_driving_after_damage_without_awareness_exception", "excludes",
        "No cover for damage from driving the car after it has already been damaged in an incident, unless the driver was not aware this could cause further damage, or was acting to prevent further loss (e.g. moving it off a busy motorway).",
        19, "driving your car after it has been damaged in an incident")

    add("exclusion", "overloading", "excluded_overcrowded_or_overloaded_car", "excludes",
        "No cover while the car is carrying more passengers or load than it's designed for or legally permitted, or load that isn't secured according to law.",
        19, "carrying more passengers than the car was designed for")

    add("exclusion", "consequential_loss", "excluded_extra_costs_and_consequential_loss", "excludes",
        "No cover for extra financial/non-financial costs following a covered incident, including loss of income, medical expenses, unauthorised professional/legal/valuation costs, diminished resale value after repair, or claim-related admin costs — except where specifically covered elsewhere (e.g. transport cover, third party property cleaning costs).",
        20, "extra costs or losses")

    add("exclusion", "commercial_use", "excluded_hire_or_reward_use", "excludes",
        "No cover while the car is used for hire, fare or monetary reward or as a courtesy car — except ridesharing or car pool/childcare arrangements, which are covered.",
        20, "your car being used for hire, fare or monetary reward",
        conditions=["car_used_for_hire_fare_or_reward", "NOT ridesharing_or_carpool_exception"])

    add("exclusion", "wrong_fuel", "excluded_incorrect_fuel_damage", "excludes",
        "No cover for loss or damage to the car (including engine/fuel system) caused by using the incorrect type of fuel.",
        20, "loss or damage to your car (including damage to your car")

    add("exclusion", "intentional_act", "excluded_deliberate_or_intentional_damage", "excludes",
        "No cover for an intentional/deliberate act by the policyholder, a family member, a co-owner of the car, or anyone acting with the policyholder's encouragement, assistance or consent, or anyone authorised to operate the car.",
        20, "an intentional or deliberate act by")

    add("exclusion", "outside_australia", "excluded_loss_outside_australia", "excludes",
        "No cover for loss or damage that occurs outside Australia.",
        20, "loss or damage that occurs outside Australia")

    add("exclusion", "motorsport_use", "excluded_racing_or_track_use", "excludes",
        "No cover while the car is used in or being tested for a race, contest, trial, hill climb or motor sport, or on a competition track/circuit/course/arena — unless it's a driver education course not involving speeds over 100km/h or timing.",
        21, "in, or being tested in preparation for, a race, contest, trial")

    add("exclusion", "reckless_driving", "excluded_reckless_act", "excludes",
        "No cover for any reckless act by the driver or anyone acting with the policyholder's encouragement/assistance/consent — examples given are street racing, burnouts, donuts, driving into water, using a mobile phone illegally, or excessive speed.",
        21, "any reckless act by you, or by the driver of your car")

    add("exclusion", "unattended_unlocked_keys_in_car", "excluded_theft_from_unattended_unlocked_car_with_keys", "excludes",
        "No cover for theft of, or damage to, the car if it was left unattended, unlocked and with the keys left in the car.",
        22, "theft or damage to your car if the car is left unattended")

    add("exclusion", "tyre_damage", "excluded_tyre_damage_specific_causes", "excludes",
        "No cover for damage to the car's tyres caused by braking, punctures, road cuts or bursting.",
        22, "damage to your car’s tyres caused by braking")

    add("exclusion", "unlicensed_driver", "excluded_unlicensed_driver_with_exception", "excludes",
        "No cover while the car is driven by someone not licensed, not correctly licensed, or breaching their licence conditions — but the owner (not the driver) can still claim if they weren't driving/in charge, didn't consent to or encourage the driving, and can show they didn't know and couldn't reasonably have known.",
        23, "your car being driven by, or is in the charge of someone who is not licensed",
        conditions=["driver_unlicensed_or_breaching_conditions", "owner_can_prove_no_knowledge_or_consent"])

    add("exclusion", "unregistered_car", "excluded_unregistered_car_with_exception", "excludes",
        "No cover while the car is unregistered at the time of the incident, unless the loss/damage/liability wasn't caused by or didn't result from the car being unregistered.",
        23, "your car being used at the time of an incident if it was unregistered")

    # --- Excess rules ---------------------------------------------------------
    add("definition", "excess", "excess_definition", "defines",
        "An excess is the amount the policyholder pays towards the cost of a claim for each incident covered; more than one type of excess may apply depending on the claim's circumstances, and the amounts/types are shown on the certificate of insurance.",
        12, "An excess is the amount you pay towards the cost of your claim")

    add("condition", "not_at_fault_excess_waiver", "excess_waived_if_at_fault_details_supplied", "permits",
        "The standard excess is waived if the policyholder can show they/the driver didn't contribute to the accident and can supply the at-fault driver's name and address AND the at-fault vehicle's registration number; if any of these three items is missing, the excess is payable.",
        14, "You or the driver didn’t contribute to the accident",
        conditions=["not_at_fault", "at_fault_driver_name_and_address_supplied", "at_fault_vehicle_registration_supplied"])

    add("rule", "excess_types", "excess_stacking_rule", "requires",
        "Multiple excess types can apply to the same claim (standard, AAMI Flexi-Premiums, age, driver history, inexperienced driver) and are additive except the standard excess is the base one all others stack on top of.",
        13, "Standard excess This excess applies to all claims")

    # --- Windscreen and window glass cover -----------------------------------
    add("rule", "windscreen_cover", "windscreen_cover_scope_and_excess_free", "covers",
        "Where the only damage to the car from a covered incident is to the windscreen or window glass (including sunroof), the reasonable cost to repair or replace it is covered without an excess, limited to one excess-free claim per period of insurance.",
        42, "When the only damage to your car following an incident",
        conditions=["only_damage_is_windscreen_or_window_glass", "within_period_of_insurance"])

    add("condition", "windscreen_chip_repair", "chip_repair_does_not_use_excess_free_claim", "permits",
        "A chipped (not cracked) windscreen that can be safely repaired is covered without an excess and without using up the one excess-free 'Windscreen and window glass' claim for the period.",
        42, "Where the damage is a chipped windscreen that has not cracked")

    add("rule", "windscreen_settlement", "windscreen_repair_or_replace_choice", "requires",
        "If a windscreen/window glass claim is paid, AAMI chooses to either repair the chip/crack, or replace the damaged windscreen or window glass.",
        48, "If we pay a claim for damaged windscreen or window glass")

    # --- Third Party Property Damage / caravans/trailers cross-cover rule ---
    add("condition", "tpp_caravan_exclusivity", "cannot_claim_tpp_and_caravan_tpp_for_same_incident", "denies",
        "If a Third Party Property Damage claim is accepted for an incident, the same incident cannot also be claimed under the separate 'Third Party Property Damage cover for caravans and trailers' benefit.",
        27, "If we accept a claim for Third Party Property Damage")

    # --- Making a claim / evidence requirements ------------------------------
    add("data_requirement", "claim_evidence", "must_prove_incident_occurred", "requires",
        "When making a claim, the policyholder must be able to prove that a covered incident actually took place; if this can't be shown, the claim cannot be paid. AAMI may seek supporting material from police.",
        47, "When making a claim you must be able to prove that an incident")

    add("data_requirement", "total_loss_process", "must_allow_recovery_of_total_loss_vehicle", "requires",
        "If the car is a total loss, the policyholder must allow AAMI (or its nominee) to recover, salvage or take possession of the car.",
        46, "if your car is a total loss, allow us or a person nominated by us")

    # --- Total loss / write-off -----------------------------------------------
    add("definition", "total_loss", "total_loss_definition", "defines",
        "A car becomes a total loss when it is uneconomical or unsafe to repair, including when combined repair cost and salvage value are likely to exceed the amount covered by the policy; the relevant State/Territory's legal write-off criteria are also taken into account.",
        51, "it is uneconomical or unsafe to repair, including where the combined repair costs")

    add("rule", "total_loss_deductions", "total_loss_settlement_deductions", "requires",
        "On a total loss settlement, AAMI pays the amount covered on the certificate of insurance less deductions including any excess, unpaid premium/instalments, and any excess arising from hire-car damage.",
        51, "excesses;")

    add("rule", "stolen_car_total_loss_timing", "stolen_car_becomes_total_loss_after_14_days", "requires",
        "If a stolen car is found within 14 days it's treated as a damage claim (repair process applies); if not found within 14 days and the theft claim is accepted, the car becomes a total loss.",
        51, "If your car is not found within 14 days after being stolen")

    # --- Additional / optional covers (scoped lightly — see Issue log) --------
    add("rule", "transport_cover", "transport_cover_scope_and_limit", "covers",
        "When the car is damaged in a covered incident, reasonable transport costs (scene to destination, to/from repairer, to/from hire car provider) are covered up to $250 per claim per incident.",
        30, "Up to a total of $250 per claim for any one incident")

    add("condition", "new_car_after_total_loss", "new_car_replacement_eligibility", "permits",
        "If the car is stolen or damaged and accepted as a total loss, AAMI will replace it with a new car if: the policyholder is the first registered owner (or bought it ex-demonstration from the first-owner dealer); the loss/damage occurred less than 2 years from original registration; and any financier consents in writing.",
        32, "you are the first registered owner of your car or you purchased your car")

    add("rule", "hire_car_after_theft", "hire_car_after_theft_up_to_21_days", "covers",
        "After a covered theft of the car, AAMI arranges and pays for a reasonable hire car (or reimburses reasonable transport costs if none is available) for up to 21 days, stopping earlier if the car is returned, repaired, or the claim is settled.",
        33, "After theft of your car that is covered by your policy")

    # --- Definitions relevant to coverage determination -----------------------
    add("definition", "incident_definition", "incident_defined", "defines",
        "An 'incident' (or event) is a single event, accident or occurrence the policyholder did not intend or expect to happen, and that isn't excluded by the policy; a series of incidents from one originating cause counts as a single incident.",
        73, "Incident or event is a single event, accident or occurrence")

    add("definition", "market_value_definition", "market_value_defined", "defines",
        "Market value is what the market would pay for the car (or hire car), based on factors like age, make, model, kilometres and condition; it excludes registration, CTP insurance, stamp duty, transfer fees, dealer warranty costs and dealer delivery.",
        73, "Market value the amount that the market would pay for the car")

    add("definition", "amount_covered_definition", "amount_covered_defined", "defines",
        "'Amount covered' is the maximum AAMI will pay for loss or damage to the car in any one incident (unless stated otherwise); it includes fitted accessories/modifications, registration and CTP insurance, and is shown on the certificate of insurance.",
        72, "Amount covered when used in relation to your car")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(claims, indent=2, ensure_ascii=False))
    print(f"Wrote {len(claims)} claims to {OUT_PATH}")


if __name__ == "__main__":
    main()
