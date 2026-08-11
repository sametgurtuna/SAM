# SAM — EXE / Installer Build Rehberi

Bu dosya her yeni sürüm için `.exe` ve installer (`SAM-Setup-x.y.z.exe`) almanın
adım adım sürecidir. Amaç: bu işlemi bana (Claude'a) sordurmadan tek başına
tekrarlayabilmen.

---

## 0) Bir kerelik kurulumlar (zaten yapıldıysa atla)

```powershell
pip install pyinstaller
```

**Inno Setup 6** — installer (`SAM-Setup-x.y.z.exe`) üretmek için gerekli.
Bu makineye winget ile kuruldu:

```powershell
winget install -e --id JRSoftware.InnoSetup
```

Bu makinede kurulum yolu (Program Files değil, kullanıcıya özel klasör):
`C:\Users\samet\AppData\Local\Programs\Inno Setup 6\ISCC.exe`

Her seferinde tam yol yazmamak istersen o klasörü PATH'e ekleyebilirsin, ama
gerekli değil — Adım 4'teki komut zaten tam yolu kullanıyor.

---

## 1) Sürüm numarasını güncelle

Yeni bir sürüm çıkaracağın **her seferinde** aşağıdaki 4 dosyada aynı sürüm
numarasını (örn. `0.4.1`) elle güncelle — hepsi birbirinden bağımsız, tek bir
merkezi "version" değişkeni yok:

| Dosya | Satır |
|---|---|
| `core/config.py` | `"version": "0.4.1",` (DEFAULTS içinde, `app` altında) |
| `config.yaml` | `version: 0.4.1` (kendi gitignored'lı dosyan) |
| `config.example.yaml` | `version: 0.4.1` (repoya giden şablon) |
| `installer/SAM.iss` | `#define AppVersion     "0.4.1"` |

İstersen `README.md` / `ROADMAP.md` içindeki "What's new" / changelog
bölümlerini de güncelle ama bu, build'in çalışması için şart değil.

---

## 2) Build öncesi kontrol listesi

- [ ] `assets/models/hey_sam.onnx` diskte mevcut mu? (git'e girmiyor, elle
      kopyalanmış olmalı — yoksa `SAM.spec` build'i doğrudan durdurur.)
- [ ] Çalışan bir SAM örneği açık değil (dosya kilidi/DLL çakışması olmasın).
- [ ] `config.yaml` içinde gerçek Spotify anahtarların vs. olsa da sorun
      değil — `SAM.spec` içindeki güvenlik kontrolü `config.yaml`,
      `.cache`, `*oauth*`, `*.log` gibi dosyaları paket dışına **elle
      engelliyor**, yanlışlıkla paketlenemezler.
- [ ] Eski build klasörlerini temizle:

```powershell
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
```

---

## 3) PyInstaller ile `.exe` üret (onedir)

Proje kök dizininde (venv aktifken):

```powershell
pyinstaller SAM.spec
```

Bu, `dist\SAM\` klasörünü üretir — içinde `SAM.exe` ve tüm bağımlılıklar var.
Build birkaç dakika sürebilir (özellikle `ctranslate2` / `onnxruntime` DLL
toplama adımında).

**Build biterse ama hata verirse:** genelde eksik bir hidden import ya da
native DLL'dir — `SAM.spec` içindeki `hiddenimports` / `binaries` listesine
bakılır. Şu an torch, pandas, tkinter, matplotlib gibi ağır paketler bilinçli
olarak `excludes` içinde — onları geri eklemeye gerek yok.

### Hızlı manuel test

```powershell
.\dist\SAM\SAM.exe
```

Orb görünmeli, "hey sam" ile tetiklenmeli, Ollama'ya yanıt alabilmeli. Sorun
varsa `%LOCALAPPDATA%\SAM\logs\sam.log` (frozen build log yolu) veya proje
içindeki `logs/sam.log`'a bak.

---

## 4) Installer'ı üret (Inno Setup)

```powershell
& "C:\Users\samet\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\SAM.iss
```

(Eğer `iscc` PATH'e eklendiyse sadece `iscc installer\SAM.iss` yeterli.)

Bu, `installer\SAM.iss` içindeki `[Files]` bölümünden `dist\SAM\*`'i alıp
şunu üretir:

```
installer\Output\SAM-Setup-0.4.1.exe
```

(Dosya adı `#define AppVersion` değerinden otomatik türetiliyor — Adım 1'de
güncellemeyi unutma, yoksa eski sürüm numarasıyla installer çıkar.)

---

## 5) Installer'ı test et

- `installer\Output\SAM-Setup-0.4.1.exe`'yi çalıştır.
- Kurulum sihirbazında "Launch SAM" ile aç, orb'un göründüğünü doğrula.
- İstersen kaldırıp (uninstall) "settings/logs/models sil?" diyaloğunun
  düzgün çalıştığını da kontrol et.

---

## 6) (Opsiyonel) Git'e işle

```powershell
git add -A
git commit -m "release: v0.4.1"
git tag v0.4.1
git push && git push --tags
```

---

## Özet — tek seferde kopyala-yapıştır (sürüm dosyalarını elle güncelledikten sonra)

```powershell
cd C:\Users\samet\Desktop\Projects\SAM
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
pyinstaller SAM.spec
& "C:\Users\samet\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\SAM.iss
```

Çıktı: `installer\Output\SAM-Setup-<version>.exe`
