use std::{
    borrow::Cow,
    collections::HashMap,
    sync::OnceLock,
};

use rust_embed::RustEmbed;
use serde::Deserialize;

const SOURCE_LOCALE: &str = "en-US";

#[derive(RustEmbed)]
#[folder = "../../assets/locales"]
#[include = "*.json"]
struct LocaleAssets;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LocaleSource {
    User,
    LegacyMarker,
    System,
    EnglishFallback,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FallbackReason {
    UnsupportedPreference,
    InvalidLegacyMarker,
    NoSupportedSystemLocale,
    CorruptIndex,
    CorruptBundle,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
pub struct LocaleMetadata {
    pub id: String,
    pub english_name: String,
    pub native_name: String,
    #[serde(default)]
    pub aliases: Vec<String>,
    pub direction: String,
    pub bundle: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LocaleResolution {
    pub resolved_locale: String,
    pub source: LocaleSource,
    pub fallback_reason: Option<FallbackReason>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InitOutcome {
    pub resolved_locale: String,
    pub system_locale: Option<String>,
    pub source: LocaleSource,
    pub persist_legacy_locale: Option<String>,
    pub fallback_reason: Option<FallbackReason>,
}

#[derive(Clone, Copy)]
pub struct InitRequest<'a> {
    pub user_preference: Option<&'a str>,
    pub legacy_locale: Option<&'a str>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(untagged)]
enum FormatSegment {
    Text { text: String },
    Arg { arg: String },
}

#[derive(Debug, Deserialize)]
struct LocaleIndex {
    schema_version: u32,
    source_locale: String,
    catalog_sha256: String,
    locales: Vec<LocaleMetadata>,
    #[serde(default)]
    source_formats: HashMap<String, Vec<FormatSegment>>,
}

#[derive(Debug, Deserialize)]
struct LocaleBundle {
    schema_version: u32,
    locale: String,
    catalog_sha256: String,
    #[serde(default)]
    messages: HashMap<String, String>,
    #[serde(default)]
    formats: HashMap<String, Vec<FormatSegment>>,
}

struct Registry {
    outcome: InitOutcome,
    locales: Box<[LocaleMetadata]>,
    messages: HashMap<Box<str>, Box<str>>,
    formats: HashMap<Box<str>, Box<[FormatSegment]>>,
    source_formats: HashMap<Box<str>, Box<[FormatSegment]>>,
}

static REGISTRY: OnceLock<Registry> = OnceLock::new();

impl Registry {
    #[cfg(test)]
    fn build(
        index_json: &str,
        bundle_json: Option<&str>,
        request: InitRequest<'_>,
        system_locales: &[String],
    ) -> Self {
        let Ok(index) = serde_json::from_str::<LocaleIndex>(index_json) else {
            return Self::english(
                Vec::new(),
                HashMap::new(),
                None,
                LocaleSource::EnglishFallback,
                Some(FallbackReason::CorruptIndex),
            );
        };
        Self::from_index(index, bundle_json, request, system_locales)
    }

    fn from_index(
        index: LocaleIndex,
        bundle_json: Option<&str>,
        request: InitRequest<'_>,
        system_locales: &[String],
    ) -> Self {
        if index.schema_version != 1 || index.source_locale != SOURCE_LOCALE {
            return Self::english(
                index.locales,
                index.source_formats,
                None,
                LocaleSource::EnglishFallback,
                Some(FallbackReason::CorruptIndex),
            );
        }

        let (resolution, system_locale, persist_legacy_locale) = resolve_locale(
            request.user_preference,
            request.legacy_locale,
            system_locales,
            &index.locales,
        );
        if resolution.resolved_locale == SOURCE_LOCALE {
            let mut registry = Self::english(
                index.locales,
                index.source_formats,
                system_locale,
                resolution.source,
                resolution.fallback_reason,
            );
            registry.outcome.persist_legacy_locale = persist_legacy_locale;
            return registry;
        }

        let Some(bundle_json) = bundle_json else {
            return Self::english(
                index.locales,
                index.source_formats,
                system_locale,
                LocaleSource::EnglishFallback,
                Some(FallbackReason::CorruptBundle),
            );
        };
        let Ok(bundle) = serde_json::from_str::<LocaleBundle>(bundle_json) else {
            return Self::english(
                index.locales,
                index.source_formats,
                system_locale,
                LocaleSource::EnglishFallback,
                Some(FallbackReason::CorruptBundle),
            );
        };
        if bundle.schema_version != 1
            || bundle.locale != resolution.resolved_locale
            || bundle.catalog_sha256 != index.catalog_sha256
        {
            return Self::english(
                index.locales,
                index.source_formats,
                system_locale,
                LocaleSource::EnglishFallback,
                Some(FallbackReason::CorruptBundle),
            );
        }

        Self {
            outcome: InitOutcome {
                resolved_locale: resolution.resolved_locale,
                system_locale,
                source: resolution.source,
                persist_legacy_locale,
                fallback_reason: resolution.fallback_reason,
            },
            locales: index.locales.into_boxed_slice(),
            messages: bundle
                .messages
                .into_iter()
                .map(|(key, value)| (key.into_boxed_str(), value.into_boxed_str()))
                .collect(),
            formats: bundle
                .formats
                .into_iter()
                .map(|(key, value)| (key.into_boxed_str(), value.into_boxed_slice()))
                .collect(),
            source_formats: index
                .source_formats
                .into_iter()
                .map(|(key, value)| (key.into_boxed_str(), value.into_boxed_slice()))
                .collect(),
        }
    }

    fn english(
        locales: Vec<LocaleMetadata>,
        source_formats: HashMap<String, Vec<FormatSegment>>,
        system_locale: Option<String>,
        source: LocaleSource,
        fallback_reason: Option<FallbackReason>,
    ) -> Self {
        Self {
            outcome: InitOutcome {
                resolved_locale: SOURCE_LOCALE.into(),
                system_locale,
                source,
                persist_legacy_locale: None,
                fallback_reason,
            },
            locales: locales.into_boxed_slice(),
            messages: HashMap::new(),
            formats: HashMap::new(),
            source_formats: source_formats
                .into_iter()
                .map(|(key, value)| (key.into_boxed_str(), value.into_boxed_slice()))
                .collect(),
        }
    }

    fn translate_static<'a>(&'a self, source: &'static str) -> &'a str {
        self.messages
            .get(source)
            .map(|translation| translation.as_ref())
            .unwrap_or(source)
    }

    fn lookup(&self, source: &str) -> Option<&str> {
        self.messages
            .get(source)
            .map(|translation| translation.as_ref())
    }

    fn format_message(&self, source: &'static str, args: &[(&'static str, String)]) -> String {
        if let Some(segments) = self.formats.get(source) {
            if let Some(rendered) = render_segments(segments, args) {
                return rendered;
            }
            return source.to_owned();
        }
        if let Some(segments) = self.source_formats.get(source) {
            return render_segments(segments, args).unwrap_or_else(|| source.to_owned());
        }
        source.to_owned()
    }
}

pub fn initialize(request: InitRequest<'_>) -> &'static InitOutcome {
    let registry = REGISTRY.get_or_init(|| {
        let system_locales = sys_locale::get_locales().collect::<Vec<_>>();
        let Some(index_json) = embedded_text("index.json") else {
            return Registry::english(
                Vec::new(),
                HashMap::new(),
                None,
                LocaleSource::EnglishFallback,
                Some(FallbackReason::CorruptIndex),
            );
        };
        let Ok(index) = serde_json::from_str::<LocaleIndex>(&index_json) else {
            return Registry::english(
                Vec::new(),
                HashMap::new(),
                None,
                LocaleSource::EnglishFallback,
                Some(FallbackReason::CorruptIndex),
            );
        };
        let requested_bundle = {
            let (resolution, _, _) = resolve_locale(
                request.user_preference,
                request.legacy_locale,
                &system_locales,
                &index.locales,
            );
            index
                .locales
                .iter()
                .find(|locale| locale.id == resolution.resolved_locale)
                .and_then(|locale| locale.bundle.as_deref())
                .and_then(embedded_text)
        };
        Registry::from_index(
            index,
            requested_bundle.as_deref(),
            request,
            &system_locales,
        )
    });
    log::info!(
        "localization initialized: requested={:?}, system={:?}, resolved={}, source={:?}, fallback={:?}",
        request.user_preference,
        registry.outcome.system_locale,
        registry.outcome.resolved_locale,
        registry.outcome.source,
        registry.outcome.fallback_reason,
    );
    &registry.outcome
}

pub fn is_initialized() -> bool {
    REGISTRY.get().is_some()
}

pub fn translate_static(source: &'static str) -> &'static str {
    REGISTRY
        .get()
        .map(|registry| registry.translate_static(source))
        .unwrap_or(source)
}

pub fn lookup(source: &str) -> Option<&'static str> {
    REGISTRY.get().and_then(|registry| registry.lookup(source))
}

pub fn format_message(source: &'static str, args: &[(&'static str, String)]) -> String {
    REGISTRY
        .get()
        .map(|registry| registry.format_message(source, args))
        .unwrap_or_else(|| render_source_without_registry(source, args))
}

pub fn available_locales() -> &'static [LocaleMetadata] {
    REGISTRY
        .get()
        .map(|registry| registry.locales.as_ref())
        .unwrap_or(&[])
}

pub fn resolved_locale() -> &'static str {
    REGISTRY
        .get()
        .map(|registry| registry.outcome.resolved_locale.as_str())
        .unwrap_or(SOURCE_LOCALE)
}

pub fn system_locale() -> Option<&'static str> {
    REGISTRY
        .get()
        .and_then(|registry| registry.outcome.system_locale.as_deref())
}

pub fn preview_resolution(preference: &str) -> LocaleResolution {
    let Some(registry) = REGISTRY.get() else {
        return LocaleResolution {
            resolved_locale: SOURCE_LOCALE.into(),
            source: LocaleSource::EnglishFallback,
            fallback_reason: Some(FallbackReason::CorruptIndex),
        };
    };
    resolve_locale(Some(preference), None, &[], &registry.locales).0
}

fn resolve_locale(
    user_preference: Option<&str>,
    legacy_locale: Option<&str>,
    system_locales: &[String],
    locales: &[LocaleMetadata],
) -> (LocaleResolution, Option<String>, Option<String>) {
    if let Some(preference) = user_preference {
        if !preference.eq_ignore_ascii_case("system") {
            if let Some(locale) = match_locale(preference, locales) {
                return (
                    LocaleResolution {
                        resolved_locale: locale.id.clone(),
                        source: LocaleSource::User,
                        fallback_reason: None,
                    },
                    resolve_system_locale(system_locales, locales),
                    None,
                );
            }
            return (
                LocaleResolution {
                    resolved_locale: SOURCE_LOCALE.into(),
                    source: LocaleSource::EnglishFallback,
                    fallback_reason: Some(FallbackReason::UnsupportedPreference),
                },
                resolve_system_locale(system_locales, locales),
                None,
            );
        }
    } else if let Some(marker) = legacy_locale {
        if let Some(locale) = match_locale(marker, locales) {
            return (
                LocaleResolution {
                    resolved_locale: locale.id.clone(),
                    source: LocaleSource::LegacyMarker,
                    fallback_reason: None,
                },
                resolve_system_locale(system_locales, locales),
                Some(locale.id.clone()),
            );
        }
    }

    if let Some(system_locale) = resolve_system_locale(system_locales, locales) {
        return (
            LocaleResolution {
                resolved_locale: system_locale.clone(),
                source: LocaleSource::System,
                fallback_reason: None,
            },
            Some(system_locale),
            None,
        );
    }
    (
        LocaleResolution {
            resolved_locale: SOURCE_LOCALE.into(),
            source: LocaleSource::EnglishFallback,
            fallback_reason: Some(if legacy_locale.is_some() && user_preference.is_none() {
                FallbackReason::InvalidLegacyMarker
            } else {
                FallbackReason::NoSupportedSystemLocale
            }),
        },
        None,
        None,
    )
}

fn normalize_locale_tag(locale: &str) -> String {
    let without_modifier = locale.split('@').next().unwrap_or(locale);
    let without_codeset = without_modifier
        .split('.')
        .next()
        .unwrap_or(without_modifier);
    let mut parts = without_codeset
        .replace('_', "-")
        .split('-')
        .filter(|part| !part.is_empty())
        .map(str::to_owned)
        .collect::<Vec<_>>();
    for (index, part) in parts.iter_mut().enumerate() {
        if index == 0 {
            *part = part.to_lowercase();
        } else if part.len() == 4 && part.chars().all(|char| char.is_ascii_alphabetic()) {
            let mut chars = part.chars();
            let first = chars.next().unwrap().to_ascii_uppercase();
            *part = first.to_string() + &chars.as_str().to_ascii_lowercase();
        } else if (part.len() == 2 && part.chars().all(|char| char.is_ascii_alphabetic()))
            || (part.len() == 3 && part.chars().all(|char| char.is_ascii_digit()))
        {
            *part = part.to_ascii_uppercase();
        }
    }
    parts.join("-")
}

fn render_segments(
    segments: &[FormatSegment],
    args: &[(&'static str, String)],
) -> Option<String> {
    let mut output = String::new();
    for segment in segments {
        match segment {
            FormatSegment::Text { text } => output.push_str(text),
            FormatSegment::Arg { arg } => {
                let (_, value) = args.iter().find(|(name, _)| *name == arg.as_str())?;
                output.push_str(value);
            }
        }
    }
    Some(output)
}

fn render_source_without_registry(
    source: &'static str,
    args: &[(&'static str, String)],
) -> String {
    let Ok(segments) = parse_source_format(source) else {
        return source.to_owned();
    };
    render_segments(&segments, args).unwrap_or_else(|| source.to_owned())
}

fn parse_source_format(source: &str) -> Result<Vec<FormatSegment>, ()> {
    let mut segments = Vec::new();
    let mut text = String::new();
    let mut implicit_index = 0;
    let chars = source.as_bytes();
    let mut index = 0;
    while index < chars.len() {
        if chars[index] == b'{' && chars.get(index + 1) == Some(&b'{') {
            text.push('{');
            index += 2;
        } else if chars[index] == b'}' && chars.get(index + 1) == Some(&b'}') {
            text.push('}');
            index += 2;
        } else if chars[index] == b'}' {
            return Err(());
        } else if chars[index] != b'{' {
            let character = source[index..].chars().next().ok_or(())?;
            text.push(character);
            index += character.len_utf8();
        } else {
            let remainder = &source[index + 1..];
            let relative_end = remainder.find('}').ok_or(())?;
            let inner = &remainder[..relative_end];
            if inner.contains('{') {
                return Err(());
            }
            if !text.is_empty() {
                segments.push(FormatSegment::Text {
                    text: std::mem::take(&mut text),
                });
            }
            let key = inner.split(':').next().ok_or(())?;
            let key = if key.is_empty() {
                let value = implicit_index.to_string();
                implicit_index += 1;
                value
            } else {
                key.to_owned()
            };
            segments.push(FormatSegment::Arg { arg: key });
            index += relative_end + 2;
        }
    }
    if !text.is_empty() {
        segments.push(FormatSegment::Text { text });
    }
    Ok(segments)
}

fn resolve_system_locale(
    system_locales: &[String],
    locales: &[LocaleMetadata],
) -> Option<String> {
    system_locales
        .iter()
        .find_map(|candidate| match_locale(candidate, locales).map(|locale| locale.id.clone()))
}

fn match_locale<'a>(
    candidate: &str,
    locales: &'a [LocaleMetadata],
) -> Option<&'a LocaleMetadata> {
    let normalized = normalize_locale_tag(candidate);
    if let Some(locale) = locales.iter().find(|locale| {
        normalize_locale_tag(&locale.id).eq_ignore_ascii_case(&normalized)
            || locale
                .aliases
                .iter()
                .any(|alias| normalize_locale_tag(alias).eq_ignore_ascii_case(&normalized))
    }) {
        return Some(locale);
    }
    let language = normalized.split('-').next()?;
    let mut matching = locales.iter().filter(|locale| {
        normalize_locale_tag(&locale.id)
            .split('-')
            .next()
            .is_some_and(|locale_language| locale_language.eq_ignore_ascii_case(language))
    });
    let first = matching.next()?;
    matching.next().is_none().then_some(first)
}

fn embedded_text(path: &str) -> Option<Cow<'static, str>> {
    let asset = LocaleAssets::get(path)?;
    match asset.data {
        Cow::Borrowed(bytes) => std::str::from_utf8(bytes).ok().map(Cow::Borrowed),
        Cow::Owned(bytes) => String::from_utf8(bytes).ok().map(Cow::Owned),
    }
}

#[macro_export]
macro_rules! localized_str {
    ($source:literal) => {{
        static VALUE: std::sync::OnceLock<&'static str> = std::sync::OnceLock::new();
        if $crate::is_initialized() {
            *VALUE.get_or_init(|| $crate::translate_static($source))
        } else {
            $source
        }
    }};
}

#[cfg(test)]
mod tests {
    use super::*;

    const INDEX: &str = r#"{
        "schema_version":1,
        "source_locale":"en-US",
        "catalog_sha256":"catalog",
        "locales":[
            {"id":"en-US","english_name":"English","native_name":"English","aliases":["en"],"direction":"ltr","bundle":null},
            {"id":"ko-KR","english_name":"Korean","native_name":"한국어","aliases":["ko"],"direction":"ltr","bundle":"ko-KR.json"},
            {"id":"zh-CN","english_name":"Chinese (Simplified)","native_name":"简体中文","aliases":["zh-Hans","zh-SG"],"direction":"ltr","bundle":"zh-CN.json"},
            {"id":"zh-TW","english_name":"Chinese (Traditional)","native_name":"繁體中文","aliases":["zh-Hant","zh-HK"],"direction":"ltr","bundle":"zh-TW.json"}
        ],
        "source_formats":{
            "Today at {}":[{"text":"Today at "},{"arg":"0"}],
            "Unknown {}":[{"text":"Unknown "},{"arg":"0"}]
        }
    }"#;

    const KO: &str = r#"{
        "schema_version":1,
        "locale":"ko-KR",
        "catalog_sha256":"catalog",
        "messages":{"Open Settings":"설정 열기"},
        "formats":{"Today at {}":[{"text":"오늘 "},{"arg":"0"}]}
    }"#;

    #[test]
    fn resolves_user_marker_and_system_priority() {
        let index: LocaleIndex = serde_json::from_str(INDEX).unwrap();
        let system = vec!["de_DE.UTF-8".into(), "ko_KR".into()];

        let (explicit, _, persist) =
            resolve_locale(Some("zh-Hant"), Some("ko-KR"), &system, &index.locales);
        assert_eq!(explicit.resolved_locale, "zh-TW");
        assert_eq!(explicit.source, LocaleSource::User);
        assert_eq!(persist, None);

        let (marker, _, persist) =
            resolve_locale(None, Some("ko-KR"), &system, &index.locales);
        assert_eq!(marker.resolved_locale, "ko-KR");
        assert_eq!(marker.source, LocaleSource::LegacyMarker);
        assert_eq!(persist.as_deref(), Some("ko-KR"));

        let (system_resolution, system_locale, _) =
            resolve_locale(Some("system"), Some("zh-CN"), &system, &index.locales);
        assert_eq!(system_resolution.resolved_locale, "ko-KR");
        assert_eq!(system_resolution.source, LocaleSource::System);
        assert_eq!(system_locale.as_deref(), Some("ko-KR"));
    }

    #[test]
    fn explicit_unsupported_locale_falls_back_to_english_not_system() {
        let index: LocaleIndex = serde_json::from_str(INDEX).unwrap();
        let (resolution, _, _) =
            resolve_locale(Some("de-DE"), None, &["ko-KR".into()], &index.locales);

        assert_eq!(resolution.resolved_locale, "en-US");
        assert_eq!(resolution.source, LocaleSource::EnglishFallback);
        assert_eq!(
            resolution.fallback_reason,
            Some(FallbackReason::UnsupportedPreference)
        );
    }

    #[test]
    fn normalizes_platform_locale_forms_and_chinese_aliases() {
        assert_eq!(normalize_locale_tag("pt_BR.UTF-8@latin"), "pt-BR");
        assert_eq!(normalize_locale_tag("zh_hans"), "zh-Hans");

        let index: LocaleIndex = serde_json::from_str(INDEX).unwrap();
        let (simplified, _, _) =
            resolve_locale(None, None, &["zh_SG.UTF-8".into()], &index.locales);
        let (traditional, _, _) =
            resolve_locale(None, None, &["zh-HK".into()], &index.locales);
        assert_eq!(simplified.resolved_locale, "zh-CN");
        assert_eq!(traditional.resolved_locale, "zh-TW");
    }

    #[test]
    fn translates_static_formats_and_english_misses() {
        let registry = Registry::build(
            INDEX,
            Some(KO),
            InitRequest {
                user_preference: Some("ko-KR"),
                legacy_locale: None,
            },
            &[],
        );

        assert_eq!(registry.translate_static("Open Settings"), "설정 열기");
        assert_eq!(registry.translate_static("Missing"), "Missing");
        assert_eq!(
            registry.format_message("Today at {}", &[("0", "오후 3시".into())]),
            "오늘 오후 3시"
        );
        assert_eq!(
            registry.format_message("Unknown {}", &[("0", "value".into())]),
            "Unknown value"
        );
    }

    #[test]
    fn corrupt_or_mismatched_bundle_builds_english_registry() {
        let corrupt = Registry::build(
            INDEX,
            Some("{"),
            InitRequest {
                user_preference: Some("ko-KR"),
                legacy_locale: None,
            },
            &[],
        );
        assert_eq!(corrupt.outcome.resolved_locale, "en-US");
        assert_eq!(
            corrupt.outcome.fallback_reason,
            Some(FallbackReason::CorruptBundle)
        );

        let wrong_hash = KO.replace("catalog", "other");
        let mismatch = Registry::build(
            INDEX,
            Some(&wrong_hash),
            InitRequest {
                user_preference: Some("ko-KR"),
                legacy_locale: None,
            },
            &[],
        );
        assert_eq!(mismatch.outcome.resolved_locale, "en-US");
    }

    #[test]
    fn missing_format_argument_returns_the_english_source() {
        let registry = Registry::build(
            INDEX,
            Some(KO),
            InitRequest {
                user_preference: Some("ko-KR"),
                legacy_locale: None,
            },
            &[],
        );

        assert_eq!(registry.format_message("Today at {}", &[]), "Today at {}");
    }

    #[test]
    fn preinitialization_macro_result_is_not_cached() {
        assert_eq!(localized_str!("Open Settings"), "Open Settings");
        let outcome = initialize(InitRequest {
            user_preference: Some("ko-KR"),
            legacy_locale: None,
        });
        assert_eq!(outcome.resolved_locale, "ko-KR");
        assert_eq!(localized_str!("Open Settings"), "설정 열기");
    }
}
