"""
Senior Tester -- EsseEsse9 Full Spec Verification
Tests every rule from Paolo's specification document.
Run: PYTHONIOENCODING=utf-8 python test_essesse9_spec.py
"""
import json, hashlib, urllib.request, urllib.error, sys

BASE_URL = "http://127.0.0.1:8000"
PASS = 0; FAIL = 0; ERRORS = []

# Standard default (all required groups satisfied, no extras)
STD = [
    "es_01_base_esseesse9_bormio_ice",
    "es_45_standard_suspensions",           # *standard suspension
    "es_57_standard_cast_aluminium_wheels", # *standard wheels
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
    _, body = http_post("validate", {"model": "essesse9", "layers": layers})
    return body["valid"], body.get("error")

def render_md5(layers):
    payload = json.dumps({"model":"essesse9","layers":layers,
                          "format":"jpeg","quality":85}).encode()
    req = urllib.request.Request(f"{BASE_URL}/configure", data=payload,
          headers={"Content-Type":"application/json"}, method="POST")
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
# TC-02: #ES-01 BASE -- always on
# =========================================================================
section("TC-02: #ES-01 BASE-EsseEsse9 BORMIO ICE -- must always be on")

v, err = validate(STD)
check("Valid config with base", v)

no_base = [l for l in STD if l != "es_01_base_esseesse9_bormio_ice"]
v, err = validate(no_base)
check("Missing base is REJECTED", not v, err)

v, err = validate(["es_01_base_esseesse9_bormio_ice"])
check("Base alone (no required groups) is REJECTED", not v, err)

md5_base, sz = render_md5(STD)
check("Base render succeeds", md5_base is not None, f"size={sz:,}b")

# =========================================================================
# TC-03: ES-02 CNC TITANIUM GREY -- only valid for Bormio Ice version
# =========================================================================
section("TC-03: ES-02 CNC TITANIUM GREY -- only for Bormio Ice (no color overlay)")

# Valid: ES-02 active on pure bormio ice (no ES-13/ES-14)
v, err = validate(STD + ["es_02_cnc_titanium_grey"])
check("ES-02 CNC grey ON with base only (Bormio Ice) is valid", v, err)
md5_cnc, _ = render_md5(STD + ["es_02_cnc_titanium_grey"])
check("ES-02 CNC grey changes render", md5_base != md5_cnc)

# INVALID: ES-02 with Sunrise Red (color overlay active)
v, err = validate(STD + ["es_13_esseesse9_sunrise_red", "es_02_cnc_titanium_grey"])
check("ES-02 + ES-13 Sunrise Red is REJECTED (not Bormio Ice version)", not v, err)

# INVALID: ES-02 with Riviera Green (color overlay active)
v, err = validate(STD + ["es_14_esseesse9_riviera_green", "es_02_cnc_titanium_grey"])
check("ES-02 + ES-14 Riviera Green is REJECTED (not Bormio Ice version)", not v, err)

# =========================================================================
# TC-04: ES-13 SUNRISE RED / ES-14 RIVIERA GREEN -- at most one, optional
# =========================================================================
section("TC-04: ES-13 SUNRISE RED / ES-14 RIVIERA GREEN -- at most one")

v, _ = validate(STD)
check("Both color overlays OFF (pure Bormio Ice) is valid", v)

v, _ = validate(STD + ["es_13_esseesse9_sunrise_red"])
check("ES-13 Sunrise Red alone is valid", v)
md5_red, _ = render_md5(STD + ["es_13_esseesse9_sunrise_red"])

v, _ = validate(STD + ["es_14_esseesse9_riviera_green"])
check("ES-14 Riviera Green alone is valid", v)
md5_green, _ = render_md5(STD + ["es_14_esseesse9_riviera_green"])

v, err = validate(STD + ["es_13_esseesse9_sunrise_red", "es_14_esseesse9_riviera_green"])
check("Both ES-13 + ES-14 ON simultaneously is REJECTED", not v, err)

md5_plain, _ = render_md5(STD)
check("Sunrise Red differs visually from Bormio Ice",    md5_red   != md5_plain)
check("Riviera Green differs visually from Bormio Ice",  md5_green != md5_plain)
check("Sunrise Red differs visually from Riviera Green", md5_red   != md5_green)

# =========================================================================
# TC-05: BELLYPAN VARIANTS -- at most one, all optional
# =========================================================================
section("TC-05: BELLYPAN (ES-22 to ES-27) -- at most one, all optional")

bellypans = [
    ("es_22_bellypan_bormio_grey_stripes",           "ES-22 Bormio Grey Stripes"),
    ("es_23_bellypan_sunrise_red_grey_stripes",      "ES-23 Sunrise Red Grey Stripes"),
    ("es_24_bellypan_riviera_green_grey_stripes",    "ES-24 Riviera Green Grey Stripes"),
    ("es_25_bellypan_bormio_yellow_stripes",         "ES-25 Bormio Yellow Stripes"),
    ("es_26_bellypan_sunrise_red_yellow_stripes",    "ES-26 Sunrise Red Yellow Stripes"),
    ("es_27_bellypan_riviera_green_yellow_stripes",  "ES-27 Riviera Green Yellow Stripes"),
]

# Each valid alone
for bid, bname in bellypans:
    v, err = validate(STD + [bid])
    check(f"{bname} alone is valid", v, err)
    md5_b, _ = render_md5(STD + [bid])
    check(f"{bname} changes render", md5_b != md5_plain)

# No bellypan is valid (optional)
v, _ = validate(STD)
check("No bellypan selected is valid (all optional)", v)

# REJECT: two bellypans simultaneously
v, err = validate(STD + ["es_22_bellypan_bormio_grey_stripes", "es_25_bellypan_bormio_yellow_stripes"])
check("Two bellypans simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["es_23_bellypan_sunrise_red_grey_stripes", "es_26_bellypan_sunrise_red_yellow_stripes"])
check("Grey + yellow stripes both active is REJECTED", not v, err)

v, err = validate(STD + ["es_22_bellypan_bormio_grey_stripes", "es_27_bellypan_riviera_green_yellow_stripes"])
check("Different bellypan colors simultaneously is REJECTED", not v, err)

# Bellypan combined with color overlay (spec doesn't restrict pairing)
v, err = validate(STD + ["es_13_esseesse9_sunrise_red", "es_23_bellypan_sunrise_red_grey_stripes"])
check("Sunrise Red + matching bellypan is valid", v, err)

v, err = validate(STD + ["es_14_esseesse9_riviera_green", "es_24_bellypan_riviera_green_grey_stripes"])
check("Riviera Green + matching bellypan is valid", v, err)

# =========================================================================
# TC-06: CARBON PARTS -- any combination, all optional
# =========================================================================
section("TC-06: ES-31/32/33/34 CARBON PARTS -- any combo, all optional")

carbon = {
    "es_31_front_mudguard_carbon": "ES-31 Front Mudguard Carbon",
    "es_32_rear_mudguard_carbon":  "ES-32 Rear Mudguard Carbon",
    "es_33_battery_cover_carbon":  "ES-33 Battery Cover Carbon",
    "es_34_tank_rib_carbon":       "ES-34 Tank Rib Carbon",
}

for cid, cname in carbon.items():
    v, err = validate(STD + [cid])
    check(f"{cname} alone is valid", v, err)

all_carbon = list(carbon.keys())
v, err = validate(STD + all_carbon)
check("ALL four carbon parts ON simultaneously is valid", v, err)
md5_all_c, _ = render_md5(STD + all_carbon)
check("All carbon parts changes render", md5_all_c != md5_plain)

# Partial combos
v, _ = validate(STD + ["es_31_front_mudguard_carbon", "es_33_battery_cover_carbon"])
check("Front mudguard + battery cover (partial combo) is valid", v)
v, _ = validate(STD + ["es_32_rear_mudguard_carbon", "es_34_tank_rib_carbon"])
check("Rear mudguard + tank rib (partial combo) is valid", v)

# =========================================================================
# TC-07: SUSPENSION -- exactly one always active
# =========================================================================
section("TC-07: SUSPENSION -- exactly one always active")

v, _ = validate(STD)
check("*ES-45 standard suspension (default) is valid", v)

ohlins = swap(STD, "es_45_standard_suspensions", "es_46_kit_ohlins_suspensions")
v, err = validate(ohlins)
check("ES-46 OHLINS suspension is valid", v, err)
md5_ohlins, _ = render_md5(ohlins)
md5_std_s, _  = render_md5(STD)
check("OHLINS differs visually from standard suspension", md5_ohlins != md5_std_s)

v, err = validate(STD + ["es_46_kit_ohlins_suspensions"])
check("Both suspensions simultaneously is REJECTED", not v, err)

no_susp = [l for l in STD if l != "es_45_standard_suspensions"]
v, err = validate(no_susp)
check("No suspension selected is REJECTED", not v, err)

# =========================================================================
# TC-08: WHEELS -- exactly one of three always active
# =========================================================================
section("TC-08: WHEELS -- exactly one of three always active")

v, _ = validate(STD)
check("*ES-57 standard wheels (default) is valid", v)

for wid, wname in [
    ("es_58_forged_aluminium_wheels", "ES-58 Forged Aluminium"),
    ("es_59carbon_fiber_wheels",      "ES-59 Carbon Fiber"),
]:
    wlayers = swap(STD, "es_57_standard_cast_aluminium_wheels", wid)
    v, err = validate(wlayers)
    check(f"{wname} wheels is valid", v, err)
    md5_w, _ = render_md5(wlayers)
    md5_sw, _ = render_md5(STD)
    check(f"{wname} wheels differ visually from standard", md5_w != md5_sw)

v, err = validate(STD + ["es_58_forged_aluminium_wheels"])
check("Two wheel types simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["es_58_forged_aluminium_wheels", "es_59carbon_fiber_wheels"])
check("Three wheel types simultaneously is REJECTED (forged+carbon)", not v, err)

no_wheels = [l for l in STD if l != "es_57_standard_cast_aluminium_wheels"]
v, err = validate(no_wheels)
check("No wheels selected is REJECTED", not v, err)

# =========================================================================
# TC-09: RS VERSION -- optional
# =========================================================================
section("TC-09: ES-60 RS VERSION -- optional")

v, _ = validate(STD + ["es_60_rs_version"])
check("RS version ON is valid", v)
md5_rs, _ = render_md5(STD + ["es_60_rs_version"])
check("RS version changes render", md5_plain != md5_rs)

# Works with all color variants
v, _ = validate(STD + ["es_13_esseesse9_sunrise_red", "es_60_rs_version"])
check("RS version + Sunrise Red is valid", v)
v, _ = validate(STD + ["es_14_esseesse9_riviera_green", "es_60_rs_version"])
check("RS version + Riviera Green is valid", v)

# =========================================================================
# TC-10: ERGAL SCREWS -- at most one of three (or none)
# =========================================================================
section("TC-10: ERGAL SCREWS -- at most one of three, or none")

v, _ = validate(STD)
check("No ergal screws is valid", v)

for eid, ename in [
    ("es_71_kit_ergal_screws_gold",  "ES-71 Gold"),
    ("es_72_kit_ergal_screws_blue",  "ES-72 Blue"),
    ("es_73_kit_ergal_screws_black", "ES-73 Black"),
]:
    v, err = validate(STD + [eid])
    check(f"{ename} ergal screws is valid", v, err)
    md5_e, _ = render_md5(STD + [eid])
    check(f"{ename} ergal changes render", md5_e != md5_plain)

# REJECT: any two simultaneously
v, err = validate(STD + ["es_71_kit_ergal_screws_gold", "es_72_kit_ergal_screws_blue"])
check("Gold + Blue ergal simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["es_71_kit_ergal_screws_gold", "es_73_kit_ergal_screws_black"])
check("Gold + Black ergal simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["es_72_kit_ergal_screws_blue", "es_73_kit_ergal_screws_black"])
check("Blue + Black ergal simultaneously is REJECTED", not v, err)

v, err = validate(STD + ["es_71_kit_ergal_screws_gold",
                          "es_72_kit_ergal_screws_blue",
                          "es_73_kit_ergal_screws_black"])
check("All three ergal types simultaneously is REJECTED", not v, err)

# =========================================================================
# TC-11: WINDSCREEN KIT -- optional, all configurations
# =========================================================================
section("TC-11: ES-84 WINDSCREEN KIT -- optional, all configurations")

v, _ = validate(STD + ["es_84_windscreen_kit"])
check("Windscreen kit ON is valid", v)
md5_ws, _ = render_md5(STD + ["es_84_windscreen_kit"])
check("Windscreen kit changes render", md5_plain != md5_ws)

# Works with all colors
v, _ = validate(STD + ["es_13_esseesse9_sunrise_red", "es_84_windscreen_kit"])
check("Windscreen + Sunrise Red is valid", v)
v, _ = validate(STD + ["es_14_esseesse9_riviera_green", "es_84_windscreen_kit"])
check("Windscreen + Riviera Green is valid", v)
v, _ = validate(STD + ["es_02_cnc_titanium_grey", "es_84_windscreen_kit"])
check("Windscreen + CNC grey (Bormio Ice) is valid", v)

# =========================================================================
# TC-12: SPLASH GUARD -- optional, all configurations
# =========================================================================
section("TC-12: ES-85 SPLASH GUARD -- optional")

v, _ = validate(STD + ["es_85_splash_guard"])
check("Splash guard ON is valid", v)
md5_sg, _ = render_md5(STD + ["es_85_splash_guard"])
check("Splash guard changes render", md5_plain != md5_sg)
v, _ = validate(STD + ["es_13_esseesse9_sunrise_red", "es_85_splash_guard"])
check("Splash guard + Sunrise Red is valid", v)

# =========================================================================
# TC-13: SIDE BAGS KIT -- optional, all configurations
# =========================================================================
section("TC-13: ES-96 SIDE BAGS KIT -- optional")

v, _ = validate(STD + ["es_96_side_bags_kit"])
check("Side bags kit ON is valid", v)
md5_bags, _ = render_md5(STD + ["es_96_side_bags_kit"])
check("Side bags changes render", md5_plain != md5_bags)
v, _ = validate(STD + ["es_14_esseesse9_riviera_green", "es_96_side_bags_kit"])
check("Side bags + Riviera Green is valid", v)

# =========================================================================
# TC-14: BAGS PLATES -- at most one (both off = standard titanium)
# =========================================================================
section("TC-14: ES-97 GUN METAL / ES-98 BLUE BAGS PLATES -- at most one")

v, _ = validate(STD)
check("Both plates OFF (standard titanium) is valid", v)

v, _ = validate(STD + ["es_96_side_bags_kit", "es_97_bags_plates_gun_metal"])
check("ES-97 Gun Metal plates (with bags kit) is valid", v)
md5_gm, _ = render_md5(STD + ["es_96_side_bags_kit", "es_97_bags_plates_gun_metal"])

v, _ = validate(STD + ["es_96_side_bags_kit", "er_98_bags_plates_blue"])
check("ES-98 Blue plates (with bags kit) is valid", v)
md5_blue_p, _ = render_md5(STD + ["es_96_side_bags_kit", "er_98_bags_plates_blue"])

v, err = validate(STD + ["es_96_side_bags_kit",
                          "es_97_bags_plates_gun_metal", "er_98_bags_plates_blue"])
check("Both Gun Metal + Blue plates simultaneously is REJECTED", not v, err)

md5_no_plate, _ = render_md5(STD + ["es_96_side_bags_kit"])
check("Gun Metal plates change render", md5_gm    != md5_no_plate)
check("Blue plates change render",      md5_blue_p != md5_no_plate)
check("Gun Metal vs Blue plates differ", md5_gm   != md5_blue_p)

# Plate options without bags kit (still valid per spec — plates can technically be on)
v, _ = validate(STD + ["es_97_bags_plates_gun_metal"])
check("Bags plate without bags kit is accepted by validator", v)

# =========================================================================
# TC-15: COMBINED CONFIGURATIONS -- realistic scenarios
# =========================================================================
section("TC-15: COMBINED CONFIGURATIONS -- realistic scenarios")

# Scenario A: Riviera Green + OHLINS + Carbon fiber + bellypan green + all carbon + RS + Blue ergal + windscreen + bags + blue plates
scenario_a = [
    "es_01_base_esseesse9_bormio_ice",
    "es_14_esseesse9_riviera_green",
    "es_24_bellypan_riviera_green_grey_stripes",
    "es_31_front_mudguard_carbon", "es_32_rear_mudguard_carbon",
    "es_33_battery_cover_carbon",  "es_34_tank_rib_carbon",
    "es_46_kit_ohlins_suspensions",
    "es_59carbon_fiber_wheels",
    "es_60_rs_version",
    "es_72_kit_ergal_screws_blue",
    "es_84_windscreen_kit",
    "es_85_splash_guard",
    "es_96_side_bags_kit",
    "er_98_bags_plates_blue",
    "background",
]
v, err = validate(scenario_a)
check("Scenario A: Riviera+OHLINS+CarbonWheels+AllCarbon+RS+BlueErgal+Wind+Bags+BluePlates -- valid", v, err)
md5_a, sz_a = render_md5(scenario_a)
check("Scenario A renders successfully", md5_a is not None, f"{sz_a:,}b")

# Scenario B: Sunrise Red + forged + bormio grey bellypan + gold ergal + splash
scenario_b = [
    "es_01_base_esseesse9_bormio_ice",
    "es_13_esseesse9_sunrise_red",
    "es_25_bellypan_bormio_yellow_stripes",
    "es_45_standard_suspensions",
    "es_58_forged_aluminium_wheels",
    "es_71_kit_ergal_screws_gold",
    "es_85_splash_guard",
]
v, err = validate(scenario_b)
check("Scenario B: SunriseRed+Forged+YellowBellypan+GoldErgal+Splash -- valid", v, err)
md5_b, sz_b = render_md5(scenario_b)
check("Scenario B renders successfully", md5_b is not None, f"{sz_b:,}b")

# Scenario C: Pure Bormio Ice + CNC grey + standard everything + black ergal + side bags
scenario_c = [
    "es_01_base_esseesse9_bormio_ice",
    "es_02_cnc_titanium_grey",
    "es_45_standard_suspensions",
    "es_57_standard_cast_aluminium_wheels",
    "es_73_kit_ergal_screws_black",
    "es_96_side_bags_kit",
    "es_97_bags_plates_gun_metal",
]
v, err = validate(scenario_c)
check("Scenario C: BormioIce+CNCgrey+StdAll+BlackErgal+Bags+GunMetalPlates -- valid", v, err)
md5_c, sz_c = render_md5(scenario_c)
check("Scenario C renders successfully", md5_c is not None, f"{sz_c:,}b")

# Scenario D: Minimal standard
v, err = validate(STD)
check("Scenario D: Minimal standard is valid", v, err)
md5_d, _ = render_md5(STD)

check("All 4 scenarios produce different renders", len({md5_a, md5_b, md5_c, md5_d}) == 4)

# FAIL combinations
v, err = validate(STD + ["es_13_esseesse9_sunrise_red", "es_14_esseesse9_riviera_green"])
check("Both color overlays active is REJECTED", not v, err)

v, err = validate(STD + ["es_02_cnc_titanium_grey", "es_13_esseesse9_sunrise_red"])
check("CNC grey + color overlay is REJECTED", not v, err)

v, err = validate(STD + ["es_22_bellypan_bormio_grey_stripes", "es_27_bellypan_riviera_green_yellow_stripes"])
check("Two bellypans active is REJECTED", not v, err)

v, err = validate(STD + ["es_45_standard_suspensions", "es_46_kit_ohlins_suspensions"])
check("Both suspensions active is REJECTED", not v, err)

v, err = validate(STD + ["es_57_standard_cast_aluminium_wheels", "es_59carbon_fiber_wheels"])
check("Two wheel types active is REJECTED", not v, err)

v, err = validate(STD + ["es_72_kit_ergal_screws_blue", "es_73_kit_ergal_screws_black"])
check("Two ergal types active is REJECTED", not v, err)

v, err = validate(STD + ["es_97_bags_plates_gun_metal", "er_98_bags_plates_blue"])
check("Both bag plate colors active is REJECTED", not v, err)

no_susp = [l for l in STD if l != "es_45_standard_suspensions"]
v, err = validate(no_susp)
check("No suspension selected is REJECTED", not v, err)

no_wheels = [l for l in STD if l != "es_57_standard_cast_aluminium_wheels"]
v, err = validate(no_wheels)
check("No wheels selected is REJECTED", not v, err)

# =========================================================================
# SUMMARY
# =========================================================================
total = PASS + FAIL
print(f"\n{'='*62}")
print(f"  EsseEsse9 SPEC TEST RESULTS")
print(f"{'='*62}")
print(f"  TOTAL  : {total}")
print(f"  PASSED : {PASS}")
print(f"  FAILED : {FAIL}")
if ERRORS:
    print(f"\n  Failed tests:")
    for e in ERRORS: print(f"    - {e}")
print(f"{'='*62}")
sys.exit(0 if FAIL == 0 else 1)
