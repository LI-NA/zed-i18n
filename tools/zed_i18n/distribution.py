from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tomllib


@dataclass(frozen=True)
class DistributionConfig:
    product_name: str = "Zed i18n"
    product_slug: str = "zed-i18n"
    macos_bundle_id: str = "dev.zed-i18n.Zed"
    linux_app_id: str = "dev.zed-i18n.Zed"
    windows_app_identifier: str = "ZedI18n-Editor-Stable"
    windows_app_id: str = "{{48948123-2766-49EA-9C78-31B8096DE3D6}"
    windows_app_user_id: str = "ZedI18n.Zed"
    windows_appx_name: str = "ZedI18n.Zed"
    windows_appx_full_name: str = "ZedI18n.Zed_1.0.0.0_neutral__japxn1gcva8rg"
    windows_mutex: str = "Zed-i18n-Stable-Instance-Mutex"
    windows_registry_value: str = "ZedI18n"
    windows_setup_name: str = "Zed-i18n"
    windows_shell_name_short: str = "Z&ed i18n"
    publisher_name: str = "zed-i18n"
    publisher_url: str = ""
    update_enabled: bool = True
    update_manifest_url: str = ""


def load_distribution_config(path: Path | str | None) -> DistributionConfig:
    if path is None:
        return DistributionConfig()
    config_path = Path(path)
    data = tomllib.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    identity = data.get("identity", {})
    windows = data.get("windows", {})
    update = data.get("update", {})
    publisher = data.get("publisher", {})

    return DistributionConfig(
        product_name=data.get("product_name", DistributionConfig.product_name),
        product_slug=data.get("product_slug", DistributionConfig.product_slug),
        macos_bundle_id=identity.get("macos_bundle_id", DistributionConfig.macos_bundle_id),
        linux_app_id=identity.get("linux_app_id", DistributionConfig.linux_app_id),
        windows_app_identifier=windows.get(
            "app_identifier", DistributionConfig.windows_app_identifier
        ),
        windows_app_id=windows.get("app_id", DistributionConfig.windows_app_id),
        windows_app_user_id=windows.get("app_user_id", DistributionConfig.windows_app_user_id),
        windows_appx_name=windows.get("appx_name", DistributionConfig.windows_appx_name),
        windows_appx_full_name=windows.get(
            "appx_full_name", DistributionConfig.windows_appx_full_name
        ),
        windows_mutex=windows.get("mutex", DistributionConfig.windows_mutex),
        windows_registry_value=windows.get(
            "registry_value", DistributionConfig.windows_registry_value
        ),
        windows_setup_name=windows.get("setup_name", DistributionConfig.windows_setup_name),
        windows_shell_name_short=windows.get(
            "shell_name_short", DistributionConfig.windows_shell_name_short
        ),
        publisher_name=publisher.get("name", DistributionConfig.publisher_name),
        publisher_url=publisher.get("url", DistributionConfig.publisher_url),
        update_enabled=bool(update.get("enabled", DistributionConfig.update_enabled)),
        update_manifest_url=update.get(
            "manifest_url", DistributionConfig.update_manifest_url
        ),
    )


def parse_i18n_revision(release_tag: str | None) -> str:
    if not release_tag:
        return "0"
    match = re.search(r"-i18n\.(\d+)$", release_tag)
    return match.group(1) if match else "0"


def distribution_build_env(
    config: DistributionConfig,
    base_env: dict[str, str] | None,
    locale: str,
    release_tag: str | None,
    repository: str | None,
) -> dict[str, str]:
    env = dict(base_env or os.environ)
    env["ZED_I18N_LOCALE"] = locale
    env["ZED_I18N_RELEASE_TAG"] = release_tag or "local"
    env["ZED_I18N_REVISION"] = parse_i18n_revision(release_tag)
    manifest_url = resolve_update_manifest_url(config, repository)
    if config.update_enabled and manifest_url:
        env["ZED_I18N_UPDATE_MANIFEST_URL"] = manifest_url
        env.pop("ZED_UPDATE_EXPLANATION", None)
    env.pop("ZED_I18N_REPOSITORY", None)
    return env


def resolve_update_manifest_url(config: DistributionConfig, repository: str | None) -> str:
    if config.update_manifest_url:
        return config.update_manifest_url.format(repository=repository or "")
    if repository:
        return f"https://github.com/{repository}/releases/latest/download/manifest.json"
    return ""


def apply_distribution_patches(zed_root: Path, config: DistributionConfig) -> None:
    patch_about_window(zed_root, config)
    patch_release_channel(zed_root, config)
    patch_macos_bundle_metadata(zed_root, config)
    patch_linux_bundle_metadata(zed_root, config)
    patch_windows_bundle_metadata(zed_root, config)
    patch_windows_resources(zed_root, config)
    patch_help_menu_i18n_repository_link(zed_root, config)
    if config.update_enabled:
        patch_auto_update(zed_root)


def patch_about_window(zed_root: Path, config: DistributionConfig) -> None:
    path = zed_root / "crates" / "zed" / "src" / "zed.rs"
    text = _read(path)
    if "i18n_build: Option<SharedString>" in text:
        return
    message_replacement = f"""            let message: SharedString = format!("{{release_channel_name}} {{version}} {{debug}}").into();
            let i18n_build = option_env!("ZED_I18N_LOCALE").map(|locale| {{
                let release = option_env!("ZED_I18N_RELEASE_TAG").unwrap_or("local");
                SharedString::from(format!("{config.product_slug} {{locale}} · {{release}}"))
            }});"""
    replacements = [
        (
            "        message: SharedString,\n        commit: Option<SharedString>,\n        full_version: SharedString,\n",
            "        message: SharedString,\n        i18n_build: Option<SharedString>,\n        commit: Option<SharedString>,\n        full_version: SharedString,\n",
        ),
        (
            '            let message: SharedString = format!("{release_channel_name} {version} {debug}").into();',
            message_replacement,
        ),
        (
            "                message,\n                commit,\n                full_version,\n",
            "                message,\n                i18n_build,\n                commit,\n                full_version,\n",
        ),
        (
            """            let content = match self.commit.as_ref() {
                Some(commit) => {
                    format!(
                        "{}\\nCommit: {}\\nVersion: {}",
                        self.message, commit, self.full_version
                    )
                }
                None => format!("{}\\nVersion: {}", self.message, self.full_version),
            };""",
            """            let mut lines = vec![format!("{}", self.message)];
            if let Some(i18n_build) = self.i18n_build.as_ref() {
                lines.push(format!("Build: {}", i18n_build));
            }
            if let Some(commit) = self.commit.as_ref() {
                lines.push(format!("Commit: {}", commit));
            }
            lines.push(format!("Version: {}", self.full_version));
            let content = lines.join("\\n");""",
        ),
    ]
    text = _replace_many(text, replacements, path)
    text = _replace_headline_build_label(text, path)
    _write(path, text)


def patch_release_channel(zed_root: Path, config: DistributionConfig) -> None:
    path = zed_root / "crates" / "release_channel" / "src" / "lib.rs"
    text = _read(path)
    replacements = [
        ('ReleaseChannel::Stable => "Zed-Editor-Stable"', f'ReleaseChannel::Stable => "{config.windows_app_identifier}"'),
        ('ReleaseChannel::Stable => "dev.zed.Zed"', f'ReleaseChannel::Stable => "{config.macos_bundle_id}"'),
    ]
    _write(path, _replace_many(text, replacements, path))


def patch_macos_bundle_metadata(zed_root: Path, config: DistributionConfig) -> None:
    path = zed_root / "crates" / "zed" / "Cargo.toml"
    text = _read(path)
    replacements = [
        ('identifier = "dev.zed.Zed"', f'identifier = "{config.macos_bundle_id}"'),
        ('name = "Zed"', f'name = "{config.product_name}"'),
    ]
    _write(path, _replace_many(text, replacements, path))


def patch_linux_bundle_metadata(zed_root: Path, config: DistributionConfig) -> None:
    path = zed_root / "script" / "bundle-linux"
    text = _read(path)
    replacements = [
        ('export APP_NAME="Zed"', f'export APP_NAME="{config.product_name}"'),
        ('APP_ID="dev.zed.Zed"', f'APP_ID="{config.linux_app_id}"'),
    ]
    _write(path, _replace_many(text, replacements, path))


def patch_windows_bundle_metadata(zed_root: Path, config: DistributionConfig) -> None:
    path = zed_root / "script" / "bundle-windows.ps1"
    text = _read(path)
    first_replacements = [
        ('$appId = "{{2DB0DA96-CA55-49BB-AF4F-64AF36A86712}"', f'$appId = "{config.windows_app_id}"'),
        ('$appName = "Zed"', f'$appName = "{config.product_name}"'),
        ('$appDisplayName = "Zed"', f'$appDisplayName = "{config.product_name}"'),
        ('$appSetupName = "Zed-$Architecture"', f'$appSetupName = "{config.windows_setup_name}-$Architecture"'),
        ('$appMutex = "Zed-Stable-Instance-Mutex"', f'$appMutex = "{config.windows_mutex}"'),
        ('$regValueName = "Zed"', f'$regValueName = "{config.windows_registry_value}"'),
        ('$appUserId = "ZedIndustries.Zed"', f'$appUserId = "{config.windows_app_user_id}"'),
        ('$appShellNameShort = "Z&ed"', f'$appShellNameShort = "{config.windows_shell_name_short}"'),
        (
            '$appAppxFullName = "ZedIndustries.Zed_1.0.0.0_neutral__japxn1gcva8rg"',
            f'$appAppxFullName = "{config.windows_appx_full_name}"',
        ),
    ]
    for old, new in first_replacements:
        text = _replace_first_required(text, old, new, path)
    _write(path, text)


def patch_windows_resources(zed_root: Path, config: DistributionConfig) -> None:
    build_rs = zed_root / "crates" / "zed" / "build.rs"
    text = _read(build_rs)
    replacements = [
        ('res.set("FileDescription", "Zed")', f'res.set("FileDescription", "{config.product_name}")'),
        ('res.set("ProductName", "Zed")', f'res.set("ProductName", "{config.product_name}")'),
    ]
    _write(build_rs, _replace_many(text, replacements, build_rs))

    appx = zed_root / "crates" / "explorer_command_injector" / "AppxManifest.xml"
    text = _read(appx)
    replacements = [
        ('Name="ZedIndustries.Zed"', f'Name="{config.windows_appx_name}"'),
        ("<DisplayName>Zed</DisplayName>", f"<DisplayName>{config.product_name}</DisplayName>"),
        ('DisplayName="Zed"', f'DisplayName="{config.product_name}"'),
        (
            'Description="Zed explorer command injector"',
            f'Description="{config.product_name} explorer command injector"',
        ),
        ('Id="OpenWithZed"', 'Id="OpenWithZedI18n"'),
        ('<com:SurrogateServer DisplayName="Zed">', f'<com:SurrogateServer DisplayName="{config.product_name}">'),
    ]
    _write(appx, _replace_many(text, replacements, appx))

    installer = zed_root / "crates" / "zed" / "resources" / "windows" / "zed.iss"
    text = _read(installer)
    replacements = [('AppPublisher=Zed Industries', f"AppPublisher={config.publisher_name}")]
    if config.publisher_url:
        replacements.extend(
            [
                ("AppPublisherURL=https://www.zed.dev/", f"AppPublisherURL={config.publisher_url}"),
                ("AppSupportURL=https://www.zed.dev/", f"AppSupportURL={config.publisher_url}"),
                ("AppUpdatesURL=https://www.zed.dev/", f"AppUpdatesURL={config.publisher_url}"),
            ]
        )
    _write(installer, _replace_many(text, replacements, installer))


def patch_help_menu_i18n_repository_link(zed_root: Path, config: DistributionConfig) -> None:
    if not config.publisher_url:
        return

    path = zed_root / "crates" / "zed" / "src" / "zed" / "app_menus.rs"
    text = _read(path)
    if config.publisher_url in text:
        return

    pattern = re.compile(
        r'(?m)^(\s*)MenuItem::action\("((?:\\.|[^"\\])*)",\s*feedback::OpenZedRepo\),'
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one Zed repository menu item in {path}, found {len(matches)}"
        )

    match = matches[0]
    indent = match.group(1)
    zed_label = match.group(2)
    i18n_brand = config.product_slug[:1].upper() + config.product_slug[1:]
    if "Zed" not in zed_label:
        raise ValueError(f"expected Zed repository label to contain 'Zed' in {path}")
    i18n_label = zed_label.replace("Zed", i18n_brand, 1)
    insertion = (
        f'{match.group(0)}\n'
        f'{indent}MenuItem::action(\n'
        f'{indent}    {_rust_string_literal(i18n_label)},\n'
        f'{indent}    super::OpenBrowser {{\n'
        f'{indent}        url: {_rust_string_literal(config.publisher_url)}.into(),\n'
        f'{indent}    }},\n'
        f'{indent}),'
    )
    text = text[: match.start()] + insertion + text[match.end() :]
    _write(path, text)


def patch_auto_update(zed_root: Path) -> None:
    path = zed_root / "crates" / "auto_update" / "src" / "auto_update.rs"
    text = _read(path)
    if "struct I18nReleaseManifest" not in text:
        text = _replace_required(
            text,
            """#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ReleaseAsset {
    pub version: String,
    pub url: String,
}
""",
            """#[derive(Deserialize, Serialize, Clone, Debug)]
pub struct ReleaseAsset {
    pub version: String,
    pub url: String,
}

#[derive(Deserialize, Clone, Debug)]
struct I18nReleaseManifest {
    zed_version: String,
    #[serde(default)]
    i18n_revision: u64,
    assets: Vec<I18nReleaseAsset>,
}

#[derive(Deserialize, Clone, Debug)]
struct I18nReleaseAsset {
    kind: String,
    #[serde(default)]
    locale: Option<String>,
    platform: String,
    arch: String,
    #[serde(default)]
    download_url: Option<String>,
    #[serde(default)]
    url: Option<String>,
}
""",
            path,
        )

    dispatch = """        if let Some(manifest_url) = option_env!("ZED_I18N_UPDATE_MANIFEST_URL") {
            let http_client = client.http_client();
            if let Some(release) =
                Self::get_i18n_release_asset(manifest_url, asset, os, arch, http_client).await?
            {
                return Ok(release);
            }
        }

"""
    if "Self::get_i18n_release_asset(manifest_url" not in text:
        text = _replace_required(
            text,
            "        let client = this.read_with(cx, |this, _| this.client.clone());\n\n",
            "        let client = this.read_with(cx, |this, _| this.client.clone());\n\n" + dispatch,
            path,
        )

    if "async fn get_i18n_release_asset(" not in text:
        text = _replace_required(
            text,
            "    async fn update(this: Entity<Self>, cx: &mut AsyncApp) -> Result<()> {\n",
            I18N_RELEASE_ASSET_FUNCTION + "\n    async fn update(this: Entity<Self>, cx: &mut AsyncApp) -> Result<()> {\n",
            path,
        )
    else:
        text = text.replace(
            '            "zed-remote-server" => "remote-server",',
            '            "zed-remote-server" => return Ok(None),',
        )

    if "check_if_i18n_fetched_version_is_newer" not in text:
        text = _replace_required(
            text,
            "        let parsed_fetched_version = fetched_version.parse::<Version>();\n\n",
            """        let parsed_fetched_version = fetched_version.parse::<Version>();

        if option_env!("ZED_I18N_UPDATE_MANIFEST_URL").is_some() {
            return Self::check_if_i18n_fetched_version_is_newer(
                installed_version,
                parsed_fetched_version?,
            );
        }

""",
            path,
        )
        text = _replace_required(
            text,
            "    fn check_if_fetched_version_is_newer_non_nightly(\n",
            I18N_VERSION_CHECK_FUNCTION + "\n    fn check_if_fetched_version_is_newer_non_nightly(\n",
            path,
        )

    _write(path, text)


I18N_RELEASE_ASSET_FUNCTION = """    async fn get_i18n_release_asset(
        manifest_url: &str,
        asset: &str,
        os: &str,
        arch: &str,
        http_client: Arc<dyn HttpClient>,
    ) -> Result<Option<ReleaseAsset>> {
        let kind = match asset {
            "zed" => "app",
            "zed-remote-server" => return Ok(None),
            _ => return Ok(None),
        };
        let locale = option_env!("ZED_I18N_LOCALE");

        let mut response = http_client
            .get(manifest_url, Default::default(), true)
            .await?;
        let mut body = Vec::new();
        response.body_mut().read_to_end(&mut body).await?;

        anyhow::ensure!(
            response.status().is_success(),
            "failed to fetch zed-i18n manifest: {:?}",
            String::from_utf8_lossy(&body),
        );

        let manifest: I18nReleaseManifest = serde_json::from_slice(body.as_slice())
            .with_context(|| "error deserializing zed-i18n release manifest")?;
        let matched_asset = manifest
            .assets
            .iter()
            .find(|candidate| {
                candidate.kind == kind
                    && candidate.platform == os
                    && candidate.arch == arch
                    && (kind != "app" || candidate.locale.as_deref() == locale)
            })
            .with_context(|| {
                format!(
                    "no zed-i18n release asset for kind={kind}, locale={:?}, os={os}, arch={arch}",
                    locale
                )
            })?;
        let url = matched_asset
            .download_url
            .as_ref()
            .or(matched_asset.url.as_ref())
            .context("zed-i18n release asset has no download_url")?;
        let version = format!(
            "{}+i18n.{}",
            manifest.zed_version.trim_start_matches('v'),
            manifest.i18n_revision
        );

        Ok(Some(ReleaseAsset {
            version,
            url: url.clone(),
        }))
    }
"""


I18N_VERSION_CHECK_FUNCTION = """    fn check_if_i18n_fetched_version_is_newer(
        mut installed_version: Version,
        fetched_version: Version,
    ) -> Result<Option<VersionCheckType>> {
        let fetched_revision = fetched_version
            .build
            .as_str()
            .strip_prefix("i18n.")
            .and_then(|revision| revision.parse::<u64>().ok())
            .unwrap_or_default();
        let installed_revision = option_env!("ZED_I18N_REVISION")
            .and_then(|revision| revision.parse::<u64>().ok())
            .unwrap_or_default();

        let mut fetched_base_version = fetched_version.clone();
        fetched_base_version.pre = semver::Prerelease::EMPTY;
        fetched_base_version.build = semver::BuildMetadata::EMPTY;
        installed_version.pre = semver::Prerelease::EMPTY;
        installed_version.build = semver::BuildMetadata::EMPTY;

        let should_download = fetched_base_version > installed_version
            || (fetched_base_version == installed_version && fetched_revision > installed_revision);
        let newer_version = should_download.then(|| VersionCheckType::Semantic(fetched_version));
        Ok(newer_version)
    }
"""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _rust_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _replace_many(text: str, replacements: list[tuple[str, str]], path: Path) -> str:
    for old, new in replacements:
        text = _replace_required(text, old, new, path)
    return text


def _replace_required(text: str, old: str, new: str, path: Path) -> str:
    if new in text:
        return text
    if old not in text:
        raise ValueError(f"expected patch target not found in {path}: {old[:80]!r}")
    return text.replace(old, new)


def _replace_first_required(text: str, old: str, new: str, path: Path) -> str:
    if new in text:
        return text
    if old not in text:
        raise ValueError(f"expected patch target not found in {path}: {old[:80]!r}")
    return text.replace(old, new, 1)


def _replace_headline_build_label(text: str, path: Path) -> str:
    if "self.i18n_build.clone()" in text:
        return text
    pattern = r"(?m)^(\s*)\.child\(Headline::new\(self\.message\.clone\(\)\)\)"

    def replacement(match: re.Match[str]) -> str:
        indent = match.group(1)
        child_indent = indent + "    "
        return (
            f"{indent}.child(Headline::new(self.message.clone()))\n"
            f"{indent}.when_some(self.i18n_build.clone(), |this, i18n_build| {{\n"
            f"{child_indent}this.child(\n"
            f"{child_indent}    Label::new(i18n_build)\n"
            f"{child_indent}        .color(Color::Muted)\n"
            f"{child_indent}        .size(LabelSize::Small),\n"
            f"{child_indent})\n"
            f"{indent}}})"
        )

    patched, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise ValueError(f"expected About headline target not found in {path}")
    return patched
