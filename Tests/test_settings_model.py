"""Settings pipeline checks that run anywhere, without Windows or the WPF build.

`settings_model.py` is a transliteration of
`AstroHybrid.App/Services/LauncherService.BuildEnvironmentVariables`,
`AppSettings.Sanitize` and `MainWindowViewModel.PickBestSettings` into Python. Keeping the
launcher's tables in one place lets us check the things that actually broke or could break:

- a dropdown label with no entry in the table the launcher indexes with it (silently wrong setting),
- an index that goes out of range once hardware changes (dropped setting or exception),
- DLSS / frame generation / Reflex / the AMD driver features switched on for a card that cannot
  do them,
- frame generation and Fluid Motion Frames both wanting the picture,
- a resolution larger than the display,
- the launch environment for each GPU tier.

When the C# in those three places changes, change `settings_model.py` with it: a table that drifts
from the view model labels fails here instead of in the app.
"""
import sys

from settings_model import (FG_LABELS, FPS_LABELS, FPS_VALUES, NVIDIA50, NONE, OVERLAY_LABELS,
                            OVERLAY_VALUES, PAD_LABELS, PAD_VALUES, RADEON, RSR_LABELS,
                            RSR_SIZE_VALUES, SIZE_LABELS, SIZE_VALUES, SPEED_VALUES, TARGET_LABELS,
                            TARGET_VALUES, UPSCALE_LABELS, build_env, defaults, pick_best, sanitize)

fails = []


def check(name, cond, detail=""):
    if cond:
        print(f"PASS {name}")
    else:
        fails.append(name)
        print(f"FAIL {name} {detail}")


# 1. Every dropdown has exactly one entry per selectable value. RSR deliberately has one label more
#    than render sizes: its last entry means "leave the screen resolution alone" and is skipped.
pairs = [(FPS_LABELS, FPS_VALUES), (SIZE_LABELS, SIZE_VALUES), (TARGET_LABELS, TARGET_VALUES),
         (OVERLAY_LABELS, OVERLAY_VALUES), (PAD_LABELS, PAD_VALUES),
         (RSR_LABELS, list(RSR_SIZE_VALUES) + ["no-op"]),
         (UPSCALE_LABELS, range(len(UPSCALE_LABELS))), (FG_LABELS, range(len(FG_LABELS)))]
for labels, values in pairs:
    check(f"labels match table ({labels[0][:22]!r})", len(labels) == len(list(values)),
          f"{len(labels)} labels vs {len(list(values))} values")

# 2. Every index of every single-select setting builds an environment on every card type: a table
#    or guard that is off by one shows up here as an exception.
for hw_name, hw in (("nvidia50", NVIDIA50), ("radeon", RADEON), ("no-gpu", NONE)):
    for key, count in (("fps", len(FPS_VALUES)), ("size", len(SIZE_VALUES)),
                       ("overlay", len(OVERLAY_VALUES)), ("controller", len(PAD_VALUES)),
                       ("speed", len(SPEED_VALUES)), ("fgtarget", len(TARGET_VALUES)),
                       ("fgmode", len(FG_LABELS)), ("upscale", len(UPSCALE_LABELS)),
                       ("amdsize", len(RSR_LABELS))):
        for value in range(count):
            s = defaults()
            s[key] = value
            try:
                build_env(s, hw)
            except Exception as exc:  # noqa: BLE001
                fails.append(f"{hw_name}/{key}={value}")
                print(f"FAIL build_env {hw_name} {key}={value}: {exc!r}")
    print(f"PASS every index builds an environment on {hw_name}")

# 3. The FPS list, and the cap frame generation imposes instead of it.
s = defaults()
s["fps"] = 6
check("No limit maps to 'unlimited'", build_env(s, NVIDIA50)["ASTROHYBRID_FPS_LIMIT"] == "unlimited")
s = defaults()
s.update(upscale=1, fgmode=1, fgtarget=2)
env = build_env(s, NVIDIA50)
check("FG Auto 60 caps the game at 30", env["ASTROHYBRID_FPS_LIMIT"] == "30", env["ASTROHYBRID_FPS_LIMIT"])
check("FG Auto 60 passes the multiplier", env["ASTROHYBRID_DLSSG_FRAMES"] == "1", env.get("ASTROHYBRID_DLSSG_FRAMES"))
s.update(fgmode=4, fgtarget=4)
env = build_env(s, NVIDIA50)
check("FG fixed 4x to 120 caps the game at 30", env["ASTROHYBRID_FPS_LIMIT"] == "30", env["ASTROHYBRID_FPS_LIMIT"])
check("FG fixed 4x asks for 3 generated frames", env["ASTROHYBRID_DLSSG_FRAMES"] == "3", env.get("ASTROHYBRID_DLSSG_FRAMES"))

# 4. The AMD block only touches the environment on a card that supports it.
s = defaults()
s.update(amdfmf=True, amdrsr=True, amdsize=2)
env_none = build_env(s, NONE)
check("no AMD card: no AMD env changes",
      env_none["ASTROHYBRID_FPS_LIMIT"] == "30" and env_none["KYTY_GPU_FULLSCREEN"] == "1"
      and env_none["KYTY_GPU_WIDTH"] == "1920", env_none)
env_amd = build_env(s, RADEON)
check("AMD card: AFMF removes the cap", env_amd["ASTROHYBRID_FPS_LIMIT"] == "unlimited", env_amd["ASTROHYBRID_FPS_LIMIT"])
check("AMD card: RSR windowed 1080p wins over fullscreen",
      env_amd["KYTY_GPU_FULLSCREEN"] == "0" and env_amd["KYTY_GPU_WIDTH"] == "1920"
      and env_amd["KYTY_GPU_HEIGHT"] == "1080", env_amd)

# 5. VSync and Fluid Motion Frames cannot both take effect.
s = defaults()
s.update(amdfmf=True, vsync=True)
check("AFMF suppresses the FIFO present mode", "KYTY_GPU_PRESENT_MODE" not in build_env(s, RADEON))
check("VSync alone still sets FIFO",
      build_env(dict(defaults(), vsync=True), RADEON).get("KYTY_GPU_PRESENT_MODE") == "Fifo")

# 6. Sanitize: a stale or hand-edited settings file can never describe an impossible setup.
hostile = dict(defaults(), upscale=1, fgmode=3, amdfmf=True, amdrsr=True, amdsize=3, fps=99,
               size=-1, fgtarget=42, overlay=9)
clean = sanitize(hostile, RADEON)
check("sanitize clears DLSS on a Radeon", clean["upscale"] == 0, clean)
check("sanitize clears NVIDIA frame generation on a Radeon", clean["fgmode"] == 0, clean)
check("sanitize keeps RSR but gives it a real render size", clean["amdrsr"] and clean["amdsize"] == 2, clean)
check("sanitize drops out-of-range indices",
      (clean["fps"], clean["size"], clean["fgtarget"], clean["overlay"]) == (0, 2, 2, 0), clean)
clean = sanitize(dict(defaults(), amdfmf=True, amdrsr=True), RADEON)
check("sanitize keeps one frame generator and one upscaler", clean["amdfmf"] and clean["amdrsr"], clean)
clean = sanitize(dict(defaults(), amdfmf=True, vsync=True, fullscreen=False), RADEON)
check("sanitize forces AFMF's fullscreen, no-VSync state", clean["fullscreen"] and not clean["vsync"], clean)
clean = sanitize(dict(defaults(), upscale=1, fgmode=1, lowlatency=True), NONE)
check("sanitize clears NVIDIA features on a non-RTX card",
      clean["upscale"] == 0 and clean["fgmode"] == 0 and clean["lowlatency"] is False, clean)

# 7. PickBestSettings and the environment a fresh install launches with, per tier.
tiers = [
    ("RTX 50 @1440p165", (2560, 1440, 50, 165), dict(size=3, upscale=1, fgmode=1, fgtarget=4, lowlatency=True)),
    ("RTX 50 @1440p90", (2560, 1440, 50, 90), dict(size=3, upscale=1, fgmode=1, fgtarget=3, lowlatency=True)),
    ("RTX 40 @1440p60", (2560, 1440, 40, 60), dict(size=3, upscale=1, fgmode=1, fgtarget=2, lowlatency=True)),
    ("RTX 30 @1080p", (1920, 1080, 30, 60), dict(size=2, upscale=1, fgmode=0, fgtarget=2, lowlatency=True)),
    ("RTX 20 @720p", (1280, 720, 20, 60), dict(size=0, upscale=1, fgmode=0, fgtarget=2, lowlatency=True)),
    ("RX 6600 @1080p", (1920, 1080, 0, 60), dict(size=2, upscale=0, fgmode=0, fgtarget=2, lowlatency=False)),
]
for name, args, want in tiers:
    got = pick_best(*args)
    check(f"best settings {name}", got == want, f"{got} != {want}")
    env = build_env(dict(defaults(), **got), NVIDIA50 if args[2] >= 20 else NONE)
    if got["fgmode"]:
        # Auto starts at 2x and the engine raises the multiplier in game.
        want_limit = str(max(30, TARGET_VALUES[got["fgtarget"]] // 2))
    else:
        want_limit = "30"  # ApplyBestSettings always starts from the 30 FPS cap
    check(f"best settings {name} caps the game at {want_limit}", env["ASTROHYBRID_FPS_LIMIT"] == want_limit, env)

# 8. The resolution chosen never exceeds the display.
for w, h in [(1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3440, 1440), (3840, 2160)]:
    size = pick_best(w, h, 0, 60)["size"]
    rw, rh = SIZE_VALUES[size]
    check(f"resolution fits {w}x{h}", rw <= w and rh <= h, f"picked {rw}x{rh}")

print()
if fails:
    print(f"{len(fails)} FAILURE(S): {fails}")
    sys.exit(1)
print("all settings checks passed")
