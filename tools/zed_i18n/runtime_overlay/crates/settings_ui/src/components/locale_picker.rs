use gpui::{App, IntoElement as _, ReadGlobal as _, SharedString, Window};
use ui::{
    Button, ButtonSize, ButtonStyle, ContextMenu, DropdownMenu, DropdownStyle, Tooltip,
    prelude::*, px,
};

use crate::{
    SettingField, SettingItem, SettingsFieldMetadata, SettingsPageItem, SettingsUiFile, USER,
    get_current_value,
};

pub(crate) fn locale_setting_item() -> SettingsPageItem {
    SettingsPageItem::SettingItem(SettingItem {
        title: localization::localized_str!("Display Language"),
        description: localization::localized_str!(
            "Select the language used by the Zed interface. Changes apply after restarting Zed."
        ),
        field: Box::new(SettingField {
            organization_override: None,
            json_path: Some("ui_locale"),
            pick: |settings| settings.ui_locale.as_ref(),
            write: |settings, value, _| settings.ui_locale = value,
        }),
        metadata: None,
        files: USER,
    })
}

pub(crate) fn render_locale_picker(
    field: SettingField<settings::UiLocale>,
    file: SettingsUiFile,
    _metadata: Option<&SettingsFieldMetadata>,
    title: &'static str,
    description: &'static str,
    window: &mut Window,
    cx: &mut App,
) -> gpui::AnyElement {
    let current = get_current_value(&settings::SettingsStore::global(cx), &file, &field, cx);
    let (selected, disabled) = current
        .map(|value| (value.value.0.clone(), value.disabled))
        .unwrap_or_else(|| ("system".to_owned(), false));
    let current_label = locale_label(&selected);
    let selected_key = if selected == "system" {
        0
    } else {
        localization::available_locales()
            .iter()
            .position(|locale| locale.id == selected)
            .map(|index| index + 1)
            .unwrap_or(0)
    };
    let selected_for_menu = selected.clone();
    let write = field.write;

    let context_menu = window.use_keyed_state(("ui-locale", selected_key), cx, |window, cx| {
        ContextMenu::new(window, cx, move |mut menu, _, _| {
            for tag in std::iter::once("system").chain(
                localization::available_locales()
                    .iter()
                    .map(|locale| locale.id.as_str()),
            ) {
                let tag = tag.to_owned();
                let label = locale_label(&tag);
                let checked = tag == selected_for_menu;
                menu = menu.toggleable_entry(
                    label,
                    checked,
                    ui::IconPosition::End,
                    None,
                    move |_window, cx| {
                        let value = settings::UiLocale(tag.clone());
                        let completion = settings::SettingsStore::global(cx)
                            .update_settings_file_with_completion(
                                <dyn fs::Fs>::global(cx),
                                move |settings, app| (write)(settings, Some(value), app),
                            );
                        cx.spawn(async move |_| {
                            match completion.await {
                                Ok(Ok(())) => {}
                                Ok(Err(error)) => {
                                    log::error!("failed to save UI locale: {error:#}")
                                }
                                Err(error) => {
                                    log::error!("UI locale update was canceled: {error}")
                                }
                            }
                        })
                        .detach();
                    },
                );
            }
            menu
        })
    });

    let dropdown = DropdownMenu::new("ui-locale-dropdown", current_label, context_menu)
        .aria_label(title)
        .aria_description(description)
        .disabled(disabled)
        .tab_index(0)
        .trigger_size(ButtonSize::Medium)
        .style(DropdownStyle::Outlined)
        .offset(gpui::Point {
            x: px(0.0),
            y: px(2.0),
        });

    let selected_locale = if selected == "system" {
        localization::system_locale().unwrap_or("en-US").to_owned()
    } else {
        localization::preview_resolution(&selected).resolved_locale
    };
    let restart_required = selected_locale != localization::resolved_locale();

    // The item description on the left already explains that changes apply
    // after a restart, so the pending-restart affordance stays a single
    // compact button next to the dropdown (matching the one-row control cell
    // used by every other settings item) with the full sentence in a tooltip.
    h_flex()
        .gap_2()
        .child(dropdown)
        .when(restart_required, |row| {
            row.child(
                Button::new(
                    "restart-zed-for-ui-locale",
                    localization::localized_str!("Restart Zed"),
                )
                .style(ButtonStyle::Outlined)
                .size(ButtonSize::Medium)
                .tooltip(Tooltip::text(localization::localized_str!(
                    "Restart Zed to apply the display language."
                )))
                .on_click(|_, _, cx| workspace::reload(cx)),
            )
        })
        .into_any_element()
}

fn locale_label(tag: &str) -> SharedString {
    if tag == "system" {
        let resolved = localization::system_locale().unwrap_or("en-US");
        let native_name = localization::available_locales()
            .iter()
            .find(|locale| locale.id == resolved)
            .map(|locale| locale.native_name.as_str())
            .unwrap_or("English (United States)");
        return localization::format_message(
            "System Default ({language}, {locale})",
            &[
                ("language", native_name.to_owned()),
                ("locale", resolved.to_owned()),
            ],
        )
        .into();
    }

    localization::available_locales()
        .iter()
        .find(|locale| locale.id == tag)
        .map(|locale| format!("{} ({})", locale.native_name, locale.id))
        .unwrap_or_else(|| tag.to_owned())
        .into()
}
