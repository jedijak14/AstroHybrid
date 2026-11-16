using System;
using System.Text.Json.Serialization;
using AstroHybrid.App.Services;

namespace AstroHybrid.App.Models
{
    public class AppSettings
    {
        [JsonPropertyName("lighting")]
        public int Lighting { get; set; } = 0;

        [JsonPropertyName("fps")]
        public int Fps { get; set; } = 0;

        [JsonPropertyName("fpsv")]
        public int FpsVersion { get; set; } = 2;

        [JsonPropertyName("size")]
        public int Size { get; set; } = 2;

        [JsonPropertyName("fullscreen")]
        public bool Fullscreen { get; set; } = true;

        // Use the game's 21:9 render-space patch when the display is ultrawide.
        [JsonPropertyName("ultrawide")]
        public bool Ultrawide { get; set; } = false;

        [JsonPropertyName("realspeed")]
        public bool RealSpeed { get; set; } = true;

        [JsonPropertyName("speed")]
        public int Speed { get; set; } = 0;

        [JsonPropertyName("overlay")]
        public int Overlay { get; set; } = 0;

        [JsonPropertyName("upscale")]
        public int Upscale { get; set; } = 0;

        [JsonPropertyName("fgmode")]
        public int FrameGenMode { get; set; } = 0;

        [JsonPropertyName("lowlatency")]
        public bool LowLatency { get; set; } = false;

        [JsonPropertyName("fgtarget")]
        public int FrameGenTarget { get; set; } = 2;

        // AMD Radeon features (Graphics page). Both are driver-level: the launcher sets up the game
        // for them (fullscreen, no VSync, a render resolution below the screen) and Adrenalin does the
        // rest per game. Stored as separate answers so turning one off leaves the other alone.
        [JsonPropertyName("amdfmf")]
        public bool AmdFluidMotion { get; set; } = false;

        [JsonPropertyName("amdrsr")]
        public bool AmdSuperResolution { get; set; } = false;

        // Output resolution while Radeon Super Resolution upscales: 0 = 720p, 1 = 900p, 2 = 1080p,
        // 3 = leave the game at the screen resolution (RSR then does nothing).
        [JsonPropertyName("amdsize")]
        public int AmdRenderSize { get; set; } = 2;

        [JsonPropertyName("pad")]
        public int Controller { get; set; } = 0;

        // Preset index used by older builds: 0 = Off, 1 = 40, 2 = 70, 3 = 100, 4 = 150 (percent).
        [JsonPropertyName("rumble")]
        public int Rumble { get; set; } = 2;

        // Vibration strength in percent (0-200); -1 when the file predates it and only "rumble" is known.
        [JsonPropertyName("rumblepct")]
        public int RumblePercent { get; set; } = -1;

        [JsonPropertyName("switchboost")]
        public bool SwitchBoost { get; set; } = true;

        // Installation settings
        [JsonPropertyName("installPath")]
        public string? InstallPath { get; set; }

        [JsonPropertyName("gameDumpPath")]
        public string? GameDumpPath { get; set; }

        [JsonPropertyName("gameVersion")]
        public string? GameVersion { get; set; }

        [JsonPropertyName("gameTitleId")]
        public string? GameTitleId { get; set; }

        [JsonPropertyName("installationManifest")]
        public InstallationManifest? InstallationManifest { get; set; }

        // First run tracking
        // Game language: -1 = follow Windows, else the console language number (ANYPS5_LANGUAGE).
        [JsonPropertyName("language")]
        public int Language { get; set; } = -1;

        // VSync (Vulkan FIFO presentation) instead of immediate presentation: no tearing.
        [JsonPropertyName("vsync")]
        public bool VSync { get; set; } = false;

        // Graphics card the launcher describes and hands to the game: index into the detected
        // adapters, -1 = automatic (the best card, discrete over integrated) - issue #24.
        [JsonPropertyName("gpu")]
        public int Gpu { get; set; } = -1;

        // Runtime options (Advanced page), passed to Run-AstroHybrid.bat; defaults are the script's own.
        [JsonPropertyName("hangWatchdog")]
        public bool HangWatchdog { get; set; } = false;

        [JsonPropertyName("shaderCache")]
        public bool ShaderCache { get; set; } = true;

        [JsonPropertyName("drawPrepTuning")]
        public bool DrawPrepTuning { get; set; } = true;

        [JsonPropertyName("priority")]
        public string Priority { get; set; } = "abovenormal";

        [JsonPropertyName("cpPriority")]
        public int CpPriority { get; set; } = 2;

        [JsonPropertyName("padMotion")]
        public bool MotionControls { get; set; } = true;

        [JsonPropertyName("triggerState")]
        public bool TriggerState { get; set; } = true;

        // Wireless DualSense features (Bluetooth HID audio/haptics) - issue #34
        [JsonPropertyName("dsWirelessSpeaker")]
        public bool DualSenseWirelessSpeaker { get; set; } = true;

        [JsonPropertyName("dsWirelessHaptics")]
        public bool DualSenseWirelessHaptics { get; set; } = true;

        // Set by the setup wizard: the main window picks the best settings for this PC once.
        [JsonPropertyName("applyBestOnStart")]
        public bool ApplyBestOnStart { get; set; } = false;

        [JsonPropertyName("firstRunComplete")]
        public bool FirstRunComplete { get; set; } = false;

        [JsonPropertyName("lastLaunched")]
        public DateTime? LastLaunched { get; set; }

        // Update settings
        [JsonPropertyName("lastUpdateCheck")]
        public DateTime? LastUpdateCheck { get; set; }

        [JsonPropertyName("ignoredUpdateVersion")]
        public string? IgnoredUpdateVersion { get; set; }

        [JsonPropertyName("autoCheckUpdates")]
        public bool AutoCheckUpdates { get; set; } = true;

        // Vibration strength the game gets: the stored percent, or the old preset index mapped to percent.
        [JsonIgnore]
        public int EffectiveRumblePercent => RumbleSetting.EffectivePercent(RumblePercent, Rumble);

        // Makes a loaded file describe something this PC can actually do, and drops index values that
        // point outside the launcher's own lists. Called once hardware is known. Only values that
        // cannot work are changed; a combination that is merely a bad idea is left for the note on
        // the Graphics page to explain.
        public void Sanitize(HardwareInfo? hardware)
        {
            if (Fps < 0 || Fps > 6) Fps = 0;
            if (Speed < 0 || Speed > 5) Speed = 0;
            if (Size < 0 || Size > 3) Size = 2;
            if (Overlay < 0 || Overlay > 3) Overlay = 0;
            if (Controller < 0 || Controller > 4) Controller = 0;
            if (FrameGenTarget < 0 || FrameGenTarget > 6) FrameGenTarget = 2;
            if (Upscale < 0 || Upscale > 1) Upscale = 0;
            if (FrameGenMode < 0 || FrameGenMode > 4) FrameGenMode = 0;
            if (AmdRenderSize < 0 || AmdRenderSize > 3) AmdRenderSize = 2;
            if (RumblePercent < 0 || RumblePercent > 200) RumblePercent = 70;

            // NVIDIA features need the card, and frame generation also needs an upscaler to run on.
            if (hardware == null || !hardware.SupportsDlss) Upscale = 0;
            if (hardware == null || !hardware.SupportsFrameGeneration || Upscale == 0) FrameGenMode = 0;
            // Reflex is VK_NV_low_latency2: without an RTX card the engine only logs "requested but
            // unavailable: off", so stop asking.
            if (hardware == null || !hardware.SupportsReflex) LowLatency = false;

            // AMD features need a Radeon card AMD's list covers.
            if (hardware == null || !hardware.SupportsAmdFluidMotion) AmdFluidMotion = false;
            if (hardware == null || !hardware.SupportsAmdSuperResolution) AmdSuperResolution = false;

            // Two upscalers and two frame generators cannot both be right.
            if (Upscale != 0) AmdSuperResolution = false;
            if (FrameGenMode != 0) AmdFluidMotion = false;

            // Fluid Motion Frames needs a fullscreen window with VSync off; Radeon Super Resolution
            // needs a window and a render size below the screen's.
            if (AmdFluidMotion)
            {
                Fullscreen = true;
                VSync = false;
            }
            if (AmdSuperResolution && AmdRenderSize >= 3) AmdRenderSize = 2;
        }

        // Writes both fields after loading, so an older launcher and this build read the same strength.
        public void NormalizeRumble()
        {
            RumblePercent = EffectiveRumblePercent;
            Rumble = RumbleSetting.ToLegacyIndex(RumblePercent);
        }
    }

    public class InstallationManifest
    {
        [JsonPropertyName("installedAt")]
        public DateTime InstalledAt { get; set; }

        [JsonPropertyName("gameVersion")]
        public string GameVersion { get; set; } = "";

        [JsonPropertyName("gameTitleId")]
        public string GameTitleId { get; set; } = "";

        [JsonPropertyName("anyps5Version")]
        public string AnyPs5Version { get; set; } = "";

        [JsonPropertyName("kytyVersion")]
        public string KytyVersion { get; set; } = "";

        [JsonPropertyName("installationPath")]
        public string InstallationPath { get; set; } = "";

        [JsonPropertyName("gameDumpPath")]
        public string GameDumpPath { get; set; } = "";

        [JsonPropertyName("files")]
        public string[] Files { get; set; } = Array.Empty<string>();
    }
}
