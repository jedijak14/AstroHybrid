"""Python transliteration of the launcher's index -> environment mapping.

Mirrors AstroHybrid.App/Services/LauncherService.BuildEnvironmentVariables and the label arrays in
the view models. If a label and a table ever disagree, the test that imports this fails.
"""
FPS_VALUES = ["30", "35", "45", "50", "55", "60", "unlimited"]
FPS_LABELS = ["30 FPS - steady (recommended)", "35 FPS", "45 FPS", "50 FPS", "55 FPS", "60 FPS", "No limit"]

SIZE_VALUES = [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440)]
SIZE_LABELS = ["1280 x 720", "1600 x 900", "1920 x 1080", "2560 x 1440"]

TARGET_VALUES = [0, 50, 60, 90, 120, 144, 165]
TARGET_LABELS = ["No lock - game as fast as it can"] + [f"{v} FPS on screen" for v in TARGET_VALUES[1:]]

OVERLAY_VALUES = ["", "fps", "compact", "full"]
OVERLAY_LABELS = ["Off (F2 shows it)", "FPS only", "FPS + CPU, GPU, VRAM, RAM", "Everything (all stats)"]

PAD_VALUES = ["auto", "ps", "xbox", "switch", "generic"]
PAD_LABELS = ["Auto", "PlayStation", "Xbox", "Switch", "Generic"]

SPEED_VALUES = ["100", "95", "90", "85", "80", "75"]

UPSCALE_LABELS = ["Game's own (default)", "NVIDIA DLSS - sharper image"]
FG_LABELS = ["Off (default)", "Auto - reach target (recommended)", "Fixed 2x", "Fixed 3x", "Fixed 4x"]

RSR_SIZE_VALUES = [(1280, 720), (1600, 900), (1920, 1080)]
RSR_LABELS = ["1280 x 720 (upscaled)", "1600 x 900 (upscaled)", "1920 x 1080 (upscaled)",
              "Screen resolution (RSR does nothing)"]


def build_env(settings, hardware):
    """settings: dict. hardware: dict of support flags. Returns the env dict."""
    env = {}
    if settings["size"] < 4:
        env["KYTY_GPU_WIDTH"], env["KYTY_GPU_HEIGHT"] = (str(x) for x in SIZE_VALUES[settings["size"]])
    env["KYTY_GPU_FULLSCREEN"] = "1" if settings["fullscreen"] else "0"
    env["ASTROHYBRID_FPS_LIMIT"] = FPS_VALUES[settings["fps"]]
    if settings["overlay"] < 4:
        env["ASTROHYBRID_OVERLAY"] = OVERLAY_VALUES[settings["overlay"]]
    if settings["upscale"] or settings["fgmode"]:
        env["ASTROHYBRID_CUDA_HOLE"] = "1"
        env["ASTROHYBRID_DLSS_PATH"] = "Build\\RunHybrid"
    if settings["upscale"]:
        env["ASTROHYBRID_DLSS"] = "1"
    if settings["fgmode"]:
        goal = TARGET_VALUES[settings["fgtarget"]]
        mult = 2 if settings["fgmode"] == 1 else min(max(settings["fgmode"], 2), 4)
        limit = 0 if goal == 0 else max(30, goal // mult)
        env["ASTROHYBRID_DLSSG"] = "1"
        env["ASTROHYBRID_DLSSG_FRAMES"] = str(mult - 1)
        if settings["fgmode"] == 1 and goal:
            env["ASTROHYBRID_DLSSG_TARGET"] = str(goal)
            env["ASTROHYBRID_DLSSG_MAX_FRAMES"] = "3"
        env["ASTROHYBRID_FPS_LIMIT"] = "unlimited" if limit == 0 else str(limit)
    if settings["amdfmf"] and hardware["amdfmf"]:
        env["KYTY_GPU_FULLSCREEN"] = "1"
        env["ASTROHYBRID_FPS_LIMIT"] = "unlimited"
    if settings["amdrsr"] and hardware["amdrsr"] and settings["amdsize"] < 3:
        w, h = RSR_SIZE_VALUES[settings["amdsize"]]
        env["KYTY_GPU_WIDTH"], env["KYTY_GPU_HEIGHT"] = str(w), str(h)
        env["KYTY_GPU_FULLSCREEN"] = "0"
    if settings["lowlatency"]:
        env["ASTROHYBRID_LOW_LATENCY"] = "1"
    if settings["controller"] < 5:
        env["ASTROHYBRID_PAD_PREFER"] = PAD_VALUES[settings["controller"]]
    if settings["speed"] < 6:
        env["ASTROHYBRID_GAME_SPEED_PERCENT"] = SPEED_VALUES[settings["speed"]]
    if settings["vsync"] and not (settings["amdfmf"] and hardware["amdfmf"]):
        env["KYTY_GPU_PRESENT_MODE"] = "Fifo"
    return env


def defaults():
    return dict(fps=0, size=2, fullscreen=True, overlay=0, upscale=0, fgmode=0, fgtarget=2,
                lowlatency=False, controller=0, speed=0, vsync=False,
                amdfmf=False, amdrsr=False, amdsize=2)


NVIDIA50 = dict(dlss=True, fg=True, amdfmf=False, amdrsr=False)
RADEON = dict(dlss=False, fg=False, amdfmf=True, amdrsr=True)
NONE = dict(dlss=False, fg=False, amdfmf=False, amdrsr=False)


def sanitize(s, hw):
    """Mirrors AppSettings.Sanitize."""
    s = dict(s)
    for key, hi, fallback in (("fps", 6, 0), ("speed", 5, 0), ("size", 3, 2), ("overlay", 3, 0),
                              ("controller", 4, 0), ("fgtarget", 6, 2), ("upscale", 1, 0),
                              ("fgmode", 4, 0), ("amdsize", 3, 2)):
        if s[key] < 0 or s[key] > hi:
            s[key] = fallback
    if hw is None or not hw["dlss"]:
        s["upscale"] = 0
    if hw is None or not hw["fg"] or s["upscale"] == 0:
        s["fgmode"] = 0
    if hw is None or not hw.get("reflex", hw["dlss"]):
        s["lowlatency"] = False
    if hw is None or not hw["amdfmf"]:
        s["amdfmf"] = False
    if hw is None or not hw["amdrsr"]:
        s["amdrsr"] = False
    if s["upscale"] != 0:
        s["amdrsr"] = False
    if s["fgmode"] != 0:
        s["amdfmf"] = False
    if s["amdfmf"]:
        s["fullscreen"] = True
        s["vsync"] = False
    if s["amdrsr"] and s["amdsize"] >= 3:
        s["amdsize"] = 2
    return s


def pick_best(screen_w, screen_h, rtx_series, hz):
    """Mirrors MainWindowViewModel.PickBestSettings for a PC's display and card."""
    size = 2
    for i, (w, h) in enumerate(SIZE_VALUES):
        if w <= screen_w and h <= screen_h:
            size = i
    upscale, fg, target, low = 0, 0, 2, False
    if rtx_series >= 20:
        upscale, low = 1, True
    if rtx_series >= 40:
        fg = 1
        goal = 120 if (rtx_series >= 50 and hz >= 120) else 90 if (rtx_series >= 50 and hz >= 90) else 60
        target = TARGET_VALUES.index(goal)
    return dict(size=size, upscale=upscale, fgmode=fg, fgtarget=target, lowlatency=low)
