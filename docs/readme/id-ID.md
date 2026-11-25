<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Terjemahkan editor Zed ke dalam bahasa Anda dengan mudah.</strong></p>

  [![Zed v1.25.3](https://img.shields.io/badge/Zed-v1.25.3-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.25.3)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Source: MIT](https://img.shields.io/badge/Source-MIT-brightgreen)](../../LICENSE-MIT)
  [![Release: GPL-3.0](https://img.shields.io/badge/Release-GPL--3.0-orange)](../../LICENSE)
  <br>
  [![Release build](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml/badge.svg)](https://github.com/LI-NA/zed-i18n/actions/workflows/i18n-release.yml)
  [![Latest release](https://img.shields.io/github/v/release/LI-NA/zed-i18n?include_prereleases&label=latest)](https://github.com/LI-NA/zed-i18n/releases/latest)
  [![Downloads](https://img.shields.io/github/downloads/LI-NA/zed-i18n/total)](https://github.com/LI-NA/zed-i18n/releases)

  <p>
    <a href="cs-CZ.md">Čeština</a> ·
    <a href="de-DE.md">Deutsch</a> ·
    <a href="../../README.md">English</a> ·
    <a href="es-ES.md">Español</a> ·
    <a href="fr-FR.md">Français</a> ·
    Bahasa Indonesia ·
    <a href="it-IT.md">Italiano</a> ·
    <a href="ja-JP.md">日本語</a> ·
    <a href="ko-KR.md">한국어</a> ·
    <a href="pl-PL.md">Polski</a> ·
    <a href="pt-BR.md">Português</a> ·
    <a href="ru-RU.md">Русский</a> ·
    <a href="tr-TR.md">Türkçe</a> ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Pengantar

Zed-i18n adalah alat untuk mengekstrak string antarmuka pengguna (UI) dari rilis resmi editor [Zed](https://zed.dev) dan menerapkan terjemahan guna menghasilkan build multi-bahasa.

> Zed-i18n adalah proyek komunitas independen dan tidak berafiliasi maupun didukung secara resmi oleh Zed Industries.

## Bahasa yang Didukung

Terjemahan untuk 14 bahasa tersedia di direktori `translations/`. Seluruh terjemahan saat ini dibuat dengan bantuan AI; kontribusi penutur asli sangat disambut baik.

cs-CZ · de-DE · es-ES · fr-FR · id-ID · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## Unduhan

Anda dapat mengunduh build terbaru dari tabel di bawah ini atau dari [Releases](https://github.com/LI-NA/zed-i18n/releases).

> [!IMPORTANT]
> Mulai dari `v1.15.0-i18n.2`, semua bahasa digabungkan ke dalam satu build universal. Pada build gabungan ini, antarmuka akan otomatis menggunakan bahasa sistem pada peluncuran pertama, dan Anda dapat mengubahnya melalui setelan `Display Language` (`ui_locale` di `settings.json`).

| Platform | aarch64 (arm64) | x86_64 (x64) |
| --- | --- | --- |
| Linux | [tar.gz](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-aarch64.tar.gz) / [deb](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-aarch64.deb) | [tar.gz](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-x86_64.tar.gz) / [deb](https://github.com/LI-NA/zed-i18n/releases/latest/download/zed-i18n-linux-x86_64.deb) |
| macOS | [dmg](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-macos-aarch64.dmg) | [dmg](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-macos-x86_64.dmg) |
| Windows | [exe](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-aarch64.exe) / [zip](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-aarch64.zip) | [exe](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-x86_64.exe) / [zip](https://github.com/LI-NA/zed-i18n/releases/latest/download/Zed-i18n-windows-x86_64.zip) |

### Membuka di macOS

Jika muncul peringatan keamanan macOS pada file unduhan, klik kanan aplikasi di Finder lalu pilih `Open`, atau hapus atribut karantina dari Terminal dengan perintah:
```bash
xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app
```

## Instalasi via Package Manager

Di macOS dan Linux menggunakan Homebrew cask:

```bash
brew trust LI-NA/zed-i18n
brew tap LI-NA/zed-i18n
brew install --cask zed-i18n
```

Di Windows menggunakan Scoop:

```powershell
scoop bucket add zed-i18n https://github.com/LI-NA/scoop-zed-i18n
scoop install zed-i18n/zed-i18n
```

## Menyiapkan Lingkungan Pengembangan

Memerlukan Python 3.12 atau lebih baru dan [`uv`](https://docs.astral.sh/uv/).

```powershell
uv sync
```

Semua perintah dijalankan melalui `uv run zed-i18n <command>`.

## Penggunaan

Versi target Zed diatur dalam `config/project.toml`. Perintah `fetch-zed` akan menyiapkan checkout yang digunakan untuk ekstraksi dan penambalan terjemahan:

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/<version>-clean-extract
uv run zed-i18n prepare-translation --language id-ID --zed-root .cache/zed/<version>-clean-extract
uv run zed-i18n merge-translation --language id-ID
uv run zed-i18n validate --language id-ID
uv run zed-i18n apply --language id-ID
```

- `extract` memindai kode sumber Rust Zed untuk menemukan teks UI dan menyimpannya di `catalog/en-US.json` serta `manifest/ui-strings.json`.
- Hasil terjemahan disimpan dalam `translations/<language>.json`.
- `validate` memastikan integritas placeholder dan token terproteksi.

## Lisensi

Konten yang diturunkan dari sumber Zed (`catalog/`, `translations/`, `manifest/`, artefak rilis, dll.) dilisensikan di bawah [GPL-3.0](../../LICENSE). Kode sumber `zed-i18n` dilisensikan di bawah [MIT](../../LICENSE-MIT).
