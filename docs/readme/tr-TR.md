<div align="center">
  <h1>Zed-i18n</h1>
  <p><strong>Zed editörünü kendi dilinize kolayca çevirin.</strong></p>

  [![Zed v1.4.2](https://img.shields.io/badge/Zed-v1.4.2-blue?logo=zedindustries&logoColor=white)](https://github.com/zed-industries/zed/releases/tag/v1.4.2)
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

Zed-i18n, [Zed](https://zed.dev) editörünün yayın sürümlerinden arayüz dizelerini çıkaran ve çok dilli sürümler üretmek amacıyla çevirileri uygulayan bir araç setidir.

> Zed-i18n, Zed Industries ile bağlantısı olmayan bir topluluk projesidir; resmi olarak sponsor olunmamış veya onaylanmamıştır.

## Desteklenen Diller

`translations/` dizini altında şu anda 13 dil için çeviri bulunmaktadır. Mevcut çevirilerin tamamı yapay zeka tarafından üretilmiştir; ana dili konuşanların katkıları memnuniyetle karşılanır.

cs-CZ · de-DE · es-ES · fr-FR · it-IT · ja-JP · ko-KR · pl-PL · pt-BR · ru-RU · tr-TR · zh-CN · zh-TW

## İndirmeler

En güncel ikili dosyaları [Releases](https://github.com/LI-NA/zed-i18n/releases) sayfasından indirebilirsiniz.

En güncel derleme süreciyle ilgili ayrıntıları [Yayın Derlemeleri](#yayın-derlemeleri) bölümünde bulabilirsiniz; kendiniz derlemek isterseniz [Elle Derleme](#elle-derleme) bölümüne bakın.

### Derleme Güvenilirliği

- Mevcut dağıtım dosyalarına kod imzası uygulanmamıştır. Windows veya macOS üzerinde güvenlik uyarıları görülebilir.
- Tüm yayınlar `.github/workflows/i18n-release.yml` üzerinden derlenir ve derleme günlükleri [Actions](https://github.com/LI-NA/zed-i18n/actions) sekmesinden ayrıntılı olarak incelenebilir.
- Zed kaynak kodu, `config/project.toml` dosyasındaki `zed_commit` SHA değerine sabitlenmiştir; bu sayede derlemenin tam olarak hangi kaynağa dayandığı doğrulanabilir.

Güvenilir olmayan kaynaklardan gelen derlemeleri kullanmaktan kaçının; mümkün olduğunda kendiniz derleyerek güvenlik risklerini azaltabilirsiniz.

### macOS'ta Açılmadığında

Yalnızca güvendiğiniz dosyalar için Finder'da sağ tıklayıp `Aç` seçeneğini kullanın ya da Terminal'de `xattr -dr com.apple.quarantine /path/to/Zed\ i18n.app` komutuyla karantina özniteliğini kaldırın.

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
uv run zed-i18n extract --zed-root .cache/zed/v1.4.2-clean-extract
uv run zed-i18n audit-candidates --zed-root .cache/zed/v1.4.2-clean-extract
uv run zed-i18n prepare-translation --language ko-KR --zed-root .cache/zed/v1.4.2-clean-extract
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
cd .cache\zed\v1.4.2
cargo build --release --package zed --target x86_64-pc-windows-msvc -j 8
```

## Yayın Derlemeleri

Yayın derlemeleri, `.github/workflows/i18n-release.yml` içinde tanımlanan GitHub Actions aracılığıyla otomatik olarak çalışır. Zed kaynak kodu, `config/project.toml` dosyasındaki `zed_version` etiketine ve `zed_commit` SHA değerine sabitlenmiştir.

Yayın iş akışı, zed-i18n tanımlayıcısını, About bilgilerini ve otomatik güncelleme yolunu düzenlemek için dile özgü çevirilerin yanı sıra `config/distribution.toml` dosyasını da uygular. Bu işlem, otomatik güncelleme yolunu `zed-i18n` olarak yeniden yazar.

> **Not:** Zed-i18n derlemeleri, otomatik güncelleme adresini Zed'in resmi sunucusundan bu depo yayınlarındaki `manifest.json` dosyasına yönlendirir. Otomatik güncellemeyi istemiyorsanız ayarlardan devre dışı bırakabilirsiniz.

### Telemetri

Zed-i18n telemetri davranışını değiştirmez. Varsayılan ayarlarda anonim kullanım ölçümleri ve çökme raporları Zed Industries'in sunucularına gönderilebilir. Telemetriyi kapatmak için Zed ayarlarında `telemetry.metrics` ve `telemetry.diagnostics` değerlerini `false` olarak ayarlayın.

## Bilinen Kısıtlamalar

Menüler, düğmeler, araç ipuçları, ayarlar ve eylem açıklamaları gibi arayüz dizelerinin büyük çoğunluğu doğrudan değiştirme yöntemiyle işlenir. Ancak Komut Paleti veya Tuş Haritası Düzenleyicisi'nde çalışma zamanında dinamik olarak oluşturulan bazı eylem adları ayrı bir yama gerektirmekte olup henüz kapsama alınmamıştır.

Çevirisi yapılmamış bu kısımlar için, Zed sürümleri arasında yamaları güvenilir biçimde uygulamanın bir yolunu biliyorsanız katkılarınızı bekliyoruz.

## Yapay Zeka Kullanımı Hakkında

Bu projedeki kodun büyük bölümü yapay zeka araçlarının yardımıyla yazılmış olup tüm çeviriler yapay zeka tarafından üretilmiştir. Çeviri sonuçları doğrudan insan denetiminden geçmediği için hatalı çeviriler veya markalama sorunları olabilir. Bu belge de dahil olmak üzere çevirilerde bir sorun olduğunu düşünüyorsanız ya da daha iyi bir çeviri öneriniz varsa, lütfen issue veya PR açmaktan çekinmeyin.

### Çeviri Süreci

Tüm çeviriler [Yapay Zeka ile Çeviri](#yapay-zeka-ile-çeviri) bölümünde anlatılan süreçten geçirilmiştir.

1. `extract`, Zed kaynak kodundan arayüz dizesi adaylarını çeker. Sonuçlar `catalog/en-US.json` ve `manifest/ui-strings.json` dosyalarına kaydedilir.
2. `audit-candidates`, çıkarma kurallarının hangi dizeleri yakaladığını ya da kaçırdığını gözden geçirir; bu çıktı, gerçek çeviri hedef listesinin (`accepted`) yönetilmesinde kullanılır.
3. `prepare-translation`, dile özgü toplu işlemler üretir; üslup rehberi, sözlük ve mevcut olduğunda VS Code dil paketi referanslarını birlikte paketler.
4. Bir yapay zeka modeli, çeviri sonucu JSON dosyasını toplu işlem bazında yazar.
5. `merge-translation` sonuçları birleştirir; `validate` ise eksik/fazla girdileri, yer tutucuları ve korunan token tutarlılığını denetler.

Hâlihazırda kayıtlı çeviriler her dil için bu sürecin iki modelle (`Sonnet 4.6` ve `GPT-5.5`) ayrı ayrı tamamlanması ve sonuçların yeniden gözden geçirilmesiyle elde edilmiştir. Tamamlanan iki çeviri ardından `Opus 4.6` modeli aracılığıyla yeniden incelenip birleştirilerek nihai çıktıya dönüştürülmüştür.

Yapay zeka çeviri süreciyle ilgili daha fazla ayrıntı için `prompts\commands` altındaki dosyalara bakın.

## Lisans

Zed kaynaklarından türetilen içerikler (`catalog/`, `translations/`, `manifest/`, yayın çıktıları vb.) [GPL-3.0](../../LICENSE) lisansı kapsamındadır. Bu proje, Zed'in değiştirilmiş derlemelerini dağıtır. `zed-i18n` kaynak kodu ve [Visual Studio Code Localization Packs](https://github.com/microsoft/vscode-loc) kaynaklı çeviri sözlükleri (`prompts/translation/glossary/`) [MIT](../../LICENSE-MIT) lisansı kapsamındadır.

Zed ve Zed logosu Zed Industries'in mülkiyetindedir; VS Code ve VS Code dil paketi içeriğinin telif hakkı Microsoft Corporation'a aittir.
