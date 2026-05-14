import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.distribution import (
    apply_distribution_patches,
    distribution_build_env,
    load_distribution_config,
    parse_i18n_revision,
)


class DistributionPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.temp_root, ignore_errors=True)
        self.zed_root = self.temp_root / "zed"
        self._write_fixture()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def _write_fixture(self) -> None:
        files = {
            "crates/zed/src/zed.rs": """
fn open_about_window(cx: &mut App) {
    impl AboutWindow {
        message: SharedString,
        commit: Option<SharedString>,
        full_version: SharedString,

        fn new(cx: &mut Context<Self>) -> Self {
            let release_channel_name = release_channel.display_name();
            let version = env!("CARGO_PKG_VERSION");
            let debug = "";
            let message: SharedString = format!("{release_channel_name} {version} {debug}").into();
            Self {
                message,
                commit,
                full_version,
            }
        }

        fn copy_details(&self, window: &mut Window, cx: &mut Context<Self>) {
            let content = match self.commit.as_ref() {
                Some(commit) => {
                    format!(
                        "{}\\nCommit: {}\\nVersion: {}",
                        self.message, commit, self.full_version
                    )
                }
                None => format!("{}\\nVersion: {}", self.message, self.full_version),
            };
            cx.write_to_clipboard(ClipboardItem::new_string(content));
        }

        fn render(&mut self, window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
            v_flex()
                .child(img(self.app_icon.clone()).size_16().flex_none())
                .child(Headline::new(self.message.clone()))
                .when_some(self.commit.clone(), |this, commit| {
                    this.child(Label::new(commit).size(LabelSize::Small))
                })
                .child(Label::new("Version").color(Color::Muted).size(LabelSize::XSmall))
                .child(Label::new(self.full_version.clone()).size(LabelSize::Small))
        }
    }
}
""",
            "crates/release_channel/src/lib.rs": """
#[cfg(target_os = "windows")]
pub fn app_identifier() -> &'static str {
    match *RELEASE_CHANNEL {
        ReleaseChannel::Stable => "Zed-Editor-Stable",
    }
}

impl ReleaseChannel {
    pub fn app_id(&self) -> &'static str {
        match self {
            ReleaseChannel::Stable => "dev.zed.Zed",
        }
    }
}
""",
            "crates/zed/Cargo.toml": """
[package.metadata.bundle-stable]
identifier = "dev.zed.Zed"
name = "Zed"
osx_url_schemes = ["zed"]
""",
            "crates/windows_resources/src/windows_resources.rs": """
pub fn compile(manifest: bool) -> Result<(), Box<dyn std::error::Error>> {
    let channel = option_env!("RELEASE_CHANNEL").unwrap_or("dev");
    let (icon_filename, product_name) = match channel {
        "stable" => ("app-icon.ico", "Zed"),
        "preview" => ("app-icon-preview.ico", "Zed Preview"),
        "nightly" => ("app-icon-nightly.ico", "Zed Nightly"),
        _ => ("app-icon-dev.ico", "Zed Dev"),
    };
    Ok(())
}
""",
            "script/bundle-linux": """
export APP_NAME="Zed"
APP_ID="dev.zed.Zed"
""",
            "script/bundle-windows.ps1": """
"stable" {
    $appId = "{{2DB0DA96-CA55-49BB-AF4F-64AF36A86712}"
    $appName = "Zed"
    $appDisplayName = "Zed"
    $appSetupName = "Zed-$Architecture"
    $appMutex = "Zed-Stable-Instance-Mutex"
    $appExeName = "Zed"
    $regValueName = "Zed"
    $appUserId = "ZedIndustries.Zed"
    $appShellNameShort = "Z&ed"
    $appAppxFullName = "ZedIndustries.Zed_1.0.0.0_neutral__japxn1gcva8rg"
}
""",
            "crates/explorer_command_injector/AppxManifest.xml": """
<Identity Name="ZedIndustries.Zed" />
<DisplayName>Zed</DisplayName>
<Application Id="Zed" Executable="Zed.exe">
<uap:VisualElements DisplayName="Zed" Description="Zed explorer command injector" />
<desktop5:Verb Id="OpenWithZed" Clsid="6a1f6b13-3b82-48a1-9e06-7bb0a6d0bffd" />
<com:SurrogateServer DisplayName="Zed">
""",
            "crates/zed/resources/windows/zed.iss": """
AppPublisher=Zed Industries
AppPublisherURL=https://www.zed.dev/
AppSupportURL=https://www.zed.dev/
AppUpdatesURL=https://www.zed.dev/
""",
            "crates/auto_update/src/auto_update.rs": """
use serde::{Deserialize, Serialize};
use http_client::{HttpClient, HttpClientWithUrl};

#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ReleaseAsset {
    pub version: String,
    pub url: String,
}

impl AutoUpdater {
    async fn get_release_asset(
        this: &Entity<Self>,
        release_channel: ReleaseChannel,
        version: Option<Version>,
        asset: &str,
        os: &str,
        arch: &str,
        cx: &mut AsyncApp,
    ) -> Result<ReleaseAsset> {
        let client = this.read_with(cx, |this, _| this.client.clone());

        let (system_id, metrics_id, is_staff) = if client.telemetry().metrics_enabled() {
            (None, None, None)
        } else {
            (None, None, None)
        };
    }

    async fn update(this: Entity<Self>, cx: &mut AsyncApp) -> Result<()> {
    }

    fn check_if_fetched_version_is_newer(
        release_channel: ReleaseChannel,
        app_commit_sha: Result<Option<String>>,
        installed_version: Version,
        fetched_version: String,
        status: AutoUpdateStatus,
    ) -> Result<Option<VersionCheckType>> {
        let parsed_fetched_version = fetched_version.parse::<Version>();

        if let AutoUpdateStatus::Updated { version, .. } = status {
        }

        match release_channel {
            _ => Self::check_if_fetched_version_is_newer_non_nightly(
                installed_version,
                parsed_fetched_version?,
            ),
        }
    }

    fn check_if_fetched_version_is_newer_non_nightly(
        mut installed_version: Version,
        fetched_version: Version,
    ) -> Result<Option<VersionCheckType>> {
        installed_version.pre = semver::Prerelease::EMPTY;
        installed_version.build = semver::BuildMetadata::EMPTY;
        let should_download = fetched_version > installed_version;
        let newer_version = should_download.then(|| VersionCheckType::Semantic(fetched_version));
        Ok(newer_version)
    }
}
""",
            "crates/zed/src/zed/app_menus.rs": """
fn app_menus() -> Vec<Menu> {
    vec![Menu {
        name: "Help".into(),
        disabled: false,
        items: vec![
            MenuItem::action(
                "문서",
                super::OpenBrowser {
                    url: "https://zed.dev/docs".into(),
                },
            ),
            MenuItem::action("Zed 저장소", feedback::OpenZedRepo),
            MenuItem::action(
                "Zed Twitter",
                super::OpenBrowser {
                    url: "https://twitter.com/zeddotdev".into(),
                },
            ),
        ],
    }]
}
""",
        }
        for relative, content in files.items():
            path = self.zed_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.lstrip(), encoding="utf-8")

    def write_config(self, text: str) -> Path:
        path = self.temp_root / "distribution.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_loads_distribution_config_with_safe_defaults(self) -> None:
        config = load_distribution_config(self.write_config(""))

        self.assertEqual(config.product_name, "Zed i18n")
        self.assertEqual(config.macos_bundle_id, "dev.zed-i18n.Zed")
        self.assertEqual(config.linux_app_id, "dev.zed-i18n.Zed")
        self.assertEqual(config.windows_app_id, "{{48948123-2766-49EA-9C78-31B8096DE3D6}")
        self.assertTrue(config.update_enabled)

    def test_applies_minimal_identity_about_and_updater_patches(self) -> None:
        config = load_distribution_config(self.write_config(""))

        apply_distribution_patches(self.zed_root, config)

        about = (self.zed_root / "crates/zed/src/zed.rs").read_text(encoding="utf-8")
        release_channel = (self.zed_root / "crates/release_channel/src/lib.rs").read_text(
            encoding="utf-8"
        )
        cargo_toml = (self.zed_root / "crates/zed/Cargo.toml").read_text(encoding="utf-8")
        bundle_windows = (self.zed_root / "script/bundle-windows.ps1").read_text(
            encoding="utf-8"
        )
        windows_resources = (
            self.zed_root / "crates/windows_resources/src/windows_resources.rs"
        ).read_text(encoding="utf-8")
        auto_update = (self.zed_root / "crates/auto_update/src/auto_update.rs").read_text(
            encoding="utf-8"
        )

        self.assertIn("zed-i18n", about)
        self.assertIn("i18n_build: Option<SharedString>", about)
        self.assertIn('SharedString::from(format!("zed-i18n {locale} · {release}"))', about)
        self.assertIn('lines.push(format!("Build: {}", i18n_build));', about)
        self.assertNotIn("i18n_repository", about)
        self.assertNotIn("Repository:", about)
        self.assertNotIn("ZED_I18N_REPOSITORY", about)
        self.assertNotIn("(zed-i18n {locale}", about)
        self.assertIn('ReleaseChannel::Stable => "dev.zed-i18n.Zed"', release_channel)
        self.assertIn('identifier = "dev.zed-i18n.Zed"', cargo_toml)
        self.assertIn('name = "Zed i18n"', cargo_toml)
        self.assertIn('$appId = "{{48948123-2766-49EA-9C78-31B8096DE3D6}"', bundle_windows)
        self.assertNotIn('$appId = "{{48948123-2766-49EA-9C78-31B8096DE3D6}}"', bundle_windows)
        self.assertIn('$appName = "Zed i18n"', bundle_windows)
        self.assertIn('$appExeName = "Zed"', bundle_windows)
        self.assertIn('"stable" => ("app-icon.ico", "Zed i18n")', windows_resources)
        self.assertIn('"preview" => ("app-icon-preview.ico", "Zed Preview")', windows_resources)
        self.assertIn("ZED_I18N_UPDATE_MANIFEST_URL", auto_update)
        self.assertIn("get_i18n_release_asset", auto_update)
        self.assertIn('"zed-remote-server" => return Ok(None)', auto_update)

    def test_adds_i18n_repository_menu_after_localized_zed_repository(self) -> None:
        config = load_distribution_config(
            self.write_config('[publisher]\nurl = "https://github.com/LI-NA/zed-i18n"\n')
        )

        apply_distribution_patches(self.zed_root, config)
        apply_distribution_patches(self.zed_root, config)

        app_menus = (
            self.zed_root / "crates/zed/src/zed/app_menus.rs"
        ).read_text(encoding="utf-8")

        self.assertIn('MenuItem::action("Zed 저장소", feedback::OpenZedRepo),', app_menus)
        self.assertEqual(app_menus.count("Zed-i18n 저장소"), 1)
        self.assertLess(app_menus.index("Zed 저장소"), app_menus.index("Zed-i18n 저장소"))
        self.assertLess(app_menus.index("Zed-i18n 저장소"), app_menus.index("Zed Twitter"))
        self.assertIn('url: "https://github.com/LI-NA/zed-i18n".into()', app_menus)

    def test_distribution_build_env_sets_compile_time_metadata(self) -> None:
        config = load_distribution_config(self.write_config(""))
        env = distribution_build_env(
            config,
            base_env={"ZED_UPDATE_EXPLANATION": "disabled"},
            locale="ko-KR",
            release_tag="v1.2.3-i18n.4",
            repository="owner/repo",
        )

        self.assertNotIn("ZED_UPDATE_EXPLANATION", env)
        self.assertEqual(env["ZED_I18N_LOCALE"], "ko-KR")
        self.assertEqual(env["ZED_I18N_REVISION"], "4")
        self.assertNotIn("ZED_I18N_REPOSITORY", env)
        self.assertEqual(
            env["ZED_I18N_UPDATE_MANIFEST_URL"],
            "https://github.com/owner/repo/releases/latest/download/manifest.json",
        )

    def test_parse_i18n_revision_from_release_tag(self) -> None:
        self.assertEqual(parse_i18n_revision("v1.2.3-i18n.7"), "7")
        self.assertEqual(parse_i18n_revision("nightly"), "0")


if __name__ == "__main__":
    unittest.main()
