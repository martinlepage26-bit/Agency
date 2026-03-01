def calculate_agency(intake):
    # Tier A shapes numeric scoring and caps.
    # Base subscores /25
    p_lat, r_band, r_acc, s_leg = 20.0, 20.0, 20.0, 20.0
    caps = []

    # Logic: Isolation (Tier A) caps Perceptual Latitude
    signals = intake.get("signals", [])
    if any(i["tier"] == "A" and "isolated" in i["value"].lower() for i in signals):
        p_lat = 12.0
        caps.append("Tier A Cap: Social Isolation (Limit 12)")

    # Logic: Clinical Load (Tier A) caps Regulatory Bandwidth
    constraints = intake.get("constraints", [])
    if any(i["tier"] == "A" and "high stress" in i["value"].lower() for i in constraints):
        r_band = 8.0
        caps.append("Tier A Cap: Allostatic Overload (Limit 8)")

    total = p_lat + r_band + r_acc + s_leg
    return {
        "agency_total": total,
        "subscores": {
            "perceptual_latitude": {"score": p_lat, "caps_applied": caps},
            "regulatory_bandwidth": {"score": r_band, "caps_applied": caps if r_band < 20 else []},
            "resource_access": {"score": r_acc, "caps_applied": []},
            "social_legibility": {"score": s_leg, "caps_applied": []}
        }
    }
