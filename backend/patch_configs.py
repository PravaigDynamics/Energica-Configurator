"""
Comprehensive config patch based on Paolo's full spec for all 4 models.
Run: python patch_configs.py
"""
import json
from pathlib import Path


def load(model):
    return json.loads(Path(f"layers/{model}/config.json").read_text())


def save(model, cfg):
    Path(f"layers/{model}/config.json").write_text(json.dumps(cfg, indent=2))


# ============================================================
# EVA RIBELLE
# ============================================================
cfg = load("eva_ribelle")

# background and frame are OPTIONAL (Paolo: "you can turn it on or off")
cfg["rules"]["always_visible"] = ["er_01_base_ribelle_stealth_grey"]
for l in cfg["layers"]:
    if l["id"] in ["er_24_frame_black", "background"]:
        l["always_visible"] = False

cfg["rules"]["mutually_exclusive"] = [
    ["er_13_eva_tricolore", "er_12_eva_rosso_corsa"],           # color overlays (at most one)
    ["er_52_standard_suspensions", "er_53_kit_ohlins_suspensions"],  # always one
    ["eg_64_standard_cast_aluminium_wheels", "es_65_red_stripe_cast_wheels",
     "eg_66_forged_aluminium_wheels", "eg_67_carbon_fiber_wheels"],   # always one
    ["er_78_kit_ergal_screws_gold", "er_79_kit_ergal_screws_black"],  # at most one
    ["er_92_bags_plates_red", "er_93_bags_plates_gun_metal"],         # at most one
]

cfg["rules"]["dependencies"] = {
    "er_13_eva_tricolore":         ["er_01_base_ribelle_stealth_grey"],
    "er_12_eva_rosso_corsa":       ["er_01_base_ribelle_stealth_grey"],
    "er_41_stickers_kit_rs_sport": ["er_40_rs_version"],
}

cfg["groups"] = {
    "base_color":        ["er_13_eva_tricolore", "er_12_eva_rosso_corsa"],
    "suspension":        ["er_52_standard_suspensions", "er_53_kit_ohlins_suspensions"],
    "wheels":            ["eg_64_standard_cast_aluminium_wheels", "es_65_red_stripe_cast_wheels",
                          "eg_66_forged_aluminium_wheels", "eg_67_carbon_fiber_wheels"],
    "carbon_parts":      ["er_35_front_mudguard_carbon", "er_36_rear_mudguard_carbon",
                          "er_37_battery_cover_carbon", "er_38_tank_rib_carbon"],
    "ergal_screws":      ["er_78_kit_ergal_screws_gold", "er_79_kit_ergal_screws_black"],
    "rs_options":        ["er_40_rs_version", "er_41_stickers_kit_rs_sport"],
    "optional_upgrades": ["er_24_frame_black", "er_80_windscreen_kit", "er_81_splash_guard",
                          "er_91_side_bags_kit", "er_92_bags_plates_red",
                          "er_93_bags_plates_gun_metal", "background"],
}

save("eva_ribelle", cfg)
print("EVA RIBELLE patched")

# ============================================================
# ESSESSE9
# ============================================================
cfg = load("essesse9")

cfg["rules"]["always_visible"] = ["es_01_base_esseesse9_bormio_ice"]
for l in cfg["layers"]:
    if l["id"] == "background":
        l["always_visible"] = False

cfg["rules"]["mutually_exclusive"] = [
    ["es_13_esseesse9_sunrise_red", "es_14_esseesse9_riviera_green"],  # color overlays
    ["es_22_bellypan_bormio_grey_stripes", "es_23_bellypan_sunrise_red_grey_stripes",
     "es_24_bellypan_riviera_green_grey_stripes", "es_25_bellypan_bormio_yellow_stripes",
     "es_26_bellypan_sunrise_red_yellow_stripes", "es_27_bellypan_riviera_green_yellow_stripes"],
    ["es_45_standard_suspensions", "es_46_kit_ohlins_suspensions"],   # always one
    ["es_57_standard_cast_aluminium_wheels", "es_58_forged_aluminium_wheels",
     "es_59carbon_fiber_wheels"],                                      # always one
    ["es_71_kit_ergal_screws_gold", "es_72_kit_ergal_screws_blue",
     "es_73_kit_ergal_screws_black"],                                  # at most one
    ["es_97_bags_plates_gun_metal", "er_98_bags_plates_blue"],        # at most one
]

cfg["rules"]["dependencies"] = {
    "es_13_esseesse9_sunrise_red":   ["es_01_base_esseesse9_bormio_ice"],
    "es_14_esseesse9_riviera_green": ["es_01_base_esseesse9_bormio_ice"],
    "es_02_cnc_titanium_grey":       ["es_01_base_esseesse9_bormio_ice"],
}

cfg["groups"] = {
    "base_color":        ["es_13_esseesse9_sunrise_red", "es_14_esseesse9_riviera_green",
                          "es_02_cnc_titanium_grey"],
    "bellypan":          ["es_22_bellypan_bormio_grey_stripes", "es_23_bellypan_sunrise_red_grey_stripes",
                          "es_24_bellypan_riviera_green_grey_stripes", "es_25_bellypan_bormio_yellow_stripes",
                          "es_26_bellypan_sunrise_red_yellow_stripes", "es_27_bellypan_riviera_green_yellow_stripes"],
    "carbon_parts":      ["es_31_front_mudguard_carbon", "es_32_rear_mudguard_carbon",
                          "es_33_battery_cover_carbon", "es_34_tank_rib_carbon"],
    "suspension":        ["es_45_standard_suspensions", "es_46_kit_ohlins_suspensions"],
    "wheels":            ["es_57_standard_cast_aluminium_wheels", "es_58_forged_aluminium_wheels",
                          "es_59carbon_fiber_wheels"],
    "ergal_screws":      ["es_71_kit_ergal_screws_gold", "es_72_kit_ergal_screws_blue",
                          "es_73_kit_ergal_screws_black"],
    "optional_upgrades": ["es_60_rs_version", "es_84_windscreen_kit", "es_85_splash_guard",
                          "es_96_side_bags_kit", "es_97_bags_plates_gun_metal",
                          "er_98_bags_plates_blue", "background"],
}

save("essesse9", cfg)
print("ESSESSE9 patched")

# ============================================================
# EGO
# ============================================================
cfg = load("ego")

cfg["rules"]["always_visible"] = ["eg_01_base_ego_metal_black"]
for l in cfg["layers"]:
    if l["id"] in ["eg_24_frame_black", "background"]:
        l["always_visible"] = False
    if l["id"] == "eg_62_passenger_seat_standard":
        l["visible_by_default"] = True

cfg["rules"]["mutually_exclusive"] = [
    ["eg_13_tricolore", "eg_12_ego_rosso_corsa"],                  # color overlays
    ["eg_50_rider_seat_ego_tech_red", "eg_51_rider_seat_ego_tech_green"],  # rider seat
    ["eg_62_passenger_seat_standard", "eg_63_passenger_seat_ego_tech_red",
     "eg_64_passenger_seat_ego_tech_green", "eg_65_cover_corsaclienti_grey",
     "eg_66_cover_corsaclienti_white", "eg_67_cover_corsaclienti_black",
     "eg_68_cover_corsaclienti_red_copia"],                        # always one
    ["eg_78_standard_suspensions", "eg_79_kit_ohlins_suspensions"],  # always one
    ["eg_80_standard_cast_aluminium_wheels", "eg_81_red_stripe_cast_wheels",
     "eg_82_forged_aluminium_wheels", "eg_83_carbon_fiber_wheels"],  # always one
    ["eg_94_kit_ergal_screws_gold", "eg_95_kit_ergal_screws_black"],  # at most one
]

cfg["rules"]["dependencies"] = {
    "eg_13_tricolore":               ["eg_01_base_ego_metal_black"],
    "eg_12_ego_rosso_corsa":         ["eg_01_base_ego_metal_black"],
    "eg_50_rider_seat_ego_tech_red": ["eg_63_passenger_seat_ego_tech_red"],
    "eg_51_rider_seat_ego_tech_green": ["eg_64_passenger_seat_ego_tech_green"],
}

cfg["groups"] = {
    "base_color":        ["eg_13_tricolore", "eg_12_ego_rosso_corsa"],
    "carbon_parts":      ["eg_35_front_mudguard_carbon", "eg_36_rear_mudguard_carbon",
                          "eg_37_bellypan_carbon", "eg_38_undertail_cover_carbon"],
    "passenger_seat":    ["eg_62_passenger_seat_standard", "eg_63_passenger_seat_ego_tech_red",
                          "eg_64_passenger_seat_ego_tech_green", "eg_65_cover_corsaclienti_grey",
                          "eg_66_cover_corsaclienti_white", "eg_67_cover_corsaclienti_black",
                          "eg_68_cover_corsaclienti_red_copia"],
    "suspension":        ["eg_78_standard_suspensions", "eg_79_kit_ohlins_suspensions"],
    "wheels":            ["eg_80_standard_cast_aluminium_wheels", "eg_81_red_stripe_cast_wheels",
                          "eg_82_forged_aluminium_wheels", "eg_83_carbon_fiber_wheels"],
    "ergal_screws":      ["eg_94_kit_ergal_screws_gold", "eg_95_kit_ergal_screws_black"],
    "optional_upgrades": ["eg_24_frame_black", "eg_49_rs_version",
                          "eg_50_rider_seat_ego_tech_red", "eg_51_rider_seat_ego_tech_green",
                          "background"],
}

save("ego", cfg)
print("EGO patched")

# ============================================================
# EXPERIA
# ============================================================
cfg = load("experia")

cfg["rules"]["always_visible"] = ["ex_01_base_experia_metal_black"]
for l in cfg["layers"]:
    if l["id"] == "background":
        l["always_visible"] = False
    if l["id"] in ["ex_48_standard_injection_front_fender", "ex_50_standard_windscreen"]:
        l["visible_by_default"] = True

cfg["rules"]["mutually_exclusive"] = [
    ["ex_13_experia_white_flame", "ex_12_experia_bormio_ice"],       # color overlays
    ["ex_35_standard_cast_aluminium_wheels", "ex_36_red_stripe_cast_wheels",
     "ex_37_forged_aluminium_wheels"],                               # always one
    ["ex_48_standard_injection_front_fender", "ex_49_front_mudguard_carbon"],  # always one
    ["ex_50_standard_windscreen", "ex_51_low_windscreen_smoky"],     # always one
    ["ex_62_kit_ergal_screws_gold", "ex_63_kit_ergal_screws_black"], # at most one
]

cfg["rules"]["dependencies"] = {
    "ex_13_experia_white_flame": ["ex_01_base_experia_metal_black"],
    "ex_12_experia_bormio_ice":  ["ex_01_base_experia_metal_black"],
}

cfg["groups"] = {
    "base_color":        ["ex_13_experia_white_flame", "ex_12_experia_bormio_ice"],
    "wheels":            ["ex_35_standard_cast_aluminium_wheels", "ex_36_red_stripe_cast_wheels",
                          "ex_37_forged_aluminium_wheels"],
    "front_fender":      ["ex_48_standard_injection_front_fender", "ex_49_front_mudguard_carbon"],
    "windscreen":        ["ex_50_standard_windscreen", "ex_51_low_windscreen_smoky"],
    "ergal_screws":      ["ex_62_kit_ergal_screws_gold", "ex_63_kit_ergal_screws_black"],
    "optional_upgrades": ["ex_24_sportred_seat_kit", "ex_74_central_stand",
                          "ex_85_handguards", "ex_96_splash_guard",
                          "ex_107_top_case_kit", "ex_108_side_bags_kit", "background"],
}

save("experia", cfg)
print("EXPERIA patched")
print("\nAll 4 models patched per Paolo's spec.")
