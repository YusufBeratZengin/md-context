# md-context

[English](README.md)

Markdown notlarından, bir dil modeline verilebilecek ve belirlenen tahmini token
bütçesine sığan bağlam paketleri üretir. Notları sorguyla ilişkilerine göre sıralar,
başlıklara göre bölümlere ayırır ve Markdown ya da JSON çıktısı verir. Obsidian
kasalarıyla ve sıradan dokümantasyon klasörleriyle çalışır. Python 3.10 ve üzerini
gerektirir; çalışma zamanı bağımlılığı yoktur.

## Kurulum ve kullanım

Depoyu indirdikten sonra:

```sh
python -m pip install .
md-context index tests/fixtures/vault
md-context query "irrigation valve schedule" --root tests/fixtures/vault --budget 4000
md-context stats --root tests/fixtures/vault
```

Kendi not klasörünüzün içinde:

```sh
md-context index . --strip-diacritics
md-context query "sulama planı" --budget 4000
md-context query "sulama planı" --budget 4000 --format json
md-context stats
```

`--strip-diacritics`, aksan ve harf işaretlerini aramada kaldırır; örneğin `café`
ile `cafe` eşleşir. `I`, `İ`, `ı` ve `i` bu seçenekten bağımsız olarak eşleşir.
Seçeneği kapatmak için `index` komutunu bu bayrak olmadan yeniden çalıştırın.

Kurulum yapmadan PowerShell üzerinden de deneyebilirsiniz:

```powershell
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'
py -m md_context query 'ışık deneyi' --root tests/fixtures/vault --budget 1000
```

`query` ve `stats`, bulunduğunuz klasörden yukarı doğru en yakın
`.md-context/index.json` dosyasını arar. Başka bir klasörden çalışırken `--root`
kullanın. Bu seçenekle daha önce indeks oluşturmuş olmanız gerekmez.

Her CLI sorgusu ve istatistik isteği, kaynak dosyaları yeniden okuyup yerel
önbelleği günceller. Böylece silinen, özel yapılan veya dışlama listesine alınan
notlar bir sonraki başarılı işlemde sonuçlardan ve önbellekten çıkar. İndeksin
harf normalleştirme ayarı korunur. Hatalı ön bilgi veya okunamayan UTF-8 dosyası,
stderr üzerinde açıklama ve 2 çıkış koduyla işlemi durdurur.

## Bir ajana aktarma

Standart girdiden bağlam okuyabilen yerel bir ajanınız varsa:

```sh
md-context query "sulama planı" --root ./notlar --budget 4000 | local-agent
```

`local-agent` kendi ajan komutunuz için bir yer tutucudur. md-context ağ isteği
yapmaz. Çıktının nereye gönderileceğini alıcı komut belirler; dış servise
göndermeden önce paketi inceleyin.

Markdown çıktısı, her bölümün başlığını ve kasaya göre kaynak yolunu içerir.
JSON çıktısında `query`, `budget`, `estimated_tokens` ve `sources` bulunur.
Her kaynakta `path`, `title`, `heading`, `content`, `score` ve `truncated` alanları
yer alır. Eşleşme yoksa boş paket üretilir. Çıktının temel alanlarına bile yetmeyen
bir bütçe hata verir.

## Not biçimi ve gizlilik

`.md` uzantılı dosyalar, büyük/küçük harf ayrımı yapılmadan UTF-8 olarak okunur.
Sembolik bağlantılar ile `.git/`, `.obsidian/` ve `.md-context/` klasörleri atlanır.
Önbellek ve dışlama dosyası da sembolik bağlantı olamaz.

```yaml
---
title: "Sulama planı"
tags: [bahçe, su]
date: 2026-01-15
updated: "2026-02-01T09:00:00Z"
visibility: private
---
```

`visibility: private` olan not, içerik önbelleğe veya arama sonuçlarına alınmadan
dışlanır. Kasaya ait `.mdcontextignore` dosyasıyla başka dosyaları da dışlayabilirsiniz:

```gitignore
arsiv/
taslak-*.md
notlar/**/*.md
!notlar/hazir.md
```

Kurallar sırayla uygulanır; sonraki `!` kuralı bir dosyayı yeniden dahil edebilir.
`*`, `?` ve karakter sınıfları tek yol parçasında; `**` sıfır veya daha fazla
klasörde eşleşir. Başta `/` köke sabitler, sonda `/` klasörleri seçer.
Eşleştirme her işletim sisteminde büyük/küçük harfe duyarlıdır. Git'in tüm dışlama
sözdizimi desteklenmez. Özel notlar ve yerleşik dışlamalar yeniden dahil edilemez.

Ön bilgi ayrıştırıcısı düz `anahtar: değer` çiftlerini, satır içi ve blok listeleri,
tırnaklı metinleri ve yorumları destekler. Çift tırnakta JSON kaçışları, tek
tırnakta ise çift apostrof kullanılır. Tarihler dahil tekil değerler metin olarak
kalır. İç içe sözlükler, YAML çapaları, çok satırlı değerler, yinelenen anahtarlar
ve kapanmamış ön bilgi hata verir. Ön bilgi dosyanın başında olmalıdır; UTF-8 BOM
kabul edilir.

Önbellek, dahil edilen notların tam metnini içerir. `.md-context/` klasörünü sürüm
kontrolüne veya not içeriğini taşımaması gereken yedeklere eklemeyin. Güncelleme
başarısız olursa önceki önbellek diskte kalır, ancak paket üretilmez. Python API
üzerinden yüklenen anlık görüntüler de yeniden indekslenene kadar değişmez.
Bir notu dışlamak, başka açık notlarda ona yapılan atıfları silmez.
[Güvenlik politikası](SECURITY.md).

## Sıralama ve bütçe

BM25 (`k1=1.2`, `b=0.75`), başlık ve etiket eşleşmeleriyle desteklenir. Güncellik
için `updated`, yoksa `date`, o da yoksa dosyanın değiştirilme zamanı kullanılır.
Seçilen tarih geçersizse dosya zamanına dönülür; saat dilimi olmayan tarihler UTC
sayılır. Güncellik artışı en çok yüzde 15'tir ve 90 günlük zaman ölçeğinde azalır.

`[[not]]`, `[[klasor/not#başlık|görünen metin]]` ve ortak `#etiket` değerleri notları
bağlar. Doğrudan komşular, en güçlü sözcüksel eşleşmenin puanının yüzde 20'si kadar
artış alır; bu artış zincirleme yayılmaz. Bağlantılar önce kasa yolu, sonra kaynak
nota göre yol, son olarak benzersiz dosya adı veya başlıkla çözülür. Belirsiz ve
eksik hedefler atlanır. `aliases` alanı ayrıştırılır ama bağlantı çözmede kullanılmaz.
Kod blokları ve satır içi kod içindeki etiketlerle bağlantılar grafiğe alınmaz.

`#`–`######` başlıkları bölümleri ayırır. Setext başlıklar gövde metni olarak kalır.
Paketleme, not puanını ve bölümün sorguyla örtüşmesini birlikte kullanır. Büyük bir
bölüm bütçeye sığması için baştan kesilebilir; bu durum çıktıda belirtilir.

Varsayılan tahmin `ceil(karakter_sayısı / 4)` formülüdür; modelin gerçek tokenizer'ı
değildir. Bütçeye sorgu, kaynak yolları, başlıklar, JSON alanları ve kesilme
işaretleri dahildir. JSON tahmini, kendi rakamlarının kapladığı alan nedeniyle
biraz yüksek olabilir. Sınır seçilen tahminci ve çıktı biçimi için geçerlidir.
Kesme işlemi cümleyi veya kod bloğunu ortadan bölebilir. Ajanın sistem istemi,
araçları ve yanıtı için ayrıca yer ayırın.

## Python API ve geliştirme

```python
from md_context import build_index, build_pack

index = build_index("./notlar", strip_diacritics=True)
pack = build_pack(index, "sulama", budget=4000, output_format="json")
print(pack.to_json(), end="")
```

`build_pack(..., estimator=...)` ile metin alıp negatif olmayan tamsayı döndüren
kendi sayacınızı verebilirsiniz. Tahminci deterministik olmalıdır. Monoton olmayan
sayaçlar bütçenin bir kısmını boş bırakabilir; son çıktı da ölçülerek bütçe sınırı
doğrulanır. `build_index` kaynağı yeniler; `load_index` yalnızca
önbelleği okur. Veriler bellekte işlenir ve her sorguda taranır; büyük kasalarda
yavaşlayabilir. Vektör araması yoktur.

```sh
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Testler özgün, kurmaca notlar kullanır; geçici dosyalar depo içindeki
`is/test-tmp/` altında tutulur. CI, Ubuntu ve Windows üzerinde Python 3.10 ve 3.14
ile çalışır. [Katkı rehberi](CONTRIBUTING.md), [değişiklikler](CHANGELOG.md),
[MIT lisansı](LICENSE).
