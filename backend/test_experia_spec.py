"""
Senior Tester — EXPERIA Full Spec Verification
Tests every rule from Paolo's specification document.
Run: python test_experia_spec.py
"""
import json
import hashlib
import urllib.request
import urllib.error
import sys

BASE_URL = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0
ERRORS = []

# Standard default layer set (all required groups satisfied)
STD = [
    "ex_01_base_experia_metal_black",       # base — always on
    "ex_35_standard_cast_aluminium_wheels", # *standard wheels
    "ex_48_standard_injection_front_fender",# *standard fender
    "ex_50_standard_windscreen",            # *standard windscreen
]

# --------------------------------------------------------------------------
def http_post(endpoint, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/{endpoint}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def validate(layers):
    _, body = http_post("validate", {"model": "experia", "layers": layers})
    return body["valid"], body.get("error")

def render_md5(layers):
    """POST /configure and return (md5_hex, byte_size) or (None, 0) on failure."""
    payload = json.dumps({"model": "experia", "layers": layers,
                          "format": "jpeg", "quality": 85}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/configure", data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        return hashlib.md5(raw).hexdigest()[:10], len(raw)
    except urllib.error.HTTPError as e:
        return None, 0

def check(label, condition, details=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  \033[32mPASS\033[0m  {label}")
    else:
        FAIL += 1
        ERRORS.append(label)
        print(f"  \033[31mFAIL\033[0m  {label}")
        if details:
            print(f"         {details}")

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ==========================================================================
# TC-01: BACKGROUND LAYER
# ==========================================================================
section("TC-01: BACKGROUND — optional on/off")

v, _ = validate(STD)
check("Default config valid without background", v)

v, _ = validate(STD + ["background"])
check("Config valid with background ON", v)

# Render both and check they are different images
md5_no_bg,  sz_no_bg  = render_md5(STD)
md5_with_bg, sz_with_bg = render_md5(STD + ["background"])
check("Render without background succeeds", md5_no_bg is not None, f"size={sz_no_bg}")
check("Render with background succeeds",    md5_with_bg is not None, f"size={sz_with_bg}")
check("Background ON/OFF produces different images",
      md5_no_bg != md5_with_bg,
      f"both md5={md5_no_bg} (may be same if BG is transparent)")

# ==========================================================================
# TC-02: #EX-01 BASE — always on
# ==========================================================================
section("TC-02: #EX-01 BASE-EXPERIA METAL BLACK — must always be on")

v, err = validate(STD)
check("Valid config includes base", v)

# Without base
layers_no_base = [l for l in STD if l != "ex_01_base_experia_metal_black"]
v, err = validate(layers_no_base)
check("Missing base is REJECTED", not v, f"error: {err}")

# Base alone (no wheels/fender/windscreen) — should fail required groups
v, err = validate(["ex_01_base_experia_metal_black"])
check("Base alone (no required groups) is REJECTED", not v, f"error: {err}")

md5_base, sz = render_md5(STD)
check("Base render succeeds", md5_base is not None, f"size={sz:,}b")

# ==========================================================================
# TC-03: COLOR OVERLAYS — EX-12 and EX-13
# ==========================================================================
section("TC-03: EX-12 BORMIO ICE / EX-13 WHITE FLAME — at most one, not required")

# Both off — valid (metal black shown by base)
v, _ = validate(STD)
check("Both color overlays OFF is valid (pure metal black)", v)

# Bormio ice only
v, _ = validate(STD + ["ex_12_experia_bormio_ice"])
check("EX-12 BORMIO ICE alone is valid", v)
md5_bormio, _ = render_md5(STD + ["ex_12_experia_bormio_ice"])

# White flame only
v, _ = validate(STD + ["ex_13_experia_white_flame"])
check("EX-13 WHITE FLAME alone is valid", v)
md5_flame, _ = render_md5(STD + ["ex_13_experia_white_flame"])

# Both on — MUST FAIL
v, err = validate(STD + ["ex_12_experia_bormio_ice", "ex_13_experia_white_flame"])
check("Both EX-12 + EX-13 ON is REJECTED", not v, f"error: {err}")

# Visually different renders
md5_no_color, _ = render_md5(STD)
check("Bormio ice differs visually from metal black",   md5_bormio != md5_no_color)
check("White flame differs visually from metal black",  md5_flame  != md5_no_color)
check("Bormio ice differs visually from white flame",   md5_bormio != md5_flame)

# ==========================================================================
# TC-04: EX-24 SPORTRED SEAT KIT — optional
# ==========================================================================
section("TC-04: EX-24 SPORTRED SEAT KIT — optional, independent")

v, _ = validate(STD)
check("Without sportred seat — valid", v)

v, _ = validate(STD + ["ex_24_sportred_seat_kit"])
check("With sportred seat — valid", v)

md5_no_seat, _ = render_md5(STD)
md5_seat, _    = render_md5(STD + ["ex_24_sportred_seat_kit"])
check("Sportred seat changes render", md5_no_seat != md5_seat)

# ==========================================================================
# TC-05: WHEELS — exactly one always active
# ==========================================================================
section("TC-05: WHEELS — exactly one of three must always be active")

# Standard is default
v, _ = validate(STD)
check("*EX-35 standard wheels (default) valid", v)

# Optional: red stripe
STD_RED = [l for l in STD if l != "ex_35_standard_cast_aluminium_wheels"] + ["ex_36_red_stripe_cast_wheels"]
v, _ = validate(STD_RED)
check("EX-36 red stripe wheels valid", v)
md5_red, _ = render_md5(STD_RED)

# Optional: forged
STD_FORGED = [l for l in STD if l != "ex_35_standard_cast_aluminium_wheels"] + ["ex_37_forged_aluminium_wheels"]
v, _ = validate(STD_FORGED)
check("EX-37 forged aluminium wheels valid", v)
md5_forged, _ = render_md5(STD_FORGED)

# FAIL: two wheels at once
v, err = validate(STD + ["ex_36_red_stripe_cast_wheels"])
check("Two wheel types simultaneously REJECTED", not v, f"error: {err}")

v, err = validate(STD + ["ex_37_forged_aluminium_wheels"])
check("Another two-wheel combo REJECTED", not v, f"error: {err}")

v, err = validate([l for l in STD if l != "ex_35_standard_cast_aluminium_wheels"])
check("No wheels selected REJECTED", not v, f"error: {err}")

# Visually distinct
md5_std_w, _ = render_md5(STD)
check("Red stripe wheels differ from standard",  md5_red    != md5_std_w)
check("Forged wheels differ from standard",      md5_forged != md5_std_w)
check("Forged wheels differ from red stripe",    md5_forged != md5_red)

# ==========================================================================
# TC-06: FRONT FENDER — exactly one always active
# ==========================================================================
section("TC-06: FRONT FENDER — exactly one of two must always be active")

v, _ = validate(STD)
check("*EX-48 standard fender (default) valid", v)

STD_CARBON_FENDER = [l for l in STD if l != "ex_48_standard_injection_front_fender"] + ["ex_49_front_mudguard_carbon"]
v, _ = validate(STD_CARBON_FENDER)
check("EX-49 carbon front mudguard valid", v)
md5_carbon_fender, _ = render_md5(STD_CARBON_FENDER)

# FAIL: both
v, err = validate(STD + ["ex_49_front_mudguard_carbon"])
check("Both fenders simultaneously REJECTED", not v, f"error: {err}")

# FAIL: none
STD_NO_FENDER = [l for l in STD if l != "ex_48_standard_injection_front_fender"]
v, err = validate(STD_NO_FENDER)
check("No fender selected REJECTED", not v, f"error: {err}")

md5_std_fender, _ = render_md5(STD)
check("Carbon fender differs visually from standard", md5_carbon_fender != md5_std_fender)

# ==========================================================================
# TC-07: WINDSCREEN — exactly one always active
# ==========================================================================
section("TC-07: WINDSCREEN — exactly one of two must always be active")

v, _ = validate(STD)
check("*EX-50 standard windscreen (default) valid", v)

STD_LOW = [l for l in STD if l != "ex_50_standard_windscreen"] + ["ex_51_low_windscreen_smoky"]
v, _ = validate(STD_LOW)
check("EX-51 low smoky windscreen valid", v)
md5_low_wind, _ = render_md5(STD_LOW)

# FAIL: both
v, err = validate(STD + ["ex_51_low_windscreen_smoky"])
check("Both windscreens simultaneously REJECTED", not v, f"error: {err}")

# FAIL: none
STD_NO_WIND = [l for l in STD if l != "ex_50_standard_windscreen"]
v, err = validate(STD_NO_WIND)
check("No windscreen selected REJECTED", not v, f"error: {err}")

md5_std_wind, _ = render_md5(STD)
check("Low smoky windscreen differs visually from standard", md5_low_wind != md5_std_wind)

# ==========================================================================
# TC-08: ERGAL SCREWS — at most one, both optional
# ==========================================================================
section("TC-08: ERGAL SCREWS — at most one (or none)")

v, _ = validate(STD)
check("No ergal screws — valid", v)

v, _ = validate(STD + ["ex_62_kit_ergal_screws_gold"])
check("EX-62 gold ergal screws — valid", v)
md5_gold, _ = render_md5(STD + ["ex_62_kit_ergal_screws_gold"])

v, _ = validate(STD + ["ex_63_kit_ergal_screws_black"])
check("EX-63 black ergal screws — valid", v)
md5_black_screws, _ = render_md5(STD + ["ex_63_kit_ergal_screws_black"])

# FAIL: both
v, err = validate(STD + ["ex_62_kit_ergal_screws_gold", "ex_63_kit_ergal_screws_black"])
check("Both ergal screw types REJECTED", not v, f"error: {err}")

md5_base_r, _ = render_md5(STD)
check("Gold screws change render",  md5_gold         != md5_base_r)
check("Black screws change render", md5_black_screws != md5_base_r)
check("Gold vs black screws differ", md5_gold        != md5_black_screws)

# ==========================================================================
# TC-09: CENTRAL STAND — optional, independent
# ==========================================================================
section("TC-09: EX-74 CENTRAL STAND — optional")

v, _ = validate(STD)
check("Without central stand — valid", v)
v, _ = validate(STD + ["ex_74_central_stand"])
check("With central stand — valid", v)
md5_no_cs, _ = render_md5(STD)
md5_cs, _    = render_md5(STD + ["ex_74_central_stand"])
check("Central stand changes render", md5_no_cs != md5_cs)

# ==========================================================================
# TC-10: HANDGUARDS — optional, independent
# ==========================================================================
section("TC-10: EX-85 HANDGUARDS — optional")

v, _ = validate(STD + ["ex_85_handguards"])
check("Handguards — valid", v)
md5_hg, _ = render_md5(STD + ["ex_85_handguards"])
check("Handguards change render", md5_no_cs != md5_hg)

# ==========================================================================
# TC-11: SPLASH GUARD — optional, independent
# ==========================================================================
section("TC-11: EX-96 SPLASH GUARD — optional")

v, _ = validate(STD + ["ex_96_splash_guard"])
check("Splash guard — valid", v)
md5_sg, _ = render_md5(STD + ["ex_96_splash_guard"])
check("Splash guard changes render", md5_no_cs != md5_sg)

# ==========================================================================
# TC-12: TOP CASE + SIDE BAGS — BOTH can be active simultaneously
# ==========================================================================
section("TC-12: EX-107 TOP CASE / EX-108 SIDE BAGS — can both be ON")

v, _ = validate(STD + ["ex_107_top_case_kit"])
check("Top case kit alone — valid", v)

v, _ = validate(STD + ["ex_108_side_bags_kit"])
check("Side bags kit alone — valid", v)

v, _ = validate(STD + ["ex_107_top_case_kit", "ex_108_side_bags_kit"])
check("Top case + side bags BOTH ON — valid (Paolo spec)", v)

md5_tc,   _ = render_md5(STD + ["ex_107_top_case_kit"])
md5_sb,   _ = render_md5(STD + ["ex_108_side_bags_kit"])
md5_both, _ = render_md5(STD + ["ex_107_top_case_kit", "ex_108_side_bags_kit"])
check("Top case changes render",            md5_no_cs != md5_tc)
check("Side bags change render",            md5_no_cs != md5_sb)
check("Both together differs from each alone (tc)", md5_both != md5_tc)
check("Both together differs from each alone (sb)", md5_both != md5_sb)

# ==========================================================================
# TC-13: COMBINED — realistic user sessions
# ==========================================================================
section("TC-13: COMBINED CONFIGURATIONS — realistic scenarios")

# Scenario A: Bormio Ice + forged wheels + carbon fender + low windscreen + gold ergal + both bags
scenario_a = [
    "ex_01_base_experia_metal_black",
    "ex_12_experia_bormio_ice",
    "ex_37_forged_aluminium_wheels",
    "ex_49_front_mudguard_carbon",
    "ex_51_low_windscreen_smoky",
    "ex_62_kit_ergal_screws_gold",
    "ex_107_top_case_kit",
    "ex_108_side_bags_kit",
    "background",
]
v, err = validate(scenario_a)
check("Scenario A: Bormio+Forged+Carbon+LowWind+GoldErgal+BothBags — valid", v, err)
md5_a, sz_a = render_md5(scenario_a)
check("Scenario A renders successfully", md5_a is not None, f"size={sz_a:,}b")

# Scenario B: White flame + red stripe wheels + sportred seat + central stand + handguards + splash
scenario_b = [
    "ex_01_base_experia_metal_black",
    "ex_13_experia_white_flame",
    "ex_36_red_stripe_cast_wheels",
    "ex_48_standard_injection_front_fender",
    "ex_50_standard_windscreen",
    "ex_24_sportred_seat_kit",
    "ex_74_central_stand",
    "ex_85_handguards",
    "ex_96_splash_guard",
    "ex_63_kit_ergal_screws_black",
]
v, err = validate(scenario_b)
check("Scenario B: WhiteFlame+RedStripe+SportSeat+Stand+Guards+Splash+BlackErgal — valid", v, err)
md5_b, sz_b = render_md5(scenario_b)
check("Scenario B renders successfully", md5_b is not None, f"size={sz_b:,}b")

# Scenario C: Pure metal black, fully standard, no extras
scenario_c = list(STD)  # base + std wheels + std fender + std windscreen
v, err = validate(scenario_c)
check("Scenario C: Pure standard metal black — valid", v, err)
md5_c, sz_c = render_md5(scenario_c)
check("Scenario C renders successfully", md5_c is not None, f"size={sz_c:,}b")

check("All 3 scenarios produce different renders",
      len({md5_a, md5_b, md5_c}) == 3)

# FAIL scenarios
v, err = validate(["ex_01_base_experia_metal_black",
                   "ex_12_experia_bormio_ice", "ex_13_experia_white_flame",  # both colors
                   "ex_35_standard_cast_aluminium_wheels",
                   "ex_48_standard_injection_front_fender",
                   "ex_50_standard_windscreen"])
check("Two colors active simultaneously REJECTED in full config", not v, err)

v, err = validate(["ex_01_base_experia_metal_black",
                   "ex_35_standard_cast_aluminium_wheels", "ex_36_red_stripe_cast_wheels",  # two wheels
                   "ex_48_standard_injection_front_fender",
                   "ex_50_standard_windscreen"])
check("Two wheel types in full config REJECTED", not v, err)

v, err = validate(["ex_01_base_experia_metal_black",
                   "ex_35_standard_cast_aluminium_wheels",
                   "ex_48_standard_injection_front_fender", "ex_49_front_mudguard_carbon",  # two fenders
                   "ex_50_standard_windscreen"])
check("Two fender types in full config REJECTED", not v, err)

v, err = validate(["ex_01_base_experia_metal_black",
                   "ex_35_standard_cast_aluminium_wheels",
                   "ex_48_standard_injection_front_fender",
                   "ex_50_standard_windscreen", "ex_51_low_windscreen_smoky"])  # two windscreens
check("Two windscreen types in full config REJECTED", not v, err)

v, err = validate(["ex_01_base_experia_metal_black",
                   "ex_35_standard_cast_aluminium_wheels",
                   "ex_48_standard_injection_front_fender",
                   "ex_50_standard_windscreen",
                   "ex_62_kit_ergal_screws_gold", "ex_63_kit_ergal_screws_black"])  # two ergal
check("Two ergal screw types in full config REJECTED", not v, err)

# ==========================================================================
# SUMMARY
# ==========================================================================
total = PASS + FAIL
print(f"\n{'='*60}")
print(f"  EXPERIA SPEC TEST RESULTS")
print(f"{'='*60}")
print(f"  TOTAL  : {total}")
print(f"  PASSED : {PASS}")
print(f"  FAILED : {FAIL}")
if ERRORS:
    print(f"\n  Failed tests:")
    for e in ERRORS:
        print(f"    - {e}")
print(f"{'='*60}")
sys.exit(0 if FAIL == 0 else 1)
