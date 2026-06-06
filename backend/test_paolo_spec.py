"""
Full validation test of all 4 models against Paolo's exact spec.
Run: python test_paolo_spec.py
"""
import json, urllib.request, sys

BASE = "http://127.0.0.1:8000"
PASS = 0; FAIL = 0

def validate(model, layers, expect_valid, label):
    global PASS, FAIL
    payload = json.dumps({"model": model, "layers": layers}).encode()
    req = urllib.request.Request(f"{BASE}/validate", data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        result = json.loads(r.read())
    ok = result["valid"] == expect_valid
    status = "PASS" if ok else "FAIL"
    if not ok:
        FAIL += 1
        print(f"  {status}  {label}")
        print(f"        expected valid={expect_valid}, got valid={result['valid']}, error={result.get('error')}")
    else:
        PASS += 1
        print(f"  {status}  {label}")


# ============================================================
# EVA RIBELLE
# ============================================================
print("\n=== EVA RIBELLE ===")
BASE_ER = ["er_01_base_ribelle_stealth_grey", "er_52_standard_suspensions",
           "eg_64_standard_cast_aluminium_wheels"]

validate("eva_ribelle", BASE_ER,                            True,  "default (stealth grey, std susp, std wheels)")
validate("eva_ribelle", BASE_ER + ["er_13_eva_tricolore"],  True,  "tricolore overlay")
validate("eva_ribelle", BASE_ER + ["er_12_eva_rosso_corsa"],True,  "rosso corsa overlay")
validate("eva_ribelle", BASE_ER + ["background"],           True,  "background on")
validate("eva_ribelle", BASE_ER + ["er_24_frame_black"],    True,  "frame black optional on")
validate("eva_ribelle", BASE_ER + ["er_35_front_mudguard_carbon",  # carbon parts all on
          "er_36_rear_mudguard_carbon", "er_37_battery_cover_carbon", "er_38_tank_rib_carbon"], True, "all carbon parts on")
validate("eva_ribelle", BASE_ER + ["er_40_rs_version", "er_41_stickers_kit_rs_sport"], True,  "RS version + stickers")
validate("eva_ribelle", BASE_ER + ["er_41_stickers_kit_rs_sport"], False, "stickers without RS version (should fail)")
validate("eva_ribelle", BASE_ER + ["er_53_kit_ohlins_suspensions"],  False, "both suspensions active (should fail)")
validate("eva_ribelle", BASE_ER + ["er_13_eva_tricolore", "er_12_eva_rosso_corsa"], False, "both colors active (should fail)")
validate("eva_ribelle", BASE_ER + ["er_78_kit_ergal_screws_gold", "er_79_kit_ergal_screws_black"], False, "both ergal screws (should fail)")
validate("eva_ribelle", BASE_ER + ["er_92_bags_plates_red", "er_93_bags_plates_gun_metal"], False, "both bag plates (should fail)")
validate("eva_ribelle", BASE_ER + ["er_78_kit_ergal_screws_gold"], True,  "gold ergal screws only")
validate("eva_ribelle", BASE_ER + ["er_91_side_bags_kit", "er_92_bags_plates_red"], True,  "bags kit + red plates")
# Missing required layer
validate("eva_ribelle", ["er_52_standard_suspensions", "eg_64_standard_cast_aluminium_wheels"], False, "missing base (should fail)")
validate("eva_ribelle", ["er_01_base_ribelle_stealth_grey", "eg_64_standard_cast_aluminium_wheels"], False, "missing suspension (validator allows - no required group check)")

# ============================================================
# ESSESSE9
# ============================================================
print("\n=== ESSESSE9 ===")
BASE_ES = ["es_01_base_esseesse9_bormio_ice", "es_45_standard_suspensions",
           "es_57_standard_cast_aluminium_wheels"]

validate("essesse9", BASE_ES,                                True,  "default bormio ice")
validate("essesse9", BASE_ES + ["es_14_esseesse9_riviera_green"], True, "riviera green overlay")
validate("essesse9", BASE_ES + ["es_13_esseesse9_sunrise_red"],   True, "sunrise red overlay")
validate("essesse9", BASE_ES + ["es_13_esseesse9_sunrise_red", "es_14_esseesse9_riviera_green"], False, "both colors (should fail)")
validate("essesse9", BASE_ES + ["es_02_cnc_titanium_grey"],  True,  "CNC titanium grey (bormio only)")
validate("essesse9", BASE_ES + ["es_22_bellypan_bormio_grey_stripes"], True, "bellypan grey stripes")
validate("essesse9", BASE_ES + ["es_22_bellypan_bormio_grey_stripes",
          "es_25_bellypan_bormio_yellow_stripes"],           False, "two bellypans (should fail)")
validate("essesse9", BASE_ES + ["es_71_kit_ergal_screws_gold"], True, "gold ergal")
validate("essesse9", BASE_ES + ["es_71_kit_ergal_screws_gold", "es_72_kit_ergal_screws_blue"], False, "two ergal screws (should fail)")
validate("essesse9", BASE_ES + ["es_97_bags_plates_gun_metal"], True, "gun metal plates")
validate("essesse9", BASE_ES + ["es_97_bags_plates_gun_metal", "er_98_bags_plates_blue"], False, "two bag plates (should fail)")
validate("essesse9", BASE_ES + ["es_31_front_mudguard_carbon", "es_32_rear_mudguard_carbon",
          "es_33_battery_cover_carbon", "es_34_tank_rib_carbon"], True, "all carbon parts")
validate("essesse9", BASE_ES + ["es_84_windscreen_kit", "es_85_splash_guard"], True, "windscreen + splash guard")
validate("essesse9", BASE_ES + ["background"], True, "background on")

# ============================================================
# EGO
# ============================================================
print("\n=== EGO ===")
BASE_EG = ["eg_01_base_ego_metal_black", "eg_62_passenger_seat_standard",
           "eg_78_standard_suspensions", "eg_80_standard_cast_aluminium_wheels"]

validate("ego", BASE_EG,                                    True,  "default metal black, std seat, std susp, std wheels")
validate("ego", BASE_EG + ["eg_13_tricolore"],              True,  "tricolore overlay")
validate("ego", BASE_EG + ["eg_12_ego_rosso_corsa"],        True,  "rosso corsa overlay")
validate("ego", BASE_EG + ["eg_13_tricolore", "eg_12_ego_rosso_corsa"], False, "both colors (should fail)")
validate("ego", BASE_EG + ["eg_24_frame_black"],            True,  "frame black optional on")
validate("ego", BASE_EG + ["background"],                   True,  "background on")
validate("ego", BASE_EG + ["eg_35_front_mudguard_carbon", "eg_36_rear_mudguard_carbon",
          "eg_37_bellypan_carbon", "eg_38_undertail_cover_carbon"], True, "all carbon parts")
validate("ego", BASE_EG + ["eg_49_rs_version"],             True,  "RS version")
# Passenger seat switching
EG_TECH_RED = [l for l in BASE_EG if l != "eg_62_passenger_seat_standard"] + ["eg_63_passenger_seat_ego_tech_red"]
validate("ego", EG_TECH_RED + ["eg_50_rider_seat_ego_tech_red"], True, "rider tech red + passenger tech red")
validate("ego", EG_TECH_RED,                                True,  "passenger tech red without rider seat (valid)")
validate("ego", BASE_EG + ["eg_63_passenger_seat_ego_tech_red"], False, "two passenger seats (should fail)")
validate("ego", BASE_EG + ["eg_79_kit_ohlins_suspensions"],  False, "both suspensions (should fail)")
validate("ego", BASE_EG + ["eg_83_carbon_fiber_wheels"],     False, "two wheel types (should fail)")
validate("ego", BASE_EG + ["eg_94_kit_ergal_screws_gold", "eg_95_kit_ergal_screws_black"], False, "both ergal (should fail)")
validate("ego", BASE_EG + ["eg_94_kit_ergal_screws_gold"],   True,  "gold ergal only")
# Cover corsaclienti
EG_COVER = [l for l in BASE_EG if l != "eg_62_passenger_seat_standard"] + ["eg_65_cover_corsaclienti_grey"]
validate("ego", EG_COVER,                                   True,  "corsaclienti cover grey")
validate("ego", ["eg_01_base_ego_metal_black", "eg_78_standard_suspensions",
          "eg_80_standard_cast_aluminium_wheels"],           False, "missing passenger seat (should fail)")

# ============================================================
# EXPERIA
# ============================================================
print("\n=== EXPERIA ===")
BASE_EX = ["ex_01_base_experia_metal_black", "ex_35_standard_cast_aluminium_wheels",
           "ex_48_standard_injection_front_fender", "ex_50_standard_windscreen"]

validate("experia", BASE_EX,                                True,  "default metal black")
validate("experia", BASE_EX + ["ex_13_experia_white_flame"], True, "white flame overlay")
validate("experia", BASE_EX + ["ex_12_experia_bormio_ice"],  True, "bormio ice overlay")
validate("experia", BASE_EX + ["ex_13_experia_white_flame", "ex_12_experia_bormio_ice"], False, "both colors (should fail)")
validate("experia", BASE_EX + ["background"],               True,  "background on")
validate("experia", BASE_EX + ["ex_24_sportred_seat_kit"],  True,  "sportred seat")
# Wheels
EX_FORGED = [l for l in BASE_EX if l != "ex_35_standard_cast_aluminium_wheels"] + ["ex_37_forged_aluminium_wheels"]
validate("experia", EX_FORGED,                              True,  "forged wheels")
validate("experia", BASE_EX + ["ex_37_forged_aluminium_wheels"], False, "two wheel types (should fail)")
# Front fender
EX_CARBON_FENDER = [l for l in BASE_EX if l != "ex_48_standard_injection_front_fender"] + ["ex_49_front_mudguard_carbon"]
validate("experia", EX_CARBON_FENDER,                       True,  "carbon front fender")
validate("experia", BASE_EX + ["ex_49_front_mudguard_carbon"], False, "two fenders (should fail)")
# Windscreen
EX_LOW_WIND = [l for l in BASE_EX if l != "ex_50_standard_windscreen"] + ["ex_51_low_windscreen_smoky"]
validate("experia", EX_LOW_WIND,                            True,  "low smoky windscreen")
validate("experia", BASE_EX + ["ex_51_low_windscreen_smoky"], False, "two windscreens (should fail)")
# Ergal
validate("experia", BASE_EX + ["ex_62_kit_ergal_screws_gold"], True,  "gold ergal")
validate("experia", BASE_EX + ["ex_62_kit_ergal_screws_gold", "ex_63_kit_ergal_screws_black"], False, "both ergal (should fail)")
# Top case + side bags CAN BOTH be on
validate("experia", BASE_EX + ["ex_107_top_case_kit", "ex_108_side_bags_kit"], True, "top case + side bags both on (allowed)")
# Optional accessories independently
validate("experia", BASE_EX + ["ex_74_central_stand", "ex_85_handguards", "ex_96_splash_guard"], True, "stand + handguards + splash")
# Missing required groups
validate("experia", ["ex_01_base_experia_metal_black", "ex_48_standard_injection_front_fender",
          "ex_50_standard_windscreen"],                      False, "missing wheels (validator - no group required check)")

print(f"\n{'='*50}")
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
sys.exit(0 if FAIL == 0 else 1)
