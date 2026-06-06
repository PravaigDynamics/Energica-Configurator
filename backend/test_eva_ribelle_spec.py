"""
Senior Tester -- EVA Ribelle Full Spec Verification
Tests every rule from Paolo's specification document.
Run: PYTHONIOENCODING=utf-8 python test_eva_ribelle_spec.py
"""
import json, hashlib, urllib.request, urllib.error, sys

BASE_URL = "http://127.0.0.1:8000"
PASS = 0; FAIL = 0; ERRORS = []

# Standard default (all required groups satisfied, no extras)
STD = [
    "er_01_base_ribelle_stealth_grey",
    "er_52_standard_suspensions",           # *standard suspension
    "eg_64_standard_cast_aluminium_wheels", # *standard wheels
]

def http_post(endpoint, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE_URL}/{endpoint}", data=data,
          headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def validate(layers):
    _, body = http_post("validate", {"model": "eva_ribelle", "layers": layers})
    return body["valid"], body.get("error")

def render_md5(layers):
    payload = json.dumps({"model": "eva_ribelle", "layers": layers,
                          "format": "jpeg", "quality": 85}).encode()
    req = urllib.request.Request(f"{BASE_URL}/configure", data=payload,
          headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read()
        return hashlib.md5(raw).hexdigest()[:10], len(raw)
    except urllib.error.HTTPError:
        return None, 0

def check(label, condition, details=""):
    global PASS, FAIL
    if condition:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; ERRORS.append(label)
        print(f"  FAIL  {label}")
        if details: print(f"        {details}")

def section(title):
    print(f"\n{'='*62}\n  {title}\n{'='*62}")

def swap(layers, old, new):
    return [l for l in layers if l != old] + [new]

# =========================================================================
# TC-01: BACKGROUND -- optional on/off
# =========================================================================
section("TC-01: BACKGROUND -- optional on/off")

v, _ = validate(STD)
check("Default without background is valid", v)
v, _ = validate(STD + ["background"])
check("With background ON is valid", v)

md5_no_bg, _ = render_md5(STD)
md5_bg, _    = render_md5(STD + ["background"])
check("Render without background succeeds", md5_no_bg is not None)
check("Render with background succeeds",    md5_bg    is not None)
check("Background ON/OFF produces different images", md5_no_bg != md5_bg)

# =========================================================================
# TC-02: #ER-01 BASE-RIBELLE STEALTH GREY -- always on
# =========================================================================
section("TC-02: #ER-01 BASE-RIBELLE STEALTH GREY -- must always be on")

v, err = validate(STD)
check("Valid config with base", v)

no_base = [l for l in STD if l != "er_01_base_ribelle_stealth_grey"]
v, err = validate(no_base)
check("Missing base is REJECTED", not v, err)

v, err = validate(["er_01_base_ribelle_stealth_grey"])
check("Base alone (no required groups) is REJECTED", not v, err)

md5_plain, sz = render_md5(STD)
check("Base render succeeds", md5_plain is not None, f"size={sz:,}b")

# =========================================================================
# TC-03: ER-12 ROSSO CORSA / ER-13 TRICOLORE -- at most one, optional
# =========================================================================
section("TC-03: ER-12 ROSSO CORSA / ER-13 TRICOLORE -- at most one, not required")

v, _ = validate(STD)
check("Both color overlays OFF (pure Stealth Grey) is valid", v)

v, _ = validate(STD + ["er_12_eva_rosso_corsa"])
check("ER-12 Rosso Corsa alone is valid", v)
md5_rosso, _ = render_md5(STD + ["er_12_eva_rosso_corsa"])

v, _ = validate(STD + ["er_13_eva_tricolore"])
check("ER-13 Tricolore alone is valid", v)
md5_tri, _ = render_md5(STD + ["er_13_eva_tricolore"])

v, err = validate(STD + ["er_12_eva_rosso_corsa", "er_13_eva_tricolore"])
check("Both ER-12 + ER-13 ON simultaneously is REJECTED", not v, err)

check("Rosso Corsa differs visually from Stealth Grey",  md5_rosso != md5_plain)
check("Tricolore differs visually from Stealth Grey",    md5_tri   != md5_plain)
check("Rosso Corsa differs visually from Tricolore",     md5_rosso != md5_tri)

# Colors work with all other options
v, _ = validate(STD + ["er_12_eva_rosso_corsa", "er_24_frame_black"])
check("Rosso Corsa + frame black together is valid", v)
v, _ = validate(STD + ["er_13_eva_tricolore", "er_24_frame_black"])
check("Tricolore + frame black together is valid", v)

# =========================================================================
# TC-04: ER-24 FRAME BLACK -- optional, all color models
# =========================================================================
section("TC-04: ER-24 FRAME BLACK -- optional, works with any color")

v, _ = validate(STD + ["er_24_frame_black"])
check("Frame black ON with Stealth Grey is valid", v)
md5_frame, _ = render_md5(STD + ["er_24_frame_black"])
check("Frame black changes render", md5_plain != md5_frame)

v, _ = validate(STD + ["er_13_eva_tricolore", "er_24_frame_black"])
check("Frame black + Tricolore is valid", v)
v, _ = validate(STD + ["er_12_eva_rosso_corsa", "er_24_frame_black"])
check("Frame black + Rosso Corsa is valid", v)
# Swap standard -> OHLINS, then add frame black + color (correct swap, no duplicates)
frame_rosso_ohlins = swap(STD, "er_52_standard_suspensions", "er_53_kit_ohlins_suspensions")
frame_rosso_ohlins = frame_rosso_ohlins + ["er_12_eva_rosso_corsa", "er_24_frame_black"]
v, err = validate(frame_rosso_ohlins)
check("Frame black + Rosso Corsa + Ohlins (correct swap) is valid", v, err)

# =========================================================================
# TC-05: CARBON PARTS -- any combination, all optional
# =========================================================================
section("TC-05: ER-35/36/37/38 CARBON PARTS -- any combo, all optional")

carbon = {
    "er_35_front_mudguard_carbon": "ER-35 Front Mudguard Carbon",
    "er_36_rear_mudguard_carbon":  "ER-36 Rear Mudguard Carbon",
    "er_37_battery_cover_carbon":  "ER-37 Battery Cover Carbon",
    "er_38_tank_rib_carbon":       "ER-38 Tank Rib Carbon",
}

for cid, cname in carbon.items():
    v, err = validate(STD + [cid])
    check(f"{cname} alone is valid", v, err)
    md5_c, _ = render_md5(STD + [cid])
    check(f"{cname} changes render", md5_c != md5_plain)

all_carbon = list(carbon.keys())
v, err = validate(STD + all_carbon)
check("ALL four carbon parts ON simultaneously is valid", v, err)
md5_all_c, _ = render_md5(STD + all_carbon)
check("All carbon parts changes render vs plain", md5_all_c != md5_plain)

v, _ = validate(STD + ["er_35_front_mudguard_carbon", "er_38_tank_rib_carbon"])
check("Front mudguard + tank rib (partial combo) is valid", v)
v, _ = validate(STD + ["er_36_rear_mudguard_carbon", "er_37_battery_cover_carbon"])
check("Rear mudguard + battery cover (partial combo) is valid", v)

# Carbon parts work with all color variants
v, _ = validate(STD + ["er_12_eva_rosso_corsa"] + all_carbon)
check("All carbon parts + Rosso Corsa is valid", v)
v, _ = validate(STD + ["er_13_eva_tricolore"] + all_carbon)
check("All carbon parts + Tricolore is valid", v)

# =========================================================================
# TC-06: RS VERSION + STICKERS -- RS optional, stickers require RS
# =========================================================================
section("TC-06: ER-40 RS VERSION / ER-41 STICKERS -- RS optional, stickers require RS")

v, _ = validate(STD + ["er_40_rs_version"])
check("ER-40 RS version alone is valid", v)
md5_rs, _ = render_md5(STD + ["er_40_rs_version"])
check("RS version changes render", md5_plain != md5_rs)

v, _ = validate(STD + ["er_40_rs_version", "er_41_stickers_kit_rs_sport"])
check("ER-40 + ER-41 stickers together is valid", v)
md5_rs_stk, _ = render_md5(STD + ["er_40_rs_version", "er_41_stickers_kit_rs_sport"])
check("Stickers + RS differs from RS alone", md5_rs != md5_rs_stk)

# REJECT: stickers without RS version
v, err = validate(STD + ["er_41_stickers_kit_rs_sport"])
check("ER-41 stickers WITHOUT ER-40 RS version is REJECTED", not v, err)

# RS works with all color variants
v, _ = validate(STD + ["er_12_eva_rosso_corsa", "er_40_rs_version", "er_41_stickers_kit_rs_sport"])
check("RS + stickers + Rosso Corsa is valid", v)
v, _ = validate(STD + ["er_13_eva_tricolore", "er_40_rs_version"])
check("RS + Tricolore is valid", v)

# =========================================================================
# TC-07: SUSPENSION -- exactly one always active
# =========================================================================
section("TC-07: SUSPENSION -- exactly one always active")

v, _ = validate(STD)
check("*ER-52 standard suspension (default) is valid", v)

ohlins = swap(STD, "er_52_standard_suspensions", "er_53_kit_ohlins_suspensions")
v, err = validate(ohlins)
check("ER-53 OHLINS suspension is valid", v, err)
md5_ohlins, _ = render_md5(ohlins)
md5_std_s, _  = render_md5(STD)
check("OHLINS differs visually from standard suspension", md5_ohlins != md5_std_s)

v, err = validate(STD + ["er_53_kit_ohlins_suspensions"])
check("Both suspensions simultaneously is REJECTED", not v, err)

no_susp = [l for l in STD if l != "er_52_standard_suspensions"]
v, err = validate(no_susp)
check("No suspension selected is REJECTED", not v, err)

# =========================================================================
# TC-08: WHEELS -- exactly one of four always active
# =========================================================================
section("TC-08: WHEELS -- exactly one of four always active (EG-64/ES-65/EG-66/EG-67)")

v, _ = validate(STD)
check("*EG-64 standard wheels (default) is valid", v)

for wid, wname in [
    ("es_65_red_stripe_cast_wheels", "ES-65 Red Stripe Cast"),
    ("eg_66_forged_aluminium_wheels","EG-66 Forged Aluminium"),
    ("eg_67_carbon_fiber_wheels",    "EG-67 Carbon Fiber"),
]:
    wlayers = swap(STD, "eg_64_standard_cast_aluminium_wheels", wid)
    v, err = validate(wlayers)
    check(f"{wname} wheels is valid", v, err)
    md5_w, _ = render_md5(wlayers)
    md5_sw, _ = render_md5(STD)
    check(f"{wname} wheels differ visually from standard", md5_w != md5_sw)

# REJECT: two wheel types
v, err = validate(STD + ["es_65_red_stripe_cast_wheels"])
check("Standard + Red Stripe simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["eg_66_forged_aluminium_wheels"])
check("Standard + Forged simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["eg_67_carbon_fiber_wheels"])
check("Standard + Carbon Fiber simultaneously is REJECTED", not v, err)

forged_and_carbon = swap(STD, "eg_64_standard_cast_aluminium_wheels", "eg_66_forged_aluminium_wheels")
v, err = validate(forged_and_carbon + ["eg_67_carbon_fiber_wheels"])
check("Forged + Carbon Fiber simultaneously is REJECTED", not v, err)

# REJECT: no wheels
no_wheels = [l for l in STD if l != "eg_64_standard_cast_aluminium_wheels"]
v, err = validate(no_wheels)
check("No wheels selected is REJECTED", not v, err)

# =========================================================================
# TC-09: ERGAL SCREWS -- at most one (or none)
# =========================================================================
section("TC-09: ERGAL SCREWS -- at most one (ER-78 Gold / ER-79 Black)")

v, _ = validate(STD)
check("No ergal screws is valid", v)

v, _ = validate(STD + ["er_78_kit_ergal_screws_gold"])
check("ER-78 Gold ergal screws is valid", v)
md5_gold, _ = render_md5(STD + ["er_78_kit_ergal_screws_gold"])
check("Gold ergal changes render", md5_gold != md5_plain)

v, _ = validate(STD + ["er_79_kit_ergal_screws_black"])
check("ER-79 Black ergal screws is valid", v)
md5_blk, _ = render_md5(STD + ["er_79_kit_ergal_screws_black"])
check("Black ergal changes render", md5_blk != md5_plain)

v, err = validate(STD + ["er_78_kit_ergal_screws_gold", "er_79_kit_ergal_screws_black"])
check("Both Gold + Black ergal simultaneously is REJECTED", not v, err)

check("Gold vs Black ergal renders differ", md5_gold != md5_blk)

# Ergal works with all color variants
v, _ = validate(STD + ["er_12_eva_rosso_corsa", "er_78_kit_ergal_screws_gold"])
check("Gold ergal + Rosso Corsa is valid", v)
v, _ = validate(STD + ["er_13_eva_tricolore", "er_79_kit_ergal_screws_black"])
check("Black ergal + Tricolore is valid", v)

# =========================================================================
# TC-10: WINDSCREEN KIT -- optional, all configurations
# =========================================================================
section("TC-10: ER-80 WINDSCREEN KIT -- optional, all configurations")

v, _ = validate(STD + ["er_80_windscreen_kit"])
check("Windscreen kit ON is valid", v)
md5_ws, _ = render_md5(STD + ["er_80_windscreen_kit"])
check("Windscreen kit changes render", md5_plain != md5_ws)

v, _ = validate(STD + ["er_12_eva_rosso_corsa", "er_80_windscreen_kit"])
check("Windscreen + Rosso Corsa is valid", v)
v, _ = validate(STD + ["er_13_eva_tricolore", "er_80_windscreen_kit"])
check("Windscreen + Tricolore is valid", v)

# =========================================================================
# TC-11: SPLASH GUARD -- optional, all configurations
# =========================================================================
section("TC-11: ER-81 SPLASH GUARD -- optional")

v, _ = validate(STD + ["er_81_splash_guard"])
check("Splash guard ON is valid", v)
md5_sg, _ = render_md5(STD + ["er_81_splash_guard"])
check("Splash guard changes render", md5_plain != md5_sg)

v, _ = validate(STD + ["er_12_eva_rosso_corsa", "er_81_splash_guard"])
check("Splash guard + Rosso Corsa is valid", v)
v, _ = validate(STD + ["er_80_windscreen_kit", "er_81_splash_guard"])
check("Windscreen + splash guard together is valid", v)

# =========================================================================
# TC-12: SIDE BAGS KIT -- optional, all configurations
# =========================================================================
section("TC-12: ER-91 SIDE BAGS KIT -- optional")

v, _ = validate(STD + ["er_91_side_bags_kit"])
check("Side bags kit ON is valid", v)
md5_bags, _ = render_md5(STD + ["er_91_side_bags_kit"])
check("Side bags changes render", md5_plain != md5_bags)

v, _ = validate(STD + ["er_13_eva_tricolore", "er_91_side_bags_kit"])
check("Side bags + Tricolore is valid", v)

# =========================================================================
# TC-13: BAGS PLATES -- at most one (both off = standard titanium)
# =========================================================================
section("TC-13: BAGS PLATES -- ER-92 Red / ER-93 Gun Metal, at most one")

v, _ = validate(STD)
check("Both plates OFF (standard titanium) is valid", v)

v, _ = validate(STD + ["er_91_side_bags_kit", "er_92_bags_plates_red"])
check("ER-92 Red plates (with bags) is valid", v)
md5_red_p, _ = render_md5(STD + ["er_91_side_bags_kit", "er_92_bags_plates_red"])

v, _ = validate(STD + ["er_91_side_bags_kit", "er_93_bags_plates_gun_metal"])
check("ER-93 Gun Metal plates (with bags) is valid", v)
md5_gm_p, _ = render_md5(STD + ["er_91_side_bags_kit", "er_93_bags_plates_gun_metal"])

v, err = validate(STD + ["er_91_side_bags_kit",
                          "er_92_bags_plates_red", "er_93_bags_plates_gun_metal"])
check("Both ER-92 + ER-93 simultaneously is REJECTED", not v, err)

md5_no_plate, _ = render_md5(STD + ["er_91_side_bags_kit"])
check("Red plates change render",      md5_red_p != md5_no_plate)
check("Gun Metal plates change render", md5_gm_p  != md5_no_plate)
check("Red vs Gun Metal plates differ", md5_red_p != md5_gm_p)

# Plates without bags kit (validator accepts, bags kit not strictly required)
v, _ = validate(STD + ["er_92_bags_plates_red"])
check("Bags plate without bags kit accepted by validator", v)

# =========================================================================
# TC-14: COMBINED CONFIGURATIONS -- realistic scenarios
# =========================================================================
section("TC-14: COMBINED CONFIGURATIONS -- realistic scenarios")

# Scenario A: Tricolore + Ohlins + Carbon wheels + Frame black + all carbon + RS + stickers + Gold ergal + windscreen + bags + red plates
scenario_a = [
    "er_01_base_ribelle_stealth_grey",
    "er_13_eva_tricolore",
    "er_24_frame_black",
    "er_35_front_mudguard_carbon", "er_36_rear_mudguard_carbon",
    "er_37_battery_cover_carbon",  "er_38_tank_rib_carbon",
    "er_40_rs_version",
    "er_41_stickers_kit_rs_sport",
    "er_53_kit_ohlins_suspensions",
    "eg_67_carbon_fiber_wheels",
    "er_78_kit_ergal_screws_gold",
    "er_80_windscreen_kit",
    "er_81_splash_guard",
    "er_91_side_bags_kit",
    "er_92_bags_plates_red",
    "background",
]
v, err = validate(scenario_a)
check("Scenario A: Tricolore+Ohlins+CarbonWheels+AllCarbon+RS+Stickers+GoldErgal+Wind+Splash+Bags+RedPlates -- valid", v, err)
md5_a, sz_a = render_md5(scenario_a)
check("Scenario A renders successfully", md5_a is not None, f"{sz_a:,}b")

# Scenario B: Rosso Corsa + Forged wheels + Black ergal + Splash + Bags + Gun Metal plates
scenario_b = [
    "er_01_base_ribelle_stealth_grey",
    "er_12_eva_rosso_corsa",
    "er_52_standard_suspensions",
    "eg_66_forged_aluminium_wheels",
    "er_79_kit_ergal_screws_black",
    "er_81_splash_guard",
    "er_91_side_bags_kit",
    "er_93_bags_plates_gun_metal",
]
v, err = validate(scenario_b)
check("Scenario B: RossoCorsa+Forged+BlackErgal+Splash+Bags+GunMetalPlates -- valid", v, err)
md5_b, sz_b = render_md5(scenario_b)
check("Scenario B renders successfully", md5_b is not None, f"{sz_b:,}b")

# Scenario C: Pure Stealth Grey + Red Stripe wheels + RS + windscreen + splash
scenario_c = [
    "er_01_base_ribelle_stealth_grey",
    "er_52_standard_suspensions",
    "es_65_red_stripe_cast_wheels",
    "er_40_rs_version",
    "er_80_windscreen_kit",
    "er_81_splash_guard",
]
v, err = validate(scenario_c)
check("Scenario C: StealthGrey+RedStripe+RS+Windscreen+Splash -- valid", v, err)
md5_c, sz_c = render_md5(scenario_c)
check("Scenario C renders successfully", md5_c is not None, f"{sz_c:,}b")

# Scenario D: Minimal standard
v, err = validate(STD)
check("Scenario D: Minimal standard is valid", v, err)
md5_d, _ = render_md5(STD)
check("Scenario D renders successfully", md5_d is not None)

check("All 4 scenarios produce different renders", len({md5_a, md5_b, md5_c, md5_d}) == 4)

# FAIL combinations
v, err = validate(STD + ["er_12_eva_rosso_corsa", "er_13_eva_tricolore"])
check("Both color overlays active is REJECTED", not v, err)

v, err = validate(STD + ["er_52_standard_suspensions", "er_53_kit_ohlins_suspensions"])
check("Both suspensions simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["eg_64_standard_cast_aluminium_wheels", "eg_67_carbon_fiber_wheels"])
check("Two wheel types simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["er_78_kit_ergal_screws_gold", "er_79_kit_ergal_screws_black"])
check("Both ergal types simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["er_92_bags_plates_red", "er_93_bags_plates_gun_metal"])
check("Both bags plate colors simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["er_41_stickers_kit_rs_sport"])
check("Stickers without RS version is REJECTED", not v, err)

no_susp = [l for l in STD if l != "er_52_standard_suspensions"]
v, err = validate(no_susp)
check("No suspension is REJECTED", not v, err)

no_wheels = [l for l in STD if l != "eg_64_standard_cast_aluminium_wheels"]
v, err = validate(no_wheels)
check("No wheels is REJECTED", not v, err)

no_base = [l for l in STD if l != "er_01_base_ribelle_stealth_grey"]
v, err = validate(no_base)
check("No base is REJECTED", not v, err)

# =========================================================================
# SUMMARY
# =========================================================================
total = PASS + FAIL
print(f"\n{'='*62}")
print(f"  EVA RIBELLE SPEC TEST RESULTS")
print(f"{'='*62}")
print(f"  TOTAL  : {total}")
print(f"  PASSED : {PASS}")
print(f"  FAILED : {FAIL}")
if ERRORS:
    print(f"\n  Failed tests:")
    for e in ERRORS: print(f"    - {e}")
print(f"{'='*62}")
sys.exit(0 if FAIL == 0 else 1)
