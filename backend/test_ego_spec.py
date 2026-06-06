"""
Senior Tester -- EGO Full Spec Verification
Tests every rule from Paolo's specification document.
Run: PYTHONIOENCODING=utf-8 python test_ego_spec.py
"""
import json, hashlib, urllib.request, urllib.error, sys

BASE_URL = "http://127.0.0.1:8000"
PASS = 0; FAIL = 0; ERRORS = []

# Standard default (all required groups satisfied, no extras)
STD = [
    "eg_01_base_ego_metal_black",
    "eg_62_passenger_seat_standard",       # *standard seat
    "eg_78_standard_suspensions",          # *standard suspension
    "eg_80_standard_cast_aluminium_wheels",# *standard wheels
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
    _, body = http_post("validate", {"model": "ego", "layers": layers})
    return body["valid"], body.get("error")

def render_md5(layers):
    payload = json.dumps({"model":"ego","layers":layers,"format":"jpeg","quality":85}).encode()
    req = urllib.request.Request(f"{BASE_URL}/configure", data=payload,
          headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        return hashlib.md5(raw).hexdigest()[:10], len(raw)
    except urllib.error.HTTPError:
        return None, 0

def check(label, condition, details=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        ERRORS.append(label)
        print(f"  FAIL  {label}")
        if details: print(f"        {details}")

def section(title):
    print(f"\n{'='*62}\n  {title}\n{'='*62}")

# swap one required group layer for another
def swap(layers, old, new):
    return [l for l in layers if l != old] + [new]

# =========================================================================
# TC-01: BACKGROUND - optional on/off
# =========================================================================
section("TC-01: BACKGROUND -- optional on/off")

v, _ = validate(STD)
check("Default without background is valid", v)
v, _ = validate(STD + ["background"])
check("With background ON is valid", v)
md5_no_bg, _ = render_md5(STD)
md5_bg,    _ = render_md5(STD + ["background"])
check("Render without background succeeds", md5_no_bg is not None)
check("Render with background succeeds",    md5_bg    is not None)
check("Background ON/OFF produces different images", md5_no_bg != md5_bg)

# =========================================================================
# TC-02: #EG-01 BASE - always on
# =========================================================================
section("TC-02: #EG-01 BASE-EGO METAL BLACK -- must always be on")

v, err = validate(STD)
check("Valid config with base", v)

no_base = [l for l in STD if l != "eg_01_base_ego_metal_black"]
v, err = validate(no_base)
check("Missing base is REJECTED", not v, err)

v, err = validate(["eg_01_base_ego_metal_black"])
check("Base alone (no required groups) is REJECTED", not v, err)

md5_base, sz = render_md5(STD)
check("Base render succeeds", md5_base is not None, f"size={sz:,}b")

# =========================================================================
# TC-03: EG-12 ROSSO CORSA / EG-13 TRICOLORE - at most one, optional
# =========================================================================
section("TC-03: EG-12 ROSSO CORSA / EG-13 TRICOLORE -- at most one")

v, _ = validate(STD)
check("Both colors OFF (pure metal black) is valid", v)

v, _ = validate(STD + ["eg_12_ego_rosso_corsa"])
check("EG-12 Rosso Corsa alone is valid", v)
md5_rosso, _ = render_md5(STD + ["eg_12_ego_rosso_corsa"])

v, _ = validate(STD + ["eg_13_tricolore"])
check("EG-13 Tricolore alone is valid", v)
md5_tri, _ = render_md5(STD + ["eg_13_tricolore"])

v, err = validate(STD + ["eg_12_ego_rosso_corsa", "eg_13_tricolore"])
check("Both colors ON simultaneously is REJECTED", not v, err)

md5_plain, _ = render_md5(STD)
check("Rosso Corsa differs visually from plain metal black", md5_rosso != md5_plain)
check("Tricolore differs visually from plain metal black",   md5_tri   != md5_plain)
check("Rosso Corsa differs visually from Tricolore",         md5_rosso != md5_tri)

# =========================================================================
# TC-04: EG-24 FRAME BLACK - optional, all color models
# =========================================================================
section("TC-04: EG-24 FRAME BLACK -- optional, works with any color")

v, _ = validate(STD + ["eg_24_frame_black"])
check("Frame black ON with metal black is valid", v)
md5_frame, _ = render_md5(STD + ["eg_24_frame_black"])
check("Frame black changes render", md5_plain != md5_frame)

v, _ = validate(STD + ["eg_13_tricolore", "eg_24_frame_black"])
check("Frame black + Tricolore together is valid", v)
v, _ = validate(STD + ["eg_12_ego_rosso_corsa", "eg_24_frame_black"])
check("Frame black + Rosso Corsa together is valid", v)

# =========================================================================
# TC-05: CARBON PARTS - any combination, all optional
# =========================================================================
section("TC-05: EG-35/36/37/38 CARBON PARTS -- any combo, all optional")

v, _ = validate(STD + ["eg_35_front_mudguard_carbon"])
check("Front mudguard carbon alone is valid", v)
v, _ = validate(STD + ["eg_36_rear_mudguard_carbon"])
check("Rear mudguard carbon alone is valid", v)
v, _ = validate(STD + ["eg_37_bellypan_carbon"])
check("Bellypan carbon alone is valid", v)
v, _ = validate(STD + ["eg_38_undertail_cover_carbon"])
check("Undertail cover carbon alone is valid", v)

all_carbon = ["eg_35_front_mudguard_carbon", "eg_36_rear_mudguard_carbon",
              "eg_37_bellypan_carbon", "eg_38_undertail_cover_carbon"]
v, _ = validate(STD + all_carbon)
check("ALL four carbon parts ON simultaneously is valid", v)

md5_all_c, _ = render_md5(STD + all_carbon)
check("All carbon parts changes render", md5_plain != md5_all_c)

# Partial combos
v, _ = validate(STD + ["eg_35_front_mudguard_carbon", "eg_38_undertail_cover_carbon"])
check("Front + undertail carbon (partial combo) is valid", v)

# =========================================================================
# TC-06: EG-49 RS VERSION - optional
# =========================================================================
section("TC-06: EG-49 RS VERSION -- optional")

v, _ = validate(STD + ["eg_49_rs_version"])
check("RS version ON is valid", v)
md5_rs, _ = render_md5(STD + ["eg_49_rs_version"])
check("RS version changes render", md5_plain != md5_rs)

# =========================================================================
# TC-07: RIDER SEATS - EG-50 and EG-51 - at most one
# =========================================================================
section("TC-07: RIDER SEATS -- EG-50 and EG-51 at most one simultaneously")

# Rider seats with correct passenger seat
# EG-50 needs EG-63, EG-65, EG-66, EG-67, or EG-68
# EG-51 needs EG-64, EG-65, EG-66, EG-67, or EG-68

# VALID: EG-50 + EG-63 (red tech combo)
std_red_rider = swap(STD, "eg_62_passenger_seat_standard", "eg_63_passenger_seat_ego_tech_red")
v, err = validate(std_red_rider + ["eg_50_rider_seat_ego_tech_red"])
check("EG-50 red rider + EG-63 red passenger is valid", v, err)

# VALID: EG-51 + EG-64 (green tech combo)
std_green_rider = swap(STD, "eg_62_passenger_seat_standard", "eg_64_passenger_seat_ego_tech_green")
v, err = validate(std_green_rider + ["eg_51_rider_seat_ego_tech_green"])
check("EG-51 green rider + EG-64 green passenger is valid", v, err)

# VALID: EG-50 + covers (EG-65, EG-66, EG-67, EG-68)
for cover_id, cover_name in [
    ("eg_65_cover_corsaclienti_grey",     "EG-65 grey cover"),
    ("eg_66_cover_corsaclienti_white",    "EG-66 white cover"),
    ("eg_67_cover_corsaclienti_black",    "EG-67 black cover"),
    ("eg_68_cover_corsaclienti_red_copia","EG-68 red cover"),
]:
    layers = swap(STD, "eg_62_passenger_seat_standard", cover_id)
    v, err = validate(layers + ["eg_50_rider_seat_ego_tech_red"])
    check(f"EG-50 red rider + {cover_name} is valid", v, err)

# VALID: EG-51 + covers
for cover_id, cover_name in [
    ("eg_65_cover_corsaclienti_grey",  "EG-65 grey cover"),
    ("eg_66_cover_corsaclienti_white", "EG-66 white cover"),
    ("eg_67_cover_corsaclienti_black", "EG-67 black cover"),
    ("eg_68_cover_corsaclienti_red_copia","EG-68 red cover"),
]:
    layers = swap(STD, "eg_62_passenger_seat_standard", cover_id)
    v, err = validate(layers + ["eg_51_rider_seat_ego_tech_green"])
    check(f"EG-51 green rider + {cover_name} is valid", v, err)

# INVALID: EG-50 + EG-51 simultaneously
std_red = swap(STD, "eg_62_passenger_seat_standard", "eg_63_passenger_seat_ego_tech_red")
v, err = validate(std_red + ["eg_50_rider_seat_ego_tech_red", "eg_51_rider_seat_ego_tech_green"])
check("EG-50 + EG-51 both ON is REJECTED", not v, err)

# INVALID: EG-50 with standard seat (incompatible)
v, err = validate(STD + ["eg_50_rider_seat_ego_tech_red"])
check("EG-50 with standard seat (EG-62) is REJECTED", not v, err)

# INVALID: EG-51 with standard seat (incompatible)
v, err = validate(STD + ["eg_51_rider_seat_ego_tech_green"])
check("EG-51 with standard seat (EG-62) is REJECTED", not v, err)

# INVALID: EG-50 + EG-64 green seat (wrong pairing)
std_green_seat = swap(STD, "eg_62_passenger_seat_standard", "eg_64_passenger_seat_ego_tech_green")
v, err = validate(std_green_seat + ["eg_50_rider_seat_ego_tech_red"])
check("EG-50 red rider + EG-64 green seat is REJECTED (wrong pairing)", not v, err)

# INVALID: EG-51 + EG-63 red seat (wrong pairing)
std_red_seat = swap(STD, "eg_62_passenger_seat_standard", "eg_63_passenger_seat_ego_tech_red")
v, err = validate(std_red_seat + ["eg_51_rider_seat_ego_tech_green"])
check("EG-51 green rider + EG-63 red seat is REJECTED (wrong pairing)", not v, err)

# INVALID: EG-50 with no matching passenger seat at all
v, err = validate(["eg_01_base_ego_metal_black", "eg_78_standard_suspensions",
                   "eg_80_standard_cast_aluminium_wheels", "eg_50_rider_seat_ego_tech_red"])
check("EG-50 rider with no passenger seat is REJECTED", not v, err)

# Visual render difference
md5_rider_red, _   = render_md5(std_red_rider + ["eg_50_rider_seat_ego_tech_red"])
md5_rider_green, _ = render_md5(std_green_rider + ["eg_51_rider_seat_ego_tech_green"])
check("Red rider seat render differs from plain", md5_rider_red   != md5_plain)
check("Green rider seat render differs from plain", md5_rider_green != md5_plain)
check("Red and green rider seats differ",        md5_rider_red   != md5_rider_green)

# =========================================================================
# TC-08: PASSENGER SEAT GROUP - exactly one always active
# =========================================================================
section("TC-08: PASSENGER SEAT -- exactly one of 7 must always be active")

# Each option valid alone
for seat_id, seat_name in [
    ("eg_62_passenger_seat_standard",        "*EG-62 standard"),
    ("eg_63_passenger_seat_ego_tech_red",    "EG-63 tech red"),
    ("eg_64_passenger_seat_ego_tech_green",  "EG-64 tech green"),
    ("eg_65_cover_corsaclienti_grey",        "EG-65 cover grey"),
    ("eg_66_cover_corsaclienti_white",       "EG-66 cover white"),
    ("eg_67_cover_corsaclienti_black",       "EG-67 cover black"),
    ("eg_68_cover_corsaclienti_red_copia",   "EG-68 cover red"),
]:
    layers = swap(STD, "eg_62_passenger_seat_standard", seat_id)
    v, err = validate(layers)
    check(f"{seat_name} alone is valid", v, err)

# Two passenger seats simultaneously rejected
v, err = validate(STD + ["eg_63_passenger_seat_ego_tech_red"])
check("Two passenger seats simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["eg_65_cover_corsaclienti_grey"])
check("Standard + cover together is REJECTED", not v, err)

# No passenger seat rejected
no_seat = [l for l in STD if l != "eg_62_passenger_seat_standard"]
v, err = validate(no_seat)
check("No passenger seat is REJECTED", not v, err)

# =========================================================================
# TC-09: SUSPENSION - exactly one always active
# =========================================================================
section("TC-09: SUSPENSION -- exactly one always active")

v, _ = validate(STD)
check("*EG-78 standard suspension (default) is valid", v)

ohlins = swap(STD, "eg_78_standard_suspensions", "eg_79_kit_ohlins_suspensions")
v, _ = validate(ohlins)
check("EG-79 OHLINS suspension is valid", v)
md5_ohlins, _ = render_md5(ohlins)
md5_std_susp, _ = render_md5(STD)
check("OHLINS suspension differs visually from standard", md5_ohlins != md5_std_susp)

v, err = validate(STD + ["eg_79_kit_ohlins_suspensions"])
check("Both suspensions simultaneously is REJECTED", not v, err)

no_susp = [l for l in STD if l != "eg_78_standard_suspensions"]
v, err = validate(no_susp)
check("No suspension selected is REJECTED", not v, err)

# =========================================================================
# TC-10: WHEELS - exactly one of four always active
# =========================================================================
section("TC-10: WHEELS -- exactly one of four always active")

v, _ = validate(STD)
check("*EG-80 standard wheels (default) is valid", v)

for wid, wname in [
    ("eg_81_red_stripe_cast_wheels", "EG-81 red stripe"),
    ("eg_82_forged_aluminium_wheels","EG-82 forged"),
    ("eg_83_carbon_fiber_wheels",    "EG-83 carbon fiber"),
]:
    wlayers = swap(STD, "eg_80_standard_cast_aluminium_wheels", wid)
    v, err = validate(wlayers)
    check(f"{wname} wheels is valid", v, err)
    md5_w, _ = render_md5(wlayers)
    md5_std_w, _ = render_md5(STD)
    check(f"{wname} wheels differ visually from standard", md5_w != md5_std_w)

# Two wheel types rejected
v, err = validate(STD + ["eg_81_red_stripe_cast_wheels"])
check("Two wheel types simultaneously is REJECTED", not v, err)
v, err = validate(STD + ["eg_83_carbon_fiber_wheels"])
check("Standard + carbon fiber wheels is REJECTED", not v, err)

# No wheels rejected
no_wheels = [l for l in STD if l != "eg_80_standard_cast_aluminium_wheels"]
v, err = validate(no_wheels)
check("No wheels selected is REJECTED", not v, err)

# =========================================================================
# TC-11: ERGAL SCREWS - at most one, both optional
# =========================================================================
section("TC-11: ERGAL SCREWS -- at most one (or none)")

v, _ = validate(STD)
check("No ergal screws is valid", v)

v, _ = validate(STD + ["eg_94_kit_ergal_screws_gold"])
check("EG-94 gold ergal screws is valid", v)
md5_gold, _ = render_md5(STD + ["eg_94_kit_ergal_screws_gold"])

v, _ = validate(STD + ["eg_95_kit_ergal_screws_black"])
check("EG-95 black ergal screws is valid", v)
md5_black, _ = render_md5(STD + ["eg_95_kit_ergal_screws_black"])

v, err = validate(STD + ["eg_94_kit_ergal_screws_gold", "eg_95_kit_ergal_screws_black"])
check("Both ergal types simultaneously is REJECTED", not v, err)

md5_base_r, _ = render_md5(STD)
check("Gold screws change render",  md5_gold  != md5_base_r)
check("Black screws change render", md5_black != md5_base_r)
check("Gold vs black screws differ", md5_gold != md5_black)

# =========================================================================
# TC-12: COMBINED - realistic user scenarios
# =========================================================================
section("TC-12: COMBINED CONFIGURATIONS -- realistic scenarios")

# Scenario A: Tricolore + Ohlins + Carbon fiber wheels + frame black + all carbon + rs + cover grey
scenario_a = [
    "eg_01_base_ego_metal_black",
    "eg_13_tricolore",
    "eg_24_frame_black",
    "eg_35_front_mudguard_carbon", "eg_36_rear_mudguard_carbon",
    "eg_37_bellypan_carbon", "eg_38_undertail_cover_carbon",
    "eg_49_rs_version",
    "eg_65_cover_corsaclienti_grey",
    "eg_79_kit_ohlins_suspensions",
    "eg_83_carbon_fiber_wheels",
    "eg_94_kit_ergal_screws_gold",
    "background",
]
v, err = validate(scenario_a)
check("Scenario A: Tricolore+Ohlins+CarbonWheels+AllCarbon+RS+Cover+Gold -- valid", v, err)
md5_a, sz_a = render_md5(scenario_a)
check("Scenario A renders successfully", md5_a is not None, f"{sz_a:,}b")

# Scenario B: Rosso Corsa + red rider + red tech seat + forged + ohlins + black ergal
scenario_b = [
    "eg_01_base_ego_metal_black",
    "eg_12_ego_rosso_corsa",
    "eg_50_rider_seat_ego_tech_red",
    "eg_63_passenger_seat_ego_tech_red",
    "eg_79_kit_ohlins_suspensions",
    "eg_82_forged_aluminium_wheels",
    "eg_95_kit_ergal_screws_black",
]
v, err = validate(scenario_b)
check("Scenario B: RossoCorsa+RedRider+RedSeat+Forged+Ohlins+BlackErgal -- valid", v, err)
md5_b, sz_b = render_md5(scenario_b)
check("Scenario B renders successfully", md5_b is not None, f"{sz_b:,}b")

# Scenario C: Green rider + corsaclienti cover + standard everything
scenario_c = [
    "eg_01_base_ego_metal_black",
    "eg_51_rider_seat_ego_tech_green",
    "eg_66_cover_corsaclienti_white",
    "eg_78_standard_suspensions",
    "eg_81_red_stripe_cast_wheels",
]
v, err = validate(scenario_c)
check("Scenario C: GreenRider+WhiteCover+StdSusp+RedStripe -- valid", v, err)
md5_c, sz_c = render_md5(scenario_c)
check("Scenario C renders successfully", md5_c is not None, f"{sz_c:,}b")

# Scenario D: Pure standard, no extras
v, err = validate(STD)
check("Scenario D: Pure standard metal black -- valid", v, err)
md5_d, _ = render_md5(STD)
check("Scenario D renders successfully", md5_d is not None)

check("All 4 scenarios produce different renders", len({md5_a, md5_b, md5_c, md5_d}) == 4)

# FAIL combinations
v, err = validate(STD + ["eg_12_ego_rosso_corsa", "eg_13_tricolore"])
check("Two colors in full config REJECTED", not v, err)

v, err = validate(STD + ["eg_80_standard_cast_aluminium_wheels", "eg_83_carbon_fiber_wheels"])
check("Two wheel types in full config REJECTED", not v, err)

v, err = validate(STD + ["eg_78_standard_suspensions", "eg_79_kit_ohlins_suspensions"])
check("Two suspensions in full config REJECTED", not v, err)

v, err = validate(STD + ["eg_94_kit_ergal_screws_gold", "eg_95_kit_ergal_screws_black"])
check("Two ergal types in full config REJECTED", not v, err)

# EG-50 with standard seat (wrong pairing in full scenario)
v, err = validate(STD + ["eg_50_rider_seat_ego_tech_red"])
check("EG-50 rider + standard seat (incompatible) REJECTED in full config", not v, err)

# =========================================================================
# SUMMARY
# =========================================================================
total = PASS + FAIL
print(f"\n{'='*62}")
print(f"  EGO SPEC TEST RESULTS")
print(f"{'='*62}")
print(f"  TOTAL  : {total}")
print(f"  PASSED : {PASS}")
print(f"  FAILED : {FAIL}")
if ERRORS:
    print(f"\n  Failed tests:")
    for e in ERRORS: print(f"    - {e}")
print(f"{'='*62}")
sys.exit(0 if FAIL == 0 else 1)
