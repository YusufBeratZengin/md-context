# md-context

[![CI](https://github.com/YusufBeratZengin/md-context/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/md-context/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/md-context.svg)](https://pypi.org/project/md-context/)
[![License](https://img.shields.io/github/license/YusufBeratZengin/md-context.svg)](LICENSE)

[English](README.md)

Markdown notlarından, bir dil modeline verilebilecek ve belirlenen tahmini token
bütçesine sığan bağlam paketleri üretir. Notları sorguyla ilişkilerine göre sıralar,
başlıklara göre bölümlere ayırır ve Markdown ya da JSON çıktısı verir. Obsidian
kasalarıyla ve sıradan dokümantasyon klasörleriyle çalışır. Python 3.10 ve üzerini
gerektirir; çalışma zamanı bağımlılığı yoktur.

## Kurulum ve kullanım

PyPI üzerinden veya depoyu indirerek kurabilirsiniz:

```sh
python -m pip install md-context
```

Önbelleği ayrı bir klasörde tutarak hızlı başlangıç:

```sh
md-context index tests/fixtures/vault --cache-dir .cache
md-context query "valve" --root tests/fixtures/vault --cache-dir .cache --budget 4000
md-context stats --root tests/fixtures/vault --cache-dir .cache
```

Kaydedilmiş terminal çıktısı:

```text
$ md-context index tests/fixtures/vault --cache-dir .cache
{"notes": 4, "chunks": 8, "links": 2, "tags": 8, "tag_edges": 9, "excluded": 3, "strip_diacritics": false}

$ md-context query "valve" --root tests/fixtures/vault --cache-dir .cache --budget 4000
# Context pack

Query: valve

## Valve schedule

Source: `Orchard.md`

Open the east valve at sunrise. Check soil moisture before the next irrigation cycle.

## Orchard irrigation

Source: `Orchard.md`

A fictional orchard uses drip irrigation to conserve water.
See [[Water storage]] for the supply plan. #planning

## Maintenance

Source: `Orchard.md`

Inspect each filter weekly and clean sediment from the pipes.

## Water storage

Source: `Water storage.md`

A demonstration tank holds rainwater for the orchard.

## Capacity

Source: `Water storage.md`

Reserve one quarter of the tank for dry weather. [[Orchard]]

$ md-context stats --root tests/fixtures/vault --cache-dir .cache
{"notes": 4, "chunks": 8, "links": 2, "tags": 8, "tag_edges": 9, "excluded": 3, "strip_diacritics": false}
```

Kendi not klasörünüzün içinde:

```sh
md-context index . --strip-diacritics
md-context query "sulama planı" --budget 4000
md-context query "sulama planı" --budget 4000 --format json
md-context query "sulama planı" --top 2 --include-tag bahce
md-context stats
```

`--strip-diacritics`, aksan ve harf işaretlerini aramada kaldırır; örneğin `café`
ile `cafe` eşleşir. `I`, `İ`, `ı` ve `i` bu seçenekten bağımsız olarak eşleşir.
Seçeneği kapatmak için `index` komutunu bu bayrak olmadan yeniden çalıştırın.

Kurulum yapmadan PowerShell üzerinden de deneyebilirsiniz:

```powershell
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'
py -m md_context query 'su deposu' --root tests/fixtures/vault --cache-dir .cache --budget 1000
```

`query` ve `stats`, bulunduğunuz klasörden yukarı doğru en yakın
`.md-context/index.json` dosyasını arar. Başka bir klasörden çalışırken `--root`
kullanın. Anlık görüntü dosyasını başka bir yerde saklamak için `--cache-dir PATH`
veya `MD_CONTEXT_CACHE` ortam değişkenini kullanabilirsiniz.

Klasörde hiç Markdown dosyası yoksa, `index` 0 not kaydeder, `query` boş bir bağlam
paketi döndürerek 0 koduyla tamamlanır ve `stats` komutu `{"notes": 0, ...}` çıktısı verir.
Hatalı ön bilgi, bozuk önbellek dosyası veya okunamayan UTF-8 dosyası, stderr üzerinde
ilgili dosya adını belirten açıklamayla ve 2 çıkış koduyla işlemi durdurur; asla kontrolsüz
hata dökümü (traceback) oluşmaz.

## Bir ajana aktarma

Kullanıma hazır boru hattı betikleri [`examples/agent-pipe.sh`](examples/agent-pipe.sh) ve
[`examples/agent-pipe.ps1`](examples/agent-pipe.ps1) dosyalarında yer alır.

Standart girdiden bağlam okuyabilen yerel bir ajanınız varsa:

```sh
md-context query "sulama planı" --root ./notlar --budget 4000 | local-agent
```

`local-agent` kendi ajan komutunuz için bir yer tutucudur. md-context ağ isteği
yapmaz. Çıktının nereye gönderileceğini alıcı komut belirler; dış servise
göndermeden önce paketi inceleyin.

Örnek Markdown çıktısı (alıntı):

```markdown
# Context pack

Query: valve

## Valve schedule

Source: `Orchard.md`

Open the east valve at sunrise. Check soil moisture before the next irrigation cycle.
```

JSON çıktısında `query`, `budget`, `estimated_tokens` ve `sources` bulunur.
Her kaynakta `path`, `title`, `heading`, `content`, `score` ve `truncated` alanları
yer alır. Eşleşme yoksa boş paket üretilir. Çıktının temel alanlarına bile yetmeyen
bir bütçe hata verir.

### `query` komutu seçenekleri

- `--budget N`: Çıktının tamamı için azami token bütçesi (varsayılan: `4000`).
- `--format md|json`: Çıktı biçimi; varsayılan `md`. Geçersiz değerler 2 koduyla sonlanır.
- `--top N`: Pakete eklenecek en fazla bölüm sayısı. Pozitif bir sayı olmalıdır.
- `--include-tag TAG`: Yalnızca bu etikete sahip notları dahil et (birden fazla eklenebilir).
- `--exclude-tag TAG`: Bu etikete sahip notları dışla (birden fazla eklenebilir).
- `--cache-dir PATH`: İndeks önbelleğinin okunacağı ve yazılacağı özel klasör yolu.
- `--root PATH`: Not kasasının kök klasörü.

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

## Performans ve kıyaslama

md-context, yüklenen `Index` nesnesi üzerinde tokenize edilmiş metinleri ve ters
dizini bellekte önbelleğe alır; kalıcı JSON şeması sürümünü değiştirmez.

2.000 notluk sentetik bir kasada yapılan ölçümde (`scripts/benchmark.py`):
- `build_index`: ~6,6 s
- `save_index`: ~0,10 s
- `load_index`: ~0.03 s
- 20 sorgu: toplam ~1,5 s (bellekteki önbellek ile sorgu başına ortalama ~76 ms; ilk ısınma sorgusu ~130 ms)

*(Python 3.11 altında ölçülmüş yaklaşık, makineye bağlı değerlerdir).*

## Python API ve geliştirme

```python
from md_context import build_index, build_pack, load_index, save_index, search

index = build_index("./notlar", strip_diacritics=True)
save_index(index)
matches = search(index, "su", title_boost=2.0, neighbor_boost=0.2)
pack = build_pack(
    index,
    "su",
    budget=4000,
    top=5,
    include_tags=["bahce"],
    output_format="json",
)
print(pack.to_json(), end="")
```

`build_pack(..., estimator=...)` ile metin alıp negatif olmayan tamsayı döndüren
kendi sayacınızı verebilirsiniz. Tahminci deterministik olmalıdır. Monoton olmayan
sayaçlar bütçenin bir kısmını boş bırakabilir; son çıktı da ölçülerek bütçe sınırı
doğrulanır. `build_index` kaynağı yeniler; `load_index` yalnızca
önbelleği okur. Vektör araması yoktur.

```sh
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Testler özgün, kurmaca notlar kullanır; geçici dosyalar depo içindeki
`is/test-tmp/` altında tutulur. CI, Ubuntu (Python 3.10–3.14) ve Windows (Python 3.10, 3.14)
üzerinde çalışır. [Katkı rehberi](CONTRIBUTING.md), [değişiklikler](CHANGELOG.md),
[MIT lisansı](LICENSE).
