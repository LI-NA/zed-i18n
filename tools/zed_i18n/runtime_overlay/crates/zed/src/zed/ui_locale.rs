use std::{path::PathBuf, sync::Arc};

use fs::Fs;
use gpui::{App, ReadGlobal as _};
use settings::SettingsStore;

pub fn initialize_localization(fs: Arc<dyn Fs>, cx: &mut App) {
    let user_preference = SettingsStore::global(cx)
        .raw_user_settings()
        .and_then(|user| user.content.ui_locale.as_ref())
        .map(|locale| locale.0.clone());
    let legacy_locale = legacy_marker_path()
        .and_then(|path| std::fs::read_to_string(path).ok())
        .map(|locale| locale.trim().to_owned())
        .filter(|locale| !locale.is_empty());

    let outcome = localization::initialize(localization::InitRequest {
        user_preference: user_preference.as_deref(),
        legacy_locale: legacy_locale.as_deref(),
    });

    if let Some(locale) = outcome.persist_legacy_locale.clone() {
        let completion = SettingsStore::global(cx).update_settings_file_with_completion(
            fs,
            move |settings, _| settings.ui_locale = Some(settings::UiLocale(locale)),
        );
        cx.spawn(async move |_| match completion.await {
            Ok(Ok(())) => log::info!("persisted legacy UI locale"),
            Ok(Err(error)) => log::error!("failed to persist legacy UI locale: {error:#}"),
            Err(error) => log::error!("legacy UI locale persistence was canceled: {error}"),
        })
        .detach();
    }

    #[cfg(debug_assertions)]
    gpui::set_text_observer(observe_untranslated_text);
}

fn legacy_marker_path() -> Option<PathBuf> {
    let executable = std::env::current_exe().ok()?;
    let executable_dir = executable.parent()?;

    #[cfg(target_os = "windows")]
    return Some(executable_dir.join("locales").join("legacy-locale"));

    #[cfg(target_os = "macos")]
    return executable_dir
        .parent()
        .map(|contents| contents.join("Resources").join("locales").join("legacy-locale"));

    #[cfg(target_os = "linux")]
    return executable_dir.parent().map(|prefix| {
        prefix
            .join("share")
            .join("zed-i18n")
            .join("locales")
            .join("legacy-locale")
    });

    #[allow(unreachable_code)]
    None
}

#[cfg(debug_assertions)]
fn observe_untranslated_text(text: &str) {
    use std::{
        collections::HashMap,
        sync::{Mutex, OnceLock},
    };

    if localization::resolved_locale() == "en-US" || localization::lookup(text).is_none() {
        return;
    }

    static COUNTS: OnceLock<Mutex<HashMap<String, usize>>> = OnceLock::new();
    let mut counts = COUNTS
        .get_or_init(|| Mutex::new(HashMap::new()))
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    let count = counts.entry(text.to_owned()).or_default();
    *count += 1;
    if *count == 1 || count.is_power_of_two() {
        log::warn!("untranslated accepted UI text reached GPUI layout ({count}): {text:?}");
    }
}
