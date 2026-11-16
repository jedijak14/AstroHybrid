using System;
using System.IO;
using System.Text;
using System.Text.Json;
using AstroHybrid.App.Models;

namespace AstroHybrid.App.Services
{
    public class SettingsManager
    {
        private readonly string _settingsPath;
        private readonly string _backupPath;
        private readonly string _tempPath;
        private readonly JsonSerializerOptions _jsonOptions;
        private AppSettings? _cachedSettings;

        // Set when Load() had to recover from a damaged settings file, so the app can say so. A silent
        // fall back to defaults looks to the player like the launcher forgot everything, and the next
        // save then writes those defaults over the top of the real file.
        public string? RecoveryNotice { get; private set; }

        public SettingsManager(string rootDirectory, string? settingsPath = null)
        {
            _settingsPath = settingsPath ?? Path.Combine(rootDirectory, "Build", "astrohybrid-settings.json");
            _backupPath = _settingsPath + ".bak";
            _tempPath = _settingsPath + ".tmp";
            _jsonOptions = new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNameCaseInsensitive = true
            };
        }

        public AppSettings Load()
        {
            if (_cachedSettings != null)
                return _cachedSettings;

            // A truncated file parses as nothing, so this is where an interrupted or half-written save
            // would surface: ReadSettings returns null for damaged JSON rather than throwing.
            var settings = ReadSettings(_settingsPath);
            if (settings != null)
            {
                _cachedSettings = settings;
                return settings;
            }

            var hadFile = File.Exists(_settingsPath);

            // The backup is one save behind the live file, which is a great deal better than defaults:
            // the player's install path, GPU choice and controls are in there.
            var recovered = ReadSettings(_backupPath);
            if (recovered != null)
            {
                _cachedSettings = recovered;
                RecoveryNotice = $"The settings file was damaged; the backup (.bak) was used instead. " +
                                 $"File: {_settingsPath}";
                return recovered;
            }

            _cachedSettings = new AppSettings();
            if (hadFile)
            {
                RecoveryNotice = $"The settings file and its backup could not be read; starting from " +
                                 $"defaults. File: {_settingsPath}";
            }
            return _cachedSettings;
        }

        public void Save(AppSettings settings)
        {
            _cachedSettings = settings;
            var directory = Path.GetDirectoryName(_settingsPath);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            var json = JsonSerializer.Serialize(settings, _jsonOptions);

            // Never truncate the live file and write into it: a crash, a full disk or a power cut in
            // that window leaves unparseable JSON, which used to load as all-defaults with no message.
            // Write the new copy beside it, flush it to the disk, then swap it in atomically, keeping
            // the previous version as .bak. File.Replace does the swap in one move and leaves no
            // moment where the settings file does not exist.
            var bytes = new UTF8Encoding(false).GetBytes(json);
            using (var stream = new FileStream(_tempPath, FileMode.Create, FileAccess.Write,
                                               FileShare.None, 4096, FileOptions.WriteThrough))
            {
                stream.Write(bytes, 0, bytes.Length);
                stream.Flush(true);
            }

            if (File.Exists(_settingsPath))
            {
                File.Replace(_tempPath, _settingsPath, _backupPath, true);
            }
            else
            {
                // First save: there is nothing to replace, so the move itself must be the atomic step.
                File.Move(_tempPath, _settingsPath);
            }
        }

        /// <summary>Reads one settings file; null when it is missing, empty or not valid JSON.</summary>
        private AppSettings? ReadSettings(string path)
        {
            try
            {
                if (!File.Exists(path))
                    return null;

                var json = File.ReadAllText(path);
                if (string.IsNullOrEmpty(json))
                    return null;

                var settings = JsonSerializer.Deserialize<AppSettings>(json, _jsonOptions);
                if (settings == null)
                    return null;

                // Older files only have the preset index ("rumble"); make the percent explicit.
                settings.NormalizeRumble();
                return settings;
            }
            catch
            {
                // Damaged JSON is the expected case here, not an exceptional one.
                return null;
            }
        }

        public string GetSettingsPath() => _settingsPath;
    }
}