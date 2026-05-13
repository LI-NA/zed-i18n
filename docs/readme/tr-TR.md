<div align="center">
  <h1>zed-i18n</h1>
  <p><strong>Zed editörünü kendi dilinize kolayca çevirin.</strong></p>

  [![Zed v1.1.8](https://img.shields.io/badge/Zed-v1.1.8-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.1.8)
  [![Python ≥3.12](https://img.shields.io/badge/Python-≥3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue)](../../LICENSE)
  [![MIT components](https://img.shields.io/badge/MIT-components-yellow)](../../LICENSE-MIT)

  <p>
    <a href="cs-CZ.md">Čeština</a> ·
    <a href="de-DE.md">Deutsch</a> ·
    <a href="../../README.md">English</a> ·
    <a href="es-ES.md">Español</a> ·
    <a href="fr-FR.md">Français</a> ·
    <a href="it-IT.md">Italiano</a> ·
    <a href="ja-JP.md">日本語</a> ·
    <a href="ko-KR.md">한국어</a> ·
    <a href="pl-PL.md">Polski</a> ·
    <a href="pt-BR.md">Português</a> ·
    <a href="ru-RU.md">Русский</a> ·
    Türkçe ·
    <a href="zh-CN.md">简体中文</a> ·
    <a href="zh-TW.md">繁體中文</a>
  </p>
</div>

## Giriş

zed-i18n, [Zed](https://zed.dev) editörünün yayın sürümlerinden arayüz dizelerini çıkaran ve çok dilli sürümler üretmek amacıyla çevirileri uygulayan bir araç setidir.

## Desteklenen Diller

`translations/` dizini altında şu anda 13 dil için çeviri bulunmaktadır.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## İndirmeler

En güncel ikili dosyaları [Releases](https://github.com/LI-NA/zed-i18n/releases) sayfasından indirebilirsiniz. Projeyi kendiniz derlemek isterseniz aşağıdaki adımları izleyin.

Dağıtım dosyaları şu anda kod imzalı değildir. macOS uygulamayı engellerse bunu yalnızca güvendiğiniz dosyalar için yapın: Finder'da sağ tıklayıp `Aç` seçeneğini kullanın veya karantina özniteliğini `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` komutuyla kaldırın.

## Kurulum

Python 3.12 veya üzeri ile [`uv`](https://docs.astral.sh/uv/) gereklidir.

```powershell
uv sync
```

Tüm komutlar `uv run zed-i18n <command>` şeklinde çalıştırılır.

## Kullanım

Hedef Zed sürümü `config/project.toml` dosyasında belirlenir. `fetch-zed`, hem çeviri uygulama ve derleme için kullanılan çalışma kopyasını hem de dize çıkarma ve inceleme için kullanılan temiz çalışma kopyasını hazırlar.

```powershell
uv run zed-i18n fetch-zed
uv run zed-i18n extract --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.1.8-clean-extract
uv run zed-i18n merge-translation --language ko-KR
uv run zed-i18n validate --language ko-KR
uv run zed-i18n apply --language ko-KR
```

`extract`, Zed'in Rust kaynak kodunu arayüz dizesi adayları için tarar; sonuçları `catalog/en-US.json` ve `manifest/ui-strings.json` dosyalarına yazar. Çeviri sonuçları `translations/<language>.json` dosyasında saklanır.

Yeni keşfedilen dizeler `manifest/ui-strings.json` dosyasına `needs_review` durumuyla eklenir. Yalnızca arayüzde gerçekten görüntülenen dizeler `accepted` olarak işaretlenmeli ve ardından çevrilmelidir.

## Yapay Zeka ile Çeviri

Yapay zeka destekli çeviri çalışmaları için `prompts/commands/translation-start.md` dosyasını inceleyin. Birden fazla modelden elde edilen sonuçları karşılaştırmak ve birleştirmek için `prompts/commands/translation-review.md` dosyasını kullanın.

Yalnızca yeni eklenen anahtarları mevcut çevirilere dokunmadan çevirmek istiyorsanız adında `new-keys` bulunan dosyalara başvurun.

VS Code çeviri referanslarını toplu işlemlere dahil etmek için `prepare-translation` çalıştırmadan önce aşağıdaki depoları hazırlayın. Bu depolar eksikse toplu işlemler yine de normal şekilde üretilir.

```powershell
git clone https://github.com/microsoft/vscode-loc .cache/vscode-loc
git clone https://github.com/microsoft/vscode .cache/vscode-upstream
```

Yeni bir dil eklerken:

1. `prompts/translation/<language>.md` dosyasına çeviri üslubunu ve terimler sözlüğünü yazın.
2. `prepare-translation` komutuyla toplu işlemleri oluşturun.
3. Yapay zekanın ürettiği JSON sonuçlarını `merge-translation` ile birleştirin.
4. Sonucu `validate` komutuyla doğrulayın.

Dile özgü yönergeler `prompts/translation/<language>.md` dosyasında bulunur. Dosya yoksa varsayılan olarak `prompts/translation/TEMPLATE.md` kullanılır.

## Elle Derleme

Windows'ta [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022), Windows SDK, CMake ve [Rust](https://rustup.rs/) gereklidir. Derleme önbelleğini sürümler arasında `.cache/zed/target` üzerinden paylaşmak en iyi yaklaşımdır. Örnek derleme yöntemi şöyledir:

```powershell
$env:CARGO_TARGET_DIR = (Resolve-Path .cache\zed\target).Path
$env:CARGO_INCREMENTAL = "1"
cd .cache\zed\v1.1.8
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Yayın Derlemeleri

Yayın derlemeleri, `.github/workflows/i18n-release.yml` içinde tanımlanan GitHub Actions aracılığıyla otomatik olarak çalışır. Zed kaynak kodu, `config/project.toml` dosyasındaki `zed_version` etiketine ve `zed_commit` SHA değerine sabitlenmiştir.

Yayın iş akışı, zed-i18n tanımlayıcısını, About bilgilerini ve otomatik güncelleme yolunu düzenlemek için `config/distribution.toml` dosyasını uygular. Bu işlem, otomatik güncelleme yolunu `zed-i18n` olarak yeniden yazar.

## Bilinen Kısıtlamalar

Menüler, düğmeler, araç ipuçları, ayarlar ve eylem açıklamaları gibi arayüz dizelerinin büyük çoğunluğu doğrudan değiştirme yöntemiyle işlenir. Ancak Komut Paleti veya Tuş Haritası Düzenleyicisi'nde çalışma zamanında dinamik olarak oluşturulan bazı eylem adları ayrı bir yama gerektirmekte olup henüz kapsama alınmamıştır.

Zed sürümü değişse bile yamaları güvenilir biçimde uygulamanın bir yolunu biliyorsanız katkılarınızı bekliyoruz.

## Yapay Zeka Kullanımı Hakkında

Bu projedeki kodun büyük bölümü yapay zeka araçlarının yardımıyla yazılmış olup tüm çeviriler yapay zeka tarafından üretilmiştir. Kod veya çevirilerde bir hata fark ederseniz ya da daha iyi bir yaklaşım olduğunu düşünüyorsanız PR açmaktan çekinmeyin.

## Lisans

Zed kaynaklarından türetilen içerikler (`catalog/`, `translations/`, `manifest/` ve yayın çıktıları) [GPL-3.0](../../LICENSE) lisansı kapsamındadır. `zed-i18n` kaynak kodu ve [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) kaynaklı çeviri sözlükleri (`prompts/translation/glossary/`) [MIT](../../LICENSE-MIT) lisansı kapsamındadır. VS Code dil paketi içeriğinin telif hakkı Microsoft Corporation'a aittir.
