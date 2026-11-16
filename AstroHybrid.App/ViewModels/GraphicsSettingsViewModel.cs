using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using AstroHybrid.App.Models;

namespace AstroHybrid.App.ViewModels
{
    public class GraphicsSettingsViewModel : ViewModelBase
    {
        private readonly MainWindowViewModel _mainViewModel;

        public GraphicsSettingsViewModel(MainWindowViewModel mainViewModel)
        {
            _mainViewModel = mainViewModel;
            _mainViewModel.PropertyChanged += (sender, e) => OnPropertyChanged(string.Empty);
        }

        // Resolution
        public string[] ResolutionLabels => new[] { "1280 x 720", "1600 x 900", "1920 x 1080", "2560 x 1440" };

        public int ResolutionIndex
        {
            get => _mainViewModel.Settings.Size;
            set
            {
                if (_mainViewModel.Settings.Size != value)
                {
                    _mainViewModel.Settings.Size = value;
                    OnPropertyChanged();
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // Graphics card (issue #24). A laptop with hybrid graphics reports two adapters, and the one
        // that drives the built-in screen is usually the integrated GPU: the launcher must describe
        // (and enable NVIDIA features for) a card the user can pick, not just the first adapter.
        public bool HasGpuChoice => (_mainViewModel.HardwareInfo?.Gpus.Count ?? 0) > 1;

        public string[] GpuLabels
        {
            get
            {
                var labels = new List<string> { "Automatic - best graphics card" };
                foreach (var gpu in _mainViewModel.HardwareInfo?.Gpus ?? new List<GpuAdapter>())
                    labels.Add(gpu.Label);
                return labels.ToArray();
            }
        }

        public int GpuIndex
        {
            get => (_mainViewModel.HardwareInfo?.SelectedGpuIndex ?? -1) + 1;
            set
            {
                var hardware = _mainViewModel.HardwareInfo;
                var selected = value - 1;
                if (hardware == null || selected < -1 || selected >= hardware.Gpus.Count || hardware.SelectedGpuIndex == selected)
                    return;

                hardware.SelectGpu(selected);
                _mainViewModel.Settings.Gpu = selected;

                // DLSS, frame generation and the AMD driver features need their card: a card without
                // them turns the options off instead of leaving settings the launcher cannot honour.
                _mainViewModel.Settings.Sanitize(hardware);

                OnPropertyChanged();
                OnPropertyChanged(nameof(GpuNote));
                OnPropertyChanged(nameof(HardwareNote));
                OnPropertyChanged(nameof(UpscaleIndex));
                OnPropertyChanged(nameof(FrameGenIndex));
                OnPropertyChanged(nameof(SupportsDlss));
                OnPropertyChanged(nameof(SupportsReflex));
                OnPropertyChanged(nameof(IsFrameGenAvailable));
                OnPropertyChanged(nameof(SupportsAmd));
                OnPropertyChanged(nameof(AmdFeaturesNote));
                OnPropertyChanged(nameof(AmdNote));
                OnPropertyChanged(nameof(AmdFluidMotion));
                OnPropertyChanged(nameof(AmdSuperResolution));
                OnPropertyChanged(nameof(AmdRenderSizeIndex));
                OnPropertyChanged(nameof(AmdRenderSizeEnabled));
                // Sanitize may also have changed these, and the Display card shows them.
                OnPropertyChanged(nameof(Fullscreen));
                OnPropertyChanged(nameof(VSync));
                OnPropertyChanged(nameof(FpsIndex));
                OnPropertyChanged(nameof(RayTracingIndex));
                OnPropertyChanged(nameof(FrameGenTargetIndex));
                OnPropertyChanged(nameof(OverlayIndex));
                OnPropertyChanged(nameof(IsFpsLimitEnabled));
                OnPropertyChanged(nameof(IsVSyncAvailable));
                OnPropertyChanged(nameof(VSyncNote));
                OnPropertyChanged(nameof(FpsLimitNote));
                _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.HardwareInfo));
                _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
            }
        }

        public string GpuNote
        {
            get
            {
                var hardware = _mainViewModel.HardwareInfo;
                if (hardware == null || hardware.Gpus.Count == 0)
                    return "No graphics card detected.";

                var detected = string.Join(", ", hardware.Gpus.Select(g =>
                    $"{g.Name} ({(g.IsDiscrete ? "discrete" : g.IsIntegrated ? "integrated" : "graphics")})"));
                var text = "Detected: " + detected + ".";

                if (hardware.SelectedGpuIndex < 0)
                    text += " Automatic uses the discrete card: the renderer prefers one over integrated graphics.";
                else
                    text += " The choice is passed to the game as ANYPS5_GPU; the renderer also prefers a discrete card by itself.";

                if (hardware.SelectedGpu?.SupportsAmdSuperResolution == true)
                    text += " AMD Software's Fluid Motion Frames and Radeon Super Resolution apply to this card.";
                else if (hardware.SelectedGpu?.RtxSeries >= 20)
                    text += " DLSS, Reflex and frame generation use this card.";
                else if (hardware.Gpus.Any(g => g.RtxSeries >= 20))
                    text += " The NVIDIA options need the RTX card: pick it, or Automatic, to use them.";
                return text;
            }
        }

        // Fullscreen
        public bool Fullscreen
        {
            get => _mainViewModel.Settings.Fullscreen;
            set
            {
                if (_mainViewModel.Settings.Fullscreen != value)
                {
                    _mainViewModel.Settings.Fullscreen = value;
                    OnPropertyChanged();
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // Ultrawide render-space patch (issue #29/#33).
        public bool Ultrawide
        {
            get => _mainViewModel.Settings.Ultrawide;
            set
            {
                if (_mainViewModel.Settings.Ultrawide != value)
                {
                    _mainViewModel.Settings.Ultrawide = value;
                    OnPropertyChanged();
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        public string UltrawideNote => "Uses the 21:9 game patch when the generated ultrawide executable is available; 16:9 remains unchanged.";

        // Ray Tracing / Lighting mode (0 = OFF / Non-RT, 1 = ON / Ray Tracing)
        public string[] RayTracingLabels => new[] { "OFF - Faster lighting (Non-RT, recommended)", "ON - Ray Tracing (Original lighting)" };

        public int RayTracingIndex
        {
            get => _mainViewModel.Settings.Lighting;
            set
            {
                if (_mainViewModel.Settings.Lighting != value)
                {
                    _mainViewModel.Settings.Lighting = value;
                    OnPropertyChanged();
                    OnPropertyChanged(nameof(RayTracingNote));
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        public string RayTracingNote => _mainViewModel.Settings.Lighting == 1
            ? "Ray Tracing ON: runs AstroBot.exe with full GI probes and ray-traced lighting shaders (higher GPU load)."
            : "Ray Tracing OFF: runs AstroBot-NonRT-SoftAssert.exe for faster performance and steadier frame times.";

        // NVIDIA frame generation presents the frames itself, and its VSync works only on D3D12 (Streamline
        // DLSS-G guide, 22.5); this port draws with Vulkan, so VSync applies only with frame generation off.
        public bool IsVSyncAvailable => _mainViewModel.Settings.FrameGenMode == 0;
        public string VSyncNote => IsVSyncAvailable
            ? "Locks presentation to your screen's refresh (no tearing)."
            : "Not available with frame generation: NVIDIA frame generation can't use VSync with Vulkan. For no tearing, use a G-Sync / FreeSync screen (with G-Sync on, keep the on-screen target below its refresh rate), or turn frame generation off and tick VSync.";

        // VSync
        public bool VSync
        {
            get => _mainViewModel.Settings.VSync;
            set
            {
                if (_mainViewModel.Settings.VSync != value)
                {
                    _mainViewModel.Settings.VSync = value;
                    OnPropertyChanged();
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // With frame generation on, the target sets the game's own limit (as in the classic launcher).
        public bool IsFpsLimitEnabled => _mainViewModel.Settings.FrameGenMode == 0;
        public string FpsLimitNote => IsFpsLimitEnabled
            ? "The game may run below the selected limit in demanding scenes."
            : "Frame generation is on: the game's own limit comes from the frame generation target below (60 on screen = game at 30 x2). Turn frame generation off to use this limit.";

        // FPS Limiter
        public string[] FpsLabels => new[] { "30 FPS - steady (recommended)", "35 FPS", "45 FPS", "50 FPS", "55 FPS", "60 FPS", "No limit" };

        public int FpsIndex
        {
            get => _mainViewModel.Settings.Fps;
            set
            {
                if (_mainViewModel.Settings.Fps != value)
                {
                    _mainViewModel.Settings.Fps = value;
                    OnPropertyChanged();
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // Upscaling
        public string[] UpscaleLabels => new[] { "Game's own (default)", "NVIDIA DLSS - sharper image" };

        public int UpscaleIndex
        {
            get => _mainViewModel.Settings.Upscale;
            set
            {
                if (_mainViewModel.Settings.Upscale != value)
                {
                    _mainViewModel.Settings.Upscale = value;
                    // DLSS and Radeon Super Resolution are both upscalers: AMD's own guidance is not
                    // to stack them, so choosing DLSS turns RSR off (and the reverse, below).
                    if (value != 0 && _mainViewModel.Settings.AmdSuperResolution)
                        _mainViewModel.Settings.AmdSuperResolution = false;
                    OnPropertyChanged();
                    OnPropertyChanged(nameof(IsFrameGenAvailable));
                    OnPropertyChanged(nameof(FrameGenNote));
                    OnPropertyChanged(nameof(AmdSuperResolution));
                    OnPropertyChanged(nameof(AmdRenderSizeIndex));
                    OnPropertyChanged(nameof(AmdRenderSizeEnabled));
                    OnPropertyChanged(nameof(AmdNote));
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // Frame Generation
        public string[] FrameGenLabels => new[] { "Off (default)", "Auto - reach target (recommended)", "Fixed 2x", "Fixed 3x", "Fixed 4x" };

        public int FrameGenIndex
        {
            get => _mainViewModel.Settings.FrameGenMode;
            set
            {
                if (_mainViewModel.Settings.FrameGenMode != value)
                {
                    _mainViewModel.Settings.FrameGenMode = value;
                    // Both smooth the picture by showing generated frames; two of them at once would
                    // multiply each other's output, so one or the other.
                    if (value != 0 && _mainViewModel.Settings.AmdFluidMotion)
                    {
                        _mainViewModel.Settings.AmdFluidMotion = false;
                        OnPropertyChanged(nameof(AmdFluidMotion));
                        OnPropertyChanged(nameof(AmdNote));
                    }
                    OnPropertyChanged();
                    OnPropertyChanged(nameof(IsFrameGenTargetEnabled));
                    OnPropertyChanged(nameof(FrameGenNote));
                    OnPropertyChanged(nameof(IsFpsLimitEnabled));
                    OnPropertyChanged(nameof(IsVSyncAvailable));
                    OnPropertyChanged(nameof(VSyncNote));
                    OnPropertyChanged(nameof(FpsLimitNote));
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // Frame Gen Target
        public string[] FrameGenTargetLabels => new[] { "No lock - game as fast as it can", "50 FPS on screen", "60 FPS on screen (recommended)", "90 FPS on screen", "120 FPS on screen", "144 FPS on screen", "165 FPS on screen" };

        public int FrameGenTargetIndex
        {
            get => _mainViewModel.Settings.FrameGenTarget;
            set
            {
                if (_mainViewModel.Settings.FrameGenTarget != value)
                {
                    _mainViewModel.Settings.FrameGenTarget = value;
                    OnPropertyChanged();
                    OnPropertyChanged(nameof(FrameGenNote));
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // NVIDIA Reflex
        public bool LowLatency
        {
            get => _mainViewModel.Settings.LowLatency;
            set
            {
                if (_mainViewModel.Settings.LowLatency != value)
                {
                    _mainViewModel.Settings.LowLatency = value;
                    OnPropertyChanged();
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // ---- AMD Radeon features -------------------------------------------------------------
        // Unlike DLSS and frame generation there is no game-side switch here: Fluid Motion Frames
        // and Radeon Super Resolution belong to AMD Software (Adrenalin) and are switched on per
        // game there. What the launcher can do is put the game in the state they need, so that is
        // what these options change.

        public bool AmdFluidMotion
        {
            get => _mainViewModel.Settings.AmdFluidMotion;
            set
            {
                if (_mainViewModel.Settings.AmdFluidMotion == value) return;
                _mainViewModel.Settings.AmdFluidMotion = value;
                if (value)
                {
                    // AMD's requirements: a fullscreen window, VSync off, and the game's own cap off
                    // (the driver generates frames against whatever the game presents).
                    _mainViewModel.Settings.Fullscreen = true;
                    _mainViewModel.Settings.VSync = false;
                    _mainViewModel.Settings.Fps = 6;
                    // Two frame generators at once make no sense.
                    if (_mainViewModel.Settings.FrameGenMode != 0)
                        _mainViewModel.Settings.FrameGenMode = 0;
                }
                OnPropertyChanged();
                OnPropertyChanged(nameof(Fullscreen));
                OnPropertyChanged(nameof(VSync));
                OnPropertyChanged(nameof(FpsIndex));
                OnPropertyChanged(nameof(AmdNote));
                OnPropertyChanged(nameof(FrameGenIndex));
                OnPropertyChanged(nameof(FrameGenNote));
                OnPropertyChanged(nameof(IsFpsLimitEnabled));
                OnPropertyChanged(nameof(IsVSyncAvailable));
                OnPropertyChanged(nameof(IsFrameGenAvailable));
                _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
            }
        }

        public bool AmdSuperResolution
        {
            get => _mainViewModel.Settings.AmdSuperResolution;
            set
            {
                if (_mainViewModel.Settings.AmdSuperResolution == value) return;
                _mainViewModel.Settings.AmdSuperResolution = value;
                if (value)
                {
                    // RSR upscales whatever the game renders up to the screen's resolution, so the
                    // window is no longer fixed at the screen's size.
                    _mainViewModel.Settings.Fullscreen = false;
                    // Double upscaling: hand the job to one of them.
                    if (_mainViewModel.Settings.Upscale != 0)
                        _mainViewModel.Settings.Upscale = 0;
                }
                OnPropertyChanged();
                // Fullscreen, VSync and the limit may have been changed for Fluid Motion Frames.
                OnPropertyChanged(nameof(Fullscreen));
                OnPropertyChanged(nameof(VSync));
                OnPropertyChanged(nameof(FpsIndex));
                OnPropertyChanged(nameof(UpscaleIndex));
                OnPropertyChanged(nameof(AmdRenderSizeIndex));
                OnPropertyChanged(nameof(AmdRenderSizeEnabled));
                OnPropertyChanged(nameof(AmdNote));
                OnPropertyChanged(nameof(IsFrameGenAvailable));
                _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
            }
        }

        // The resolution the game renders at while RSR upscales it to the screen.
        public string[] AmdRenderSizeLabels => new[]
        {
            "1280 x 720 (upscaled)", "1600 x 900 (upscaled)", "1920 x 1080 (upscaled)",
            "Screen resolution (RSR does nothing)"
        };

        public int AmdRenderSizeIndex
        {
            get => _mainViewModel.Settings.AmdRenderSize;
            set
            {
                if (_mainViewModel.Settings.AmdRenderSize == value) return;
                _mainViewModel.Settings.AmdRenderSize = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(AmdRenderSizeEnabled));
                OnPropertyChanged(nameof(AmdNote));
                _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
            }
        }

        // RSR only makes sense with a render resolution below the screen's.
        public bool AmdRenderSizeEnabled => AmdSuperResolution && AmdRenderSizeIndex < 3;

        // What the card header says: which Radeon card was found and whether AMD Software covers it.
        public string AmdFeaturesNote
        {
            get
            {
                var hardware = _mainViewModel.HardwareInfo;
                if (hardware == null) return "";

                var name = hardware.GpuName;
                if (hardware.SupportsAmdSuperResolution)
                    return $"{name}: Fluid Motion Frames and Radeon Super Resolution - switched on for AstroBot in AMD Software.";
                if (hardware.Vendor == "AMD")
                    return $"{name}: AMD Software's frame generation and upscaling need a Radeon RX 6000 or newer; this card gets neither.";
                return $"No Radeon card in use ({name}). These options only apply to AMD cards - the NVIDIA features above are the equivalent here.";
            }
        }

        // Plain-language summary of what the two switches do, and what they do not fix.
        public string AmdNote
        {
            get
            {
                var hardware = _mainViewModel.HardwareInfo;
                if (hardware == null || !hardware.SupportsAmdSuperResolution)
                    return "Driver-level features: on an AMD card, switch them on in AMD Software (Adrenalin) for AstroBot; the launcher puts the game in the state they need.";

                var parts = new List<string>();

                if (AmdFluidMotion)
                {
                    parts.Add("Game started fullscreen with VSync off and no FPS limit, which is what Fluid Motion Frames needs. "
                              + "AMD recommends about 55 FPS at 1080p before it is switched on and this port renders about 30, so "
                              + "expect stutter and extra input lag rather than a smooth 60.");
                }
                if (AmdSuperResolution)
                {
                    var heights = new[] { "720p", "900p", "1080p", "your screen's resolution" };
                    var height = heights[Math.Min(Math.Max(AmdRenderSizeIndex, 0), 3)];
                    parts.Add(AmdRenderSizeIndex >= 3
                        ? "Radeon Super Resolution does nothing at the screen's own resolution: pick a lower one to give it something to upscale."
                        : $"The game renders at {height} and AMD Software upscales it to the screen (Radeon Super Resolution, set to borderless fullscreen for AstroBot).");
                }
                if (AmdFluidMotion && AmdSuperResolution)
                {
                    parts.Add("Note: Fluid Motion Frames wants a fullscreen game and Radeon Super Resolution wants a window, "
                              + "so the game is started windowed and only upscaling is set up for you. Pick one for a clean result.");
                }
                if (parts.Count == 0)
                    parts.Add("Both off. Turn them on for the driver-level smoothing and upscaling AMD offers instead of DLSS and frame generation.");

                return string.Join(" ", parts);
            }
        }

        // Performance Overlay
        public string[] OverlayLabels => new[] { "Off (F2 shows it)", "FPS only", "FPS + CPU, GPU, VRAM, RAM", "Everything (all stats)" };

        public int OverlayIndex
        {
            get => _mainViewModel.Settings.Overlay;
            set
            {
                if (_mainViewModel.Settings.Overlay != value)
                {
                    _mainViewModel.Settings.Overlay = value;
                    OnPropertyChanged();
                    _mainViewModel.OnPropertyChanged(nameof(MainWindowViewModel.Settings));
                }
            }
        }

        // Computed properties for UI state
        public bool IsFrameGenAvailable => _mainViewModel.HardwareInfo?.SupportsFrameGeneration == true && UpscaleIndex != 0;

        public bool IsFrameGenTargetEnabled => FrameGenIndex != 0;

        public bool SupportsDlss => _mainViewModel.HardwareInfo?.SupportsDlss == true;

        public bool SupportsReflex => _mainViewModel.HardwareInfo?.SupportsReflex == true;

        public bool SupportsAmd => _mainViewModel.HardwareInfo?.SupportsAmdSuperResolution == true;

        public string FrameGenNote
        {
            get
            {
                if (FrameGenIndex == 0)
                    return "Frame generation multiplies the frames you see (30 FPS limit x2 = 60 on screen) and turns Reflex on itself. It runs only while the game window is focused. Do not also use NVIDIA Smooth Motion.";

                var targetValues = new[] { 0, 50, 60, 90, 120, 144, 165 };
                int goal = FrameGenTargetIndex >= 0 && FrameGenTargetIndex < targetValues.Length ? targetValues[FrameGenTargetIndex] : 60;
                int mult = FrameGenIndex == 1 ? 2 : FrameGenIndex;

                if (FrameGenIndex == 1 && goal != 0)
                {
                    int limit = Math.Max(30, goal / 2);
                    return $"Game up to {limit} FPS; x2 to x4 picked in game to stay at {goal}+ FPS on screen";
                }
                else if (goal == 0)
                {
                    return $"Game unlocked, x{mult} on screen (e.g. 30 -> {30 * mult})";
                }
                else
                {
                    int limit = Math.Max(30, goal / mult);
                    return $"Game up to {limit} FPS x{mult} = {limit * mult} on screen";
                }
            }
        }

        public string HardwareNote
        {
            get
            {
                if (_mainViewModel.HardwareInfo == null) return "";

                var gpu = _mainViewModel.HardwareInfo.GpuName;
                if (_mainViewModel.HardwareInfo.RtxSeries >= 50)
                    return $"{gpu}: DLSS + Multi Frame Gen (up to 4x) + Reflex available";
                else if (_mainViewModel.HardwareInfo.RtxSeries >= 40)
                    return $"{gpu}: DLSS + Frame Gen (2x) + Reflex available";
                else if (_mainViewModel.HardwareInfo.RtxSeries >= 20)
                    return $"{gpu}: DLSS + Reflex available (Frame Gen needs RTX 40+)";
                else
                    return $"{gpu}: Using game's own upscaling (NVIDIA features need RTX 20+)";
            }
        }
    }
}
