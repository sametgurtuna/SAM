<div align="center">

# 📦 SAM — Kurulum Rehberi

**SAM'ı tam fonksiyonel çalıştırmak için bu adımları takip edin.**

</div>

---

## Genel Bakış

Bu rehber SAM'ın tüm bağımlılıklarını kurmanız, lokal LLM modelini yapılandırmanız ve uygulamayı çalıştırmanız için gereken adımları kapsar.

| Adım | Süre | Açıklama |
|:---|:---|:---|
| 1. Python bağımlılıkları | ~2 dk | `requirements.txt` üzerinden kurulum |
| 2. Ollama kurulumu | ~3 dk | Lokal LLM motoru |
| 3. Model indirme | ~5 dk | ~2 GB model dosyası |
| 4. Test & doğrulama | ~1 dk | Modelin düzgün çalıştığını kontrol |
| 5. SAM'ı çalıştırma | Anlık | `python main.py` |

---

## 1. Python Bağımlılıkları

```bash
cd SAM
pip install -r requirements.txt
```

Bu komut PyQt6, faster-whisper, openwakeword, edge-tts ve diğer bağımlılıkları yükler.

> [!NOTE]
> İlk çalıştırmada Whisper modeli (~145 MB) ve wake word modelleri (~15 MB) otomatik indirilir. Bir kere indirildikten sonra cache'lenir ve tekrar indirilmez.

---

## 2. Ollama Kurulumu (Lokal LLM)

SAM varsayılan olarak **Ollama** kullanır — tamamen lokal, tamamen ücretsiz.

### Windows

1. [ollama.com/download](https://ollama.com/download) adresinden Windows installer'ı indirin
2. `OllamaSetup.exe` dosyasını çalıştırın
3. Kurulum tamamlanınca Ollama arka planda otomatik başlar

### macOS

```bash
brew install ollama
```

Veya [ollama.com/download](https://ollama.com/download) adresinden `.dmg` dosyasını indirin.

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Doğrulama

```bash
ollama --version
```

Beklenen çıktı: `ollama version 0.x.x`

---

## 3. Model İndirme

SAM varsayılan olarak `qwen2.5:3b` modelini kullanır:

```bash
ollama pull qwen2.5:3b
```

Bu komut ~2 GB indirir. Tamamlanınca model kullanıma hazır olur.

### Alternatif Modeller

| Model | Boyut | RAM İhtiyacı | Açıklama |
|:---|:---|:---|:---|
| `qwen2.5:3b` | 2.0 GB | ~3 GB | ⭐ **Önerilen** — en iyi kalite/boyut dengesi |
| `qwen2.5:1.5b` | 1.0 GB | ~2 GB | Daha hızlı ama daha az akıllı |
| `llama3.2:3b` | 2.0 GB | ~3 GB | Meta'nın küçük modeli, iyi genel amaçlı |
| `phi3.5` | 2.2 GB | ~3 GB | Microsoft, güçlü muhakeme |
| `gemma2:2b` | 1.6 GB | ~2.5 GB | Google'ın hafif modeli |

Farklı bir model denemek için:

```bash
ollama pull llama3.2:3b
```

Ardından `config.yaml` içinde model adını güncelleyin:

```yaml
llm:
  ollama:
    model: "llama3.2:3b"
```

---

## 4. Model Testi

Ollama'nın düzgün çalıştığını doğrulayın:

```bash
ollama run qwen2.5:3b "Merhaba, nasıl yardımcı olabilirim?"
```

Yanıt alıyorsanız kurulum başarılı demektir. ✅

---

## 5. SAM'ı Çalıştırma

```bash
cd SAM
python main.py
```

Konsolda aşağıdaki çıktıyı göreceksiniz:

```
  ╔════════════════════════════════════════════╗
  ║   SAM — AI Desktop Assistant  v0.3.0      ║
  ║                                            ║
  ║   Say 'Hey Jarvis'   to activate (voice)   ║
  ║   Press CTRL+SPACE   to activate (key)     ║
  ║   Press ESC           to dismiss            ║
  ║   Press CTRL+C        to quit               ║
  ║                                            ║
  ║   LLM: Ollama (qwen2.5:3b)                ║
  ╚════════════════════════════════════════════╝
```

`LLM: Ollama (qwen2.5:3b)` görünüyorsa her şey hazır! 🎉

---

## Sorun Giderme

### ❌ `No LLM available` hatası

Ollama çalışmıyor veya model yüklenmemiş:

```bash
# Ollama'yı başlat
ollama serve

# Modeli indir
ollama pull qwen2.5:3b
```

### ❌ `Ctrl + Space` çalışmıyor

`keyboard` kütüphanesi Windows'ta yönetici yetkisi gerektirebilir:

```bash
# Terminal'i "Yönetici olarak çalıştır" ile açın
python main.py
```

### ❌ Mikrofon çalışmıyor

Windows Ses Ayarları'ndan varsayılan mikrofonu kontrol edin. SAM varsayılan ses giriş cihazını kullanır.

### ❌ Wake word algılanmıyor

`config.yaml` içinde threshold değerini düşürün:

```yaml
wake_word:
  threshold: 0.3    # Varsayılan 0.5'ten 0.3'e düşür
```

---

## Opsiyonel: Claude API (Bulut Alternatifi)

Ollama yerine Claude kullanmak isterseniz:

1. [console.anthropic.com](https://console.anthropic.com) adresinden API key alın

2. Ortam değişkenini ayarlayın:

   ```bash
   # Windows (PowerShell)
   $env:ANTHROPIC_API_KEY = "sk-ant-..."

   # Linux / macOS
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. `anthropic` paketini yükleyin:

   ```bash
   pip install anthropic
   ```

SAM, Ollama bulunamazsa otomatik olarak Claude'a geçiş yapar.

---

## Yapılandırma Referansı

Tüm ayarlar `config.yaml` dosyasında bulunur. Önemli parametreler:

```yaml
llm:
  ollama:
    model: "qwen2.5:3b"            # Model adı
    temperature: 0.7                # Yaratıcılık (0.0–1.0)
    max_tokens: 256                 # Maksimum yanıt uzunluğu

wake_word:
  model: "hey_jarvis"               # Wake word modeli
  threshold: 0.5                    # Algılama hassasiyeti

stt:
  model: "base"                     # Whisper model boyutu
  language: "en"                    # Dil (null = otomatik algılama)

tts:
  voice: "en-US-GuyNeural"          # TTS ses adı
```

> Detaylı yapılandırma bilgisi için [README — Configuration Deep-Dive](README.md#-configuration-deep-dive) bölümüne bakın.

---

<div align="center">

*Daha fazla bilgi için [README.md](README.md) ve [ARCHITECTURE.md](docs/ARCHITECTURE.md) dosyalarına göz atın.*

</div>
