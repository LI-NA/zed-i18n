/// Returns the display label for a language name.
///
/// Mirrors the VS Code convention: only the synthetic "Plain Text" language is
/// localized. Real language names (Rust, Python, Markdown, ...) are proper
/// nouns and are shown verbatim.
pub(crate) fn localized_language_name(name: &str) -> String {
    if name == "Plain Text" {
        localization::localized_str!("Plain Text").to_owned()
    } else {
        name.to_owned()
    }
}

/// Returns fuzzy-match highlight positions that are still valid for `label`.
///
/// The picker's match positions are UTF-8 byte offsets into the English match
/// string. When localization produced a different label they no longer fall on
/// that label's character boundaries, so the highlight is dropped instead of
/// pointing at the wrong bytes.
pub(crate) fn localized_match_positions(
    label: &str,
    mat: &fuzzy::StringMatch,
) -> Vec<usize> {
    if label.starts_with(mat.string.as_str()) {
        mat.positions.clone()
    } else {
        Vec::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn string_match(string: &str, positions: Vec<usize>) -> fuzzy::StringMatch {
        fuzzy::StringMatch {
            candidate_id: 0,
            score: 1.0,
            positions,
            string: string.to_owned(),
        }
    }

    #[test]
    fn shows_real_language_names_verbatim() {
        assert_eq!(localized_language_name("Rust"), "Rust");
    }

    #[test]
    fn falls_back_to_the_source_name_without_a_loaded_locale() {
        assert_eq!(localized_language_name("Plain Text"), "Plain Text");
    }

    #[test]
    fn keeps_positions_when_the_label_extends_the_match_string() {
        let mat = string_match("Plain Text", vec![0, 1]);
        assert_eq!(
            localized_match_positions("Plain Text (current)", &mat),
            vec![0, 1],
        );
    }

    #[test]
    fn drops_positions_when_localization_changed_the_label() {
        let mat = string_match("Plain Text", vec![0, 1]);
        assert_eq!(
            localized_match_positions("일반 텍스트", &mat),
            Vec::<usize>::new(),
        );
    }
}
