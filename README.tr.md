# md-context

[![CI](https://github.com/YusufBeratZengin/md-context/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/md-context/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/md-context.svg)](https://pypi.org/project/md-context/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Lisans](https://img.shields.io/github/license/YusufBeratZengin/md-context.svg)](LICENSE)

[English](README.md)

Yerel Markdown notlarından ve Obsidian kasalarından dil modelleri için bütçeli bağlam paketleri üretir.

![md-context CLI gösterimi](docs/demo.svg)

## Neden md-context?

- **Aşma yapmayan kesin token bütçesi**: Çıktının tamamının (dosya yolları, başlıklar ve JSON çerçevesi dahil) belirlenen token bütçesine tam olarak sığmasını garanti eder; LLM bağlam penceresinin taşmasını ve API hatalarını önler.
- **Çizge destekli BM25 sıralaması**: BM25 sözcüksel alaka düzeyini başlık/etiket artışları, güncellik katsayısı ve çift yönlü 1-sekmeli bağlantı/etiket çizgesiyle birleştirir; gömme modeli veya vektör veritabanı gerektirmeden kişisel notlardan yüksek doğruluklu bağlam çeker.
- **Yerel, hızlı ve gizlilik öncelikli**: Sıfır çalışma zamanı bağımlılığı, sıfır dış ağ çağrısı ve anında başlama süresi. `visibility: private` notları ve `.mdcontextignore` kalıplarını metin belleğe veya önbelleğe hiç girmeden dışlar.

## Hızlı başlangıç

### 1. Kurulum

PyPI üzerinden kurabilirsiniz:

```sh
python -m pip install md-context
```

### 2. Örnek kasa üzerinde deneme

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

### 3. Kurulum yapmadan çalıştırma

POSIX kabuğu:

```sh
PYTHONPATH=src python -m md_context query "water storage" --root tests/fixtures/vault --cache-dir .cache
```

PowerShell karşılığı:

```powershell
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'
py -m md_context query 'water storage' --root tests/fixtures/vault --cache-dir .cache
```

### 4. Kendi kasanızın içinde çalışma

```sh
cd /path/to/notes
md-context index . --strip-diacritics
md-context query "sulama planı" --budget 4000
md-context query "sulama planı" --budget 4000 --format json
md-context query "sulama planı" --top 2 --include-tag bahce
md-context stats
```

## Kullanım örnekleri

### Bir dil modeline veya ajana aktarma

Kullanıma hazır boru hattı betikleri [`examples/agent-pipe.sh`](examples/agent-pipe.sh) ve [`examples/agent-pipe.ps1`](examples/agent-pipe.ps1) dosyalarında yer alır.

Standart girdiden bağlam okuyabilen yerel bir ajanınız varsa:

```sh
md-context query "sulama planı" --root ./notlar --budget 4000 | local-agent
```

`local-agent` kendi ajan komutunuz için bir yer tutucudur. md-context ağ isteği yapmaz. Çıktının nereye gönderileceğini alıcı komut belirler; dış servise göndermeden önce paketi inceleyin.

Örnek Markdown çıktısı (alıntı):

```markdown
# Context pack

Query: valve

## Valve schedule

Source: `Orchard.md`

Open the east valve at sunrise. Check soil moisture before the next irrigation cycle.
```

JSON çıktısında (`--format json`) `query`, `budget`, `estimated_tokens` ve `sources` bulunur. Her kaynakta `path`, `title`, `heading`, `content`, `score` ve `truncated` alanları yer alır. Eşleşme yoksa boş paket üretilir. Çıktının temel alanlarına bile yetmeyen bir bütçe hata verir.

### `query` komutu seçenekleri

- `--budget N`: Çıktının tamamı için azami token bütçesi (varsayılan: `4000`).
- `--format md|json`: Çıktı biçimi; varsayılan `md`. Geçersiz değerler 2 koduyla sonlanır.
- `--top N`: Pakete eklenecek en fazla bölüm sayısı. Pozitif bir sayı olmalıdır.
- `--include-tag TAG`: Yalnızca bu etikete sahip notları dahil et (birden fazla eklenebilir).
- `--exclude-tag TAG`: Bu etikete sahip notları dışla (birden fazla eklenebilir).
- `--cache-dir PATH`: İndeks önbelleğinin okunacağı ve yazılacağı özel klasör yolu.
- `--root PATH`: Not kasasının kök klasörü.

### Python API

```python
from md_context import build_index, build_pack, load_index, save_index, search

# 1. Bellekte indeks oluşturma
index = build_index("./notlar", strip_diacritics=True)
save_index(index)  # İsteğe bağlı: .md-context/index.json dosyasına kaydeder

# 2. Notları arama
matches = search(index, "su", title_boost=2.0, neighbor_boost=0.2)

# 3. Bütçeli bağlam paketi oluşturma
pack = build_pack(
    index,
    "su",
    budget=4000,
    top=5,
    include_tags=["bahce"],
    output_format="json",
)
print(pack.to_json(), end="")

# 4. Özel bir tokenizer bağlama
# pack = build_pack(index, "su", estimator=lambda text: len(encoder.encode(text)))
```

Özel tahminciler deterministik olmalı ve negatif olmayan tamsayı döndürmelidir. Bütçe doğrulaması için üretilen nihai çıktı yeniden ölçülür.

### Sıralama ve getirme mantığı

- Unicode sözcük belirteçleri harf duyarsız eşleştirilir. `I`, `İ`, `ı` ve `i` birbirleriyle eşleşir; isteğe bağlı aksan katlama ile `café` ve `cafe` de eşleşir.
- BM25 parametreleri: `k1=1.2`, `b=0.75`. Başlık ve etiket eşleşmeleri, terimin IDF değerinin sırasıyla 2.0 ve 1.5 katı kadar ek puan kazandırır.
- Güncellik çarpanı en çok 1.15'tir ve 90 günlük ölçekte azalır. Önce geçerli `updated`, sonra `date`, en son dosya mtime zamanı kullanılır.
- `[[not]]`, `[[klasor/not#başlık|görünen metin]]` ve `#etiket` grupları notları bağlar. Doğrudan komşular, en güçlü sözcüksel eşleşmenin puanının yüzde 20'si kadar artış alır; bu artış zincirleme yayılmaz.
- `#`–`######` başlıkları bölümleri ayırır; kod blokları korunur. Bölümler not alaka düzeyi ve sorgu örtüşmesine göre sıralanarak bütçeye yerleştirilir.

Varsayılan tahmin `ceil(karakter_sayısı / 4)` formülüdür; modelin gerçek tokenizer'ı değildir. Bütçeye sorgu, kaynak yolları, başlıklar, JSON alanları ve kesilme işaretleri dahildir.

### Performans ve kıyaslama

md-context, yüklenen `Index` nesnesi üzerinde tokenize edilmiş metinleri ve ters dizini bellekte önbelleğe alır; kalıcı JSON şeması sürümünü değiştirmez.

2.000 notluk sentetik bir kasada yapılan ölçümde (`scripts/benchmark.py`):
- `build_index`: ~6,6 s
- `save_index`: ~0,10 s
- `load_index`: ~0.03 s
- 20 sorgu: toplam ~1,5 s (bellekteki önbellek ile sorgu başına ortalama ~76 ms; ilk ısınma sorgusu ~130 ms)

*(Python 3.11 altında ölçülmüş yaklaşık, makineye bağlı değerlerdir).*

## Yapılandırma

### Not ön bilgisi (Frontmatter)

Dosya başındaki YAML ön bilgisi başlık, etiket, tarih ve gizlilik için okunur:

```yaml
---
title: "Sulama planı"
tags: [bahçe, su]
date: 2026-01-15
updated: "2026-02-01T09:00:00Z"
visibility: public
---
```

- Düz `anahtar: değer` çiftleri, satır içi ve blok listeler, tırnaklı metinler ve yorumlar desteklenir.
- Tarihler dahil tekil değerler metin olarak korunur.
- `visibility: private` değeri, notu belleğe veya arama önbelleğine hiç girmeden tamamen dışlar.

### Dışlanan dosyalar (`.mdcontextignore`)

Kasaya ait kök dizinde `.mdcontextignore` dosyası oluşturarak yolları dışlayabilirsiniz:

```gitignore
# Dosya taban adı her derinlikte eşleşir
gecici-*.md
arsiv/

# / içeren yollar kasa köküne göredir
taslaklar/**/*.md
!taslaklar/hazir.md
```

- `.git/`, `.obsidian/`, `.md-context/` ve sembolik bağlantılar her zaman göz ardı edilir.
- `!` ön eki önceden dışlanmış dosyaları yeniden dahil eder.
- Kalıplar tüm işletim sistemlerinde büyük/küçük harfe duyarlıdır.

### Önbellek depolama ve bulma

- İndeks anlık görüntüleri varsayılan olarak kasa kökündeki `.md-context/index.json` altında tutulur.
- `--cache-dir PATH` veya `MD_CONTEXT_CACHE` ortam değişkeni ile farklı bir yol belirtebilirsiniz.
- CLI üzerinden çalışırken `query` ve `stats`, bulunulan klasörden yukarı doğru ilk `.md-context/index.json` dosyasını bulur. Her çalıştırma kaynak klasörü yeniden tarar ve önbelleği atomik olarak günceller.
- Önbellek dahil edilen notların tam metnini barındırır. Gizli kalması gereken ortamlara bu klasörü dahil etmeyin. [SECURITY.md](SECURITY.md) dosyasına bakın.

### Normalizasyon seçenekleri

- `index` komutuna `--strip-diacritics` bayrağını vererek aksan ve harf işaretlerini aramada kaldırabilirsiniz (`café` ile `cafe` eşleşir).
- Türkçe `i` / `I` / `İ` / `ı` harf dönüşümleri bayrak gerekmeksizin yerel olarak desteklenir.
- Aksan kaldırmayı kapatmak için `index` komutunu bu bayrak olmadan yeniden çalıştırın.

## SSS ve kısıtlamalar

### md-context bir vektör veritabanı veya gömme araması mıdır?
Hayır. md-context, bağlantı çizgesi yayılımı ve güncellik ağırlıklandırmasıyla zenginleştirilmiş BM25 sözcüksel sıralamasını kullanır. GPU, model ağırlıkları veya uzak embedding API çağrıları gerektirmez.

### Token tahmini nasıl hesaplanır?
Varsayılan olarak `ceil(karakter_sayısı / 4)` formülü kullanılır. Python API'si üzerinden `estimator` parametresiyle kesin tokenizer fonksiyonunuzu verebilirsiniz. Bütçe çıktının tamamını (Markdown veya JSON çerçevesi dahil) kapsar.

### Hangi ön bilgi sözdizimi desteklenir?
Yerleşik ayrıştırıcı düz anahtar-değer çiftlerini, satır içi ve blok listeleri, tırnaklı metinleri ve yorumları destekler. Güvenliği ve yalınlığı korumak amacıyla iç içe sözlükler ve YAML çapaları reddedilir.

### Sembolik bağlantılar takip edilir mi?
Hayır. Dizin dışına sızmayı önlemek için sembolik bağlantılı dosya ve dizinler yok sayılır. Önbellek ve dışlama dosyaları da sembolik bağlantı olamaz.

### Klasörde hiç Markdown dosyası yoksa ne olur?
`index` 0 not kaydeder, `query` boş bir bağlam paketi döndürerek 0 koduyla tamamlanır ve `stats` komutu `{"notes": 0, ...}` çıktısı verir. Hatalı ön bilgi veya bozuk dosyalarda 2 çıkış koduyla açıklayıcı hata iletilir; kontrolsüz hata dökümü oluşmaz.

## Katkıda bulunma

Katkılarınız, hata bildirimleriniz ve önerileriniz memnuniyetle karşılanır!

1. Depoyu forklayın ve yerel makinenize klonlayın.
2. Geliştirme bağımlılıklarını kurun:
   ```sh
   python -m pip install -e ".[dev]"
   ```
3. Testleri kapsam raporuyla çalıştırın:
   ```sh
   python -m pytest
   ```
4. Kod biçimlendirmesi, lint ve tip denetimini doğrulayın:
   ```sh
   python -m ruff check .
   python -m ruff format --check .
   python -m mypy
   ```

Ayrıntılı yönergeler için [CONTRIBUTING.md](CONTRIBUTING.md) ve [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) belgelerine bakabilirsiniz. Değişiklikler [CHANGELOG.md](CHANGELOG.md) içinde tutulmaktadır.

## Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında lisanslanmıştır.
