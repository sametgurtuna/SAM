# SAM — 30 Günlük Pazarlama Planı (Gün Gün, Hazır Paylaşımlarla)

Bu belge senin için hazırlandı: **her gün ne yapacağını, nereye, ne zaman ve tam olarak
ne yazarak paylaşacağını** söylüyor. Metinlerin çoğu kopyala-yapıştıra hazır — sadece
köşeli parantez `[...]` içindeki yerleri kendi bilgilerinle değiştirmen yeterli.

> **Nasıl kullanılır:** Her gün bu dosyayı aç, o güne bak, checkbox'ları işaretleyerek
> ilerle. Bir günü kaçırırsan sorun değil — bir sonraki güne geç, plan esnektir.

---

## 🧰 Başlamadan Önce Doldurman Gerekenler

Bu bilgileri bir kere doldur, aşağıdaki tüm şablonlarda kullanacağız:

| Alan | Senin Bilgin |
|---|---|
| GitHub repo linki | `https://github.com/sametgurtuna/SAM` |
| Twitter/X hesabın | `[@kullaniciadin — yoksa Gün 1'de aç]` |
| Reddit hesabın | `[u/kullaniciadin — yoksa Gün 1'de aç]` |
| YouTube kanalın | `[varsa link, yoksa Gün 3'te aç]` |
| Dev.to hesabın | `[Gün 5'te açacağız]` |
| E-posta | `sametgrtna@gmail.com` |

**Hesap oluşturma linkleri (henüz yoksa):**
- Twitter/X: https://twitter.com/signup
- Reddit: https://www.reddit.com/register
- Product Hunt: https://www.producthunt.com/
- Dev.to: https://dev.to/enter
- Hacker News: https://news.ycombinator.com/login

---

## 📅 HAFTA 1 — Hazırlık (Hiçbir Yere Paylaşım Yok, Sadece Malzeme)

Bu hafta paylaşım yapmıyoruz. Önce silah kuşanıyoruz — video, görsel, hesaplar. Erken
paylaşım hazırlıksız yakalanmak demek, o yüzden acele etme.

### Gün 1 — Hesapları Aç + GitHub'ı Süsle

**Yapılacaklar:**
- [ ] Yukarıdaki tabloda eksik olan hesapları aç (Twitter, Reddit — 5 dk her biri)
- [ ] GitHub reposuna **Topics** ekle:
  - Repo sayfası → sağ üstte ⚙️ (Settings dişlisi, "About" kutusunun yanında)
  - Şu etiketleri tek tek ekle:
    ```
    voice-assistant ollama privacy local-first pyqt6 python windows
    tts stt faster-whisper desktop-app ai-assistant self-hosted
    no-cloud offline-first
    ```
- [ ] Repo "About" açıklamasını güncelle (aynı yerde, dişlinin yanında kalem ikonu):
  ```
  A local, privacy-first Windows voice assistant powered by Ollama. No cloud, no telemetry — your voice never leaves your machine.
  ```
- [ ] Website alanına (varsa) veya boş bırak, Gün 20'de landing page ekleyeceğiz

**Bugün paylaşım YOK.** Sadece altyapı.

---

### Gün 2 — Sosyal Görsel (Social Preview) Hazırla

**Yapılacaklar:**
- [ ] Canva.com'a git (ücretsiz hesap yeterli), "Custom size" → **1280x640px**
- [ ] İçerik: `assets/preview-orb-states.png` görselini ortala, üstüne şu yazıyı ekle:
  ```
  SAM — Smart Assistant Module
  Privacy-First • Fully Local • Powered by Ollama
  ```
- [ ] PNG olarak indir, GitHub reposuna yükle:
  - Repo → Settings → General → aşağı kaydır → **Social Preview** → Upload an image
- [ ] Aynı görseli Twitter profil banner'ı için de kullanabilirsin (kırp: 1500x500px)

**Bugün paylaşım YOK.**

---

### Gün 3 — Demo Video Çek (En Kritik Adım)

Bu, tüm kampanyanın en önemli parçası. 1-2 dakikalık, sade bir ekran kaydı yeterli —
Hollywood prodüksiyonu gerekmiyor.

**Yapılacaklar:**
- [ ] OBS Studio indir (obsproject.com, ücretsiz) — yoksa kur
- [ ] Şu senaryoyu kaydet (script hazır, sırayla oku ve yap):

  ```
  0:00-0:10  "Hey Sam" de → orb'un uyanmasını göster
  0:10-0:25  Basit bir komut: "open spotify" veya "volume up"
  0:25-0:45  Bir soru sor, Ollama'nın cevap vermesini ve
             streaming TTS'in konuşmasını göster
  0:45-1:00  Ctrl+Shift+Space ile typed input'u göster
  1:00-1:15  Orb'un idle/listening/thinking/speaking state'lerini
             yakın çekim göster
  1:15-1:30  Ekranda GitHub linkini göster, "link in description" de
             (sessiz kalabilirsin, sadece ekranda yazsın)
  ```

- [ ] Kaydı YouTube'a yükle:
  - Başlık: `SAM — A Privacy-First Voice Assistant That Runs Entirely on Your PC`
  - Açıklama (kopyala-yapıştır):
    ```
    SAM is a Windows voice assistant that runs 100% locally — no cloud,
    no telemetry. Powered by Ollama for conversations and faster-whisper
    for transcription.

    ⭐ GitHub: https://github.com/sametgurtuna/SAM
    📖 Setup Guide: https://github.com/sametgurtuna/SAM/blob/main/setup.md

    Timestamps:
    0:00 Wake word activation
    0:10 Voice commands
    0:25 LLM conversation (Ollama)
    0:45 Typed input mode
    1:00 The orb states

    #VoiceAssistant #Privacy #Ollama #OpenSource #Python
    ```
  - Gizlilik: **"Unlisted"** olarak yükle (Gün 8'e kadar herkese açık yapma, önce
    GitHub README'ye gömüp test edeceğiz)

**Bugün paylaşım YOK — video hazırlığı.**

---

### Gün 4 — README'ye Video ve Rozet (Badge) Ekle

**Yapılacaklar:**
- [ ] README.md'nin en üstüne, mevcut görsellerin yanına video linkini ekle:
  ```markdown
  📺 **[Watch the 90-second demo](YOUTUBE_LINK_BURAYA)**
  ```
- [ ] Şu rozetleri README'ye ekle (mevcut badge'lerin yanına):
  ```markdown
  [![Star History Chart](https://api.star-history.com/svg?repos=sametgurtuna/SAM&type=Date)](https://star-history.com/#sametgurtuna/SAM&Date)
  ```
- [ ] `CHANGELOG.md` dosyası oluştur (yoksa), son 2-3 release'i özetle
- [ ] `CONTRIBUTING.md` oluştur — kısa tut:
  ```markdown
  # Contributing to SAM

  1. Fork & branch: `git checkout -b feature/whatever`
  2. Follow CLAUDE.md conventions (English code, Turkish inline comments,
     no shell=True, config via config.get()).
  3. No test suite — verify manually with `python main.py` and check `logs/sam.log`.
  4. Open a PR describing what changed and how you tested it.

  Looking for a place to start? Check issues labeled `good first issue`.
  ```
- [ ] GitHub'da 3 tane **"good first issue"** aç (küçük iyileştirmeler — örn. yeni bir
  komut örneği, dokümantasyon düzeltmesi, küçük bug)

**Bugün paylaşım YOK.**

---

### Gün 5 — Dev.to Hesabı + Blog Yazısı Taslağı

**Yapılacaklar:**
- [ ] Dev.to'da hesap aç (GitHub ile giriş yapabilirsin, 1 dakika)
- [ ] Şu blog yazısını taslak olarak kaydet (yayınlama, sadece draft):

  **Başlık:** `I Built a Privacy-First Voice Assistant That Actually Runs on Your Machine`

  **İçerik iskeleti (sen doldur, ~800-1200 kelime hedefle):**
  ```markdown
  ## Why I built this

  [Alexa/Google Assistant'ın verilerini buluta gönderdiği için rahatsız
  olduğun anını anlat — kişisel bir hikaye olsun, 2-3 paragraf]

  ## What SAM does differently

  - Everything runs locally: wake word (openwakeword), transcription
    (faster-whisper), and conversation (Ollama)
  - The only network call SAM makes on its own is to localhost:11434
    (your own Ollama server)
  - Claude cloud fallback is fully opt-in

  ## Architecture

  [README'deki mermaid diyagramını buraya yapıştır]

  Everything is orchestrated by a single `AppController` through PyQt
  signals — no component calls another directly.

  ## The tricky part: streaming TTS

  [core/app.py'daki _flush_streaming_tts mantığını 2-3 paragrafta anlat:
  LLM cevap üretirken cümle sınırlarını tespit edip parça parça
  seslendirme]

  ## Why SAM can't open a shell — even by accident

  [Whisper'ın sessizlikten "open command prompt" gibi bir şey
  halüsinasyon görebileceğini, bu yüzden shell erişiminin tamamen
  engellendiğini anlat]

  ## Try it yourself

  GitHub: https://github.com/sametgurtuna/SAM
  Demo video: [YOUTUBE_LINK]

  Would love feedback — what would you want from a local voice assistant?
  ```

**Bugün paylaşım YOK — taslak hazırlığı. Gün 9'da yayınlayacağız.**

---

### Gün 6 — Product Hunt "Coming Soon" Sayfası

**Yapılacaklar:**
- [ ] producthunt.com/posts/new adresine git
- [ ] "Coming Soon" / "Upcoming" olarak oluştur (henüz launch etme)
- [ ] Tagline (60 karakter sınırı):
  ```
  Privacy-first voice assistant that runs entirely on your PC
  ```
- [ ] Açıklama:
  ```
  SAM is a Windows voice assistant that never sends your voice to the
  cloud. Wake word detection, local transcription (faster-whisper), and
  conversations powered by Ollama — all running on your own machine.

  No telemetry. No API keys required. Open source.
  ```
- [ ] Gallery'e Gün 2'de yaptığın social preview görselini + demo videonun
  thumbnail'ini yükle
- [ ] "Notify me" bağlantısını kopyala, bunu bu haftanın sonunda arkadaşlarına/tanıdıklarına
  gönder (henüz herkese açık duyurmuyoruz, sadece yakın çevre)

**Bugün genel paylaşım YOK — sadece 5-10 yakın arkadaşa özel mesaj:**
```
Merhaba! Uzun zamandır üzerinde çalıştığım bir proje var — SAM adında,
tamamen lokal çalışan bir sesli asistan. Önümüzdeki hafta Product Hunt'ta
yayınlayacağım, şu an "coming soon" sayfası var. Notify list'e eklenirsen
launch günü bildirim alırsın, ilk saatlerdeki upvote'lar çok önemli 🙏
[PRODUCT HUNT LINK]
```

---

### Gün 7 — Son Kontrol + Dinlenme

**Yapılacaklar:**
- [ ] README'yi baştan sona bir yabancı gözüyle oku — anlaşılır mı?
- [ ] Video linkinin çalıştığını kontrol et
- [ ] Tüm badge'lerin doğru göründüğünü kontrol et
- [ ] Gün 8'de atacağın Hacker News ve Reddit metinlerini bir kez daha oku (aşağıda hazır)

**Bugün paylaşım YOK. Yarın lansman haftası başlıyor.**

---

## 📅 HAFTA 2 — Lansman Haftası (Asıl Paylaşımlar Burada)

> **Kural:** Bu hafta her gün **sadece bir platform**. Aynı gün 3 yere birden atma —
> hem spam gibi durur hem de yorumlara yetişemezsin.

### Gün 8 (Pazartesi) — Product Hunt Lansmanı 🏆

**Saat:** Gece 00:01 PDT (Türkiye saati ile **sabah 10:01**) — Product Hunt günü bu saatte
başlar, erken post edenler gün boyu daha çok görünür kalır.

**Yapılacaklar:**
- [ ] Coming Soon sayfasını "Launch" durumuna al
- [ ] **İlk yorumu (maker comment) hemen kendin yaz** — bu en kritik adım:
  ```
  Hey Product Hunt! 👋

  I'm Samet, and I built SAM because I was tired of voice assistants
  that send everything to the cloud.

  🎯 What makes SAM different?

  ✅ Your voice never leaves your machine
  ✅ Powered by Ollama (local LLM) — no API keys needed
  ✅ Beautiful orb UI that breathes when idle
  ✅ Can't accidentally open a terminal (yes, this matters — see why
     in the README)
  ✅ 100% open source Python — learn from it, fork it, own it

  🔍 How it works:
  Wake word → voice recording → local transcription (faster-whisper)
  → OS command OR Ollama conversation → TTS speech back

  I'd love your feedback! What would you want from a privacy-focused
  assistant?

  Try it: https://github.com/sametgurtuna/SAM
  ```
- [ ] Notify list'ine ve yakın çevrene mesaj at:
  ```
  SAM bugün Product Hunt'ta! 🚀 Bir dakikanı ayırıp upvote atarsan
  çok mutlu olurum: [PRODUCT HUNT LINK]
  ```
- [ ] Twitter'da eşzamanlı duyur:
  ```
  🎙️ SAM is live on Product Hunt today!

  A voice assistant that actually respects your privacy — 100% local,
  powered by Ollama, no cloud, no telemetry.

  Would mean a lot if you checked it out 🙏

  [PRODUCT HUNT LINK]

  #ProductHunt #Privacy #Ollama #OpenSource
  ```
- [ ] **Gün boyunca (ilk 6 saat kritik):** Her gelen yoruma 30 dk içinde yanıt ver.
  Hazır bazı yanıt şablonları:
  - Teknik soru geldiğinde → detaylı, kod referanslı cevap ver
  - "Windows only mı?" sorusuna → `"Right now yes, PyQt6 makes cross-platform possible though — Linux support is on the roadmap!"`
  - "Neden Ollama?" sorusuna → `"Wanted zero cloud dependency by default — Ollama runs the LLM entirely on your hardware."`

**Yapma:** Arkadaşlarından "sahte" upvote isteme, aynı IP'den çoklu hesap açma —
Product Hunt bunu tespit edip sıralamadan düşürüyor.

---

### Gün 9 (Salı) — Dev.to Blog Yazısını Yayınla

**Yapılacaklar:**
- [ ] Gün 5'te hazırladığın taslağı bitir ve **yayınla** (dev.to)
- [ ] Aynı yazıyı Medium'a da çapraz yayınla (canonical URL olarak Dev.to linkini işaretle,
  SEO çakışmasını önler)
- [ ] Twitter'da duyur:
  ```
  Wrote up how I built SAM's streaming TTS pipeline — speaking while
  the LLM is still generating tokens, without blocking the UI thread.

  📝 [DEV.TO LINK]

  #Python #PyQt #Ollama #BuildInPublic
  ```
- [ ] Product Hunt yorumlarına devam et (hâlâ gün 1-2 trafiği geliyor olacak)

---

### Gün 10 (Çarşamba) — Hacker News (Show HN)

**Saat:** Sabah 8-10am EST (Türkiye saati **15:00-17:00**) — HN trafiğinin en yoğun olduğu
dilim.

**Yapılacaklar:**
- [ ] news.ycombinator.com → "submit"
- [ ] Başlık:
  ```
  Show HN: SAM – Privacy-first voice assistant with local Ollama LLM
  ```
- [ ] URL: GitHub repo linki
- [ ] Post attıktan **hemen sonra** ilk yorumu sen yaz (HN'de maker'ın kendi yorumu
  çok önemli, "self-promotion" değil, "context" olarak görülür):
  ```
  I built SAM as a replacement for Alexa/Google Assistant after realizing
  how much voice data was being sent to the cloud.

  Technical highlights:

  - PyQt6 orb UI that lives at the bottom of the window stack until called
  - faster-whisper for local STT (CTranslate2, int8 quantized)
  - Ollama for LLM conversations (qwen2.5:3b by default)
  - No shell access ever — even from Whisper hallucinations on silence
  - Streaming TTS while the LLM is still generating

  The trickiest part was the streaming TTS pipeline — had to buffer
  tokens, detect sentence boundaries mid-stream, and queue audio chunks
  without blocking the UI.

  Architecture doc: https://github.com/sametgurtuna/SAM/blob/main/docs/ARCHITECTURE.md

  Happy to answer technical questions!
  ```
- [ ] **İlk 2 saat çok kritik** — her teknik soruya detaylı, savunmacı olmayan
  yanıt ver. HN kullanıcıları eleştirel olabilir, sakin ve teknik kal.
- [ ] Eleştiri gelirse (örn. "neden Electron değil de PyQt") şu tonu kullan:
  ```
  Fair question — I went with PyQt6 mainly for [gerçek sebebini yaz:
  performans, native feel, vb.]. Trade-off is [dürüstçe belirt].
  ```

**Not:** Show HN pazartesi hariç her gün post edilebilir; salı-perşembe en iyisi. Aynı
hafta hem Product Hunt hem HN yapıyoruz çünkü trafik kaynakları farklı — birbirini
yemez.

---

### Gün 11 (Perşembe) — Reddit r/SelfHosted

**Saat:** Sabah 7-10am EST (Türkiye **14:00-17:00**)

**Yapılacaklar:**
- [ ] Önce subreddit kurallarını oku (r/SelfHosted/wiki/rules) — self-promo izinli mi
  kontrol et, bazı günler/formatlar zorunlu olabilir
- [ ] Post başlığı:
  ```
  SAM – self-hosted voice assistant powered by Ollama (no cloud)
  ```
- [ ] İçerik:
  ```
  Hey r/selfhosted!

  I built SAM, a voice assistant that runs entirely locally — no cloud,
  no telemetry, just Ollama + faster-whisper on your own hardware.

  **Why I built it:**
  Got tired of Alexa/Google Assistant sending every word to the cloud.
  Wanted something I could actually audit.

  **Key features:**
  - Wake word detection (openwakeword, ONNX, low CPU)
  - Local transcription (faster-whisper)
  - Ollama integration for conversations
  - Streaming TTS (speaks while the LLM generates)
  - No shell access, ever — even Whisper hallucinations can't trigger one

  **Tech stack:** Python 3.11 · PyQt6 · Ollama · faster-whisper · edge-tts

  Demo video: [YOUTUBE LINK]
  Source: https://github.com/sametgurtuna/SAM

  Open to feedback and contributions!
  ```
- [ ] Yorumlara aynı gün içinde yanıt ver

---

### Gün 12 (Cuma) — Twitter Thread (Behind the Scenes)

**Yapılacaklar:**
- [ ] Bir thread at — mimari üzerine, satış değil, teknik hikaye:
  ```
  1/ Spent the last few months building SAM, a fully local voice
     assistant. Here's how the architecture works 🧵

  2/ Everything is orchestrated by one AppController through PyQt
     signals. No component ever calls another directly — wake word,
     recorder, STT, LLM router, and TTS all just emit/listen.

  3/ The state machine is dead simple:
     IDLE → LISTENING → THINKING → SPEAKING → IDLE
     One function owns every transition. Makes debugging trivial.

  4/ The fun part: streaming TTS. SAM starts speaking a sentence while
     the LLM is still generating the next one. Sentence-boundary
     detection on a live token stream, queued to a single TTS worker
     thread.

  5/ Security-wise: SAM physically cannot open a shell, from voice or
     text. Whisper can hallucinate phrases from silence — if one of
     those ever said "open command prompt," earlier versions would
     have opened one. Not anymore.

  6/ It's all open source: https://github.com/sametgurtuna/SAM

  If you're into local-first tooling or Ollama, would love a star ⭐
  ```
- [ ] Hafta boyunca gelen tüm platform yorumlarına (PH, HN, Reddit) son bir tur atıp
  cevaplanmamış olanları kapat

**Hafta 2 sonu hedefi:** 80-120 GitHub star

---

## 📅 HAFTA 3 — İkinci Dalga (Farklı Kitleler)

### Gün 13 (Pazartesi) — Reddit r/LocalLLaMA

**Yapılacaklar:**
- [ ] Başlık:
  ```
  Built a voice assistant around Ollama with streaming TTS
  ```
- [ ] İçerik (r/SelfHosted'dakinden farklı, Ollama entegrasyonuna odaklan):
  ```
  Sharing a project for anyone running Ollama locally — SAM is a
  Windows voice assistant that uses it for conversation instead of
  any cloud API.

  What might interest this sub specifically:
  - Intent classifier (keyword/regex, no LLM call) routes messages to
    either Ollama (fast, local) or an optional Claude cloud fallback
    for complex queries
  - RAG layer (sentence-transformers + ChromaDB) for domain-specific
    knowledge, lazy-loaded on first use
  - Default model is qwen2.5:3b, configurable in config.yaml

  Source: https://github.com/sametgurtuna/SAM
  Demo: [YOUTUBE LINK]

  Curious what models people here are running for voice/assistant use
  cases — always looking to tune the default.
  ```

---

### Gün 14 (Salı) — YouTube Tutorial #1

**Yapılacaklar:**
- [ ] Kısa bir kurulum videosu çek: "Installing SAM in 5 Minutes"
- [ ] Yükle, açıklamaya GitHub linki ekle, pinned comment:
  ```
  ⭐ Star on GitHub if this was useful: https://github.com/sametgurtuna/SAM
  ```
- [ ] Twitter'da paylaş:
  ```
  New video: setting up SAM from zero in under 5 minutes 🎥
  [YOUTUBE LINK]
  ```

---

### Gün 15 (Çarşamba) — Reddit r/Python

**Yapılacaklar:**
- [ ] Başlık:
  ```
  SAM – a PyQt6 voice assistant, mostly sharing for the signals/slots architecture
  ```
- [ ] İçerik (kod kalitesine odaklan, satış dili kullanma — r/Python teknik derinlik ister):
  ```
  Not launching anything new, just sharing a project where I leaned
  hard into PyQt's signal/slot system to keep a fairly complex app
  (wake word listener, recorder, STT, LLM router, TTS, overlay UI)
  decoupled — no component calls another directly, everything goes
  through Qt signals back to a single controller.

  Also handled: streaming TTS that speaks mid-generation, a click-through
  overlay window, and a regex command router with two-step confirmation
  for destructive actions.

  Code: https://github.com/sametgurtuna/SAM
  Architecture doc: https://github.com/sametgurtuna/SAM/blob/main/docs/ARCHITECTURE.md

  Feedback on the architecture welcome — always curious how others
  structure similar multi-threaded PyQt apps.
  ```

---

### Gün 16 (Perşembe) — Awesome List PR'ları

**Yapılacaklar:**
- [ ] github.com/awesome-selfhosted/awesome-selfhosted reposuna git
- [ ] "Voice Assistants" veya en yakın kategoriyi bul, CONTRIBUTING.md'yi oku
- [ ] Fork → SAM'i doğru formatta ekle → PR aç:
  ```
  - [SAM](https://github.com/sametgurtuna/SAM) - Local, privacy-first
    Windows voice assistant powered by Ollama. `Python` `MIT`
  ```
- [ ] Aynısını `awesome-python`, `awesome-privacy` için de dene (her repo'nun kendi
  format kuralına uy)

**Bugün sosyal medya paylaşımı YOK — bu PR'lar kabul edilirse organik, kalıcı trafik
getirir.**

---

### Gün 17 (Cuma) — Blog Yazısı #2: Güvenlik

**Yapılacaklar:**
- [ ] Dev.to'da yeni yazı:

  **Başlık:** `Why Your Voice Assistant Should Never Be Able to Open a Terminal`

  **İskelet:**
  ```markdown
  Whisper (and other STT models) occasionally hallucinate short phrases
  from silence or background noise. Usually harmless — a stray word in
  a transcript. But what if that hallucinated phrase was "open command
  prompt"?

  [Gerçek örnek varsa buraya ekle — log'dan bir örnek]

  In SAM, cmd/powershell/wt/bash are hard-blocked in commands/system.py,
  regardless of how the request arrives — voice or typed text. Here's
  the actual guard: [kod parçası ekle]

  Destructive actions (shutdown, restart) are two-step by design too —
  they only arm, a separate "confirm" within a 30-second window executes.

  Full writeup on the pattern: [GitHub link to CLAUDE.md conventions section]
  ```
- [ ] Twitter'da paylaş:
  ```
  New post: why I hard-blocked shell access in SAM, even though it
  made the command router more annoying to write.

  [DEV.TO LINK]

  #Security #Python
  ```

**Hafta 3 sonu hedefi:** 200-250 GitHub star

---

## 📅 HAFTA 4 — Sürdürme + Topluluk

### Gün 18 (Pazartesi) — GitHub Discussions Aç

**Yapılacaklar:**
- [ ] Repo → Settings → Features → **Discussions**'ı etkinleştir
- [ ] 4 kategori oluştur: 💡 Ideas · 🙋 Q&A · 📣 Show and Tell · 📢 Announcements
- [ ] İlk postu sen at (boş bir yer boş kalmasın):
  ```
  Title: What custom commands have you added to SAM?

  Curious what people are building with the command router — CPU temp
  checks, custom Spotify playlists, smart home triggers? Drop a regex +
  handler snippet if you've got one, happy to feature the best ones in
  a future SHOWCASE.md.
  ```

---

### Gün 19 (Salı) — Reddit r/Privacy

**Yapılacaklar:**
- [ ] Başlık:
  ```
  Built a voice assistant that never sends audio to the cloud
  ```
- [ ] İçerik (bu subreddit'te privacy vurgusu her şeyden önce gelmeli):
  ```
  After reading one too many stories about voice assistant recordings
  being reviewed by human contractors, I built SAM — a Windows voice
  assistant where the only unprompted network call is to your own
  local Ollama server (localhost:11434).

  - Audio is processed in memory, never written to disk
  - No telemetry, no analytics, no phone-home
  - Cloud fallback (Claude) is fully opt-in, off by default
  - Fully open source so you can verify all of this yourself

  Code: https://github.com/sametgurtuna/SAM

  Not trying to sell anything — genuinely built this for myself and
  figured this sub would appreciate it. Happy to answer questions about
  what data (if any) touches the network.
  ```

---

### Gün 20 (Çarşamba) — Landing Page (GitHub Pages)

**Yapılacaklar:**
- [ ] Repo → Settings → Pages → Source: `main` branch, `/docs` klasörü
- [ ] Basit tek sayfalık bir `docs/index.html` oluştur (istersen bana ayrıca bunu
  hazırlamamı söyleyebilirsin — tek başına ayrı bir iş):
  - Hero: orb görseli + tek cümlelik value prop
  - "Download" ve "Star on GitHub" butonları
  - Demo videosu embed
  - Feature karşılaştırma tablosu (SAM vs Alexa vs Google Assistant)
- [ ] Yayınlandıktan sonra Twitter'da paylaş:
  ```
  SAM now has a proper landing page: [LANDING PAGE LINK]

  [GitHub link'i de ekle]
  ```

---

### Gün 21 (Perşembe) — YouTube Shorts Deneme

**Yapılacaklar:**
- [ ] 30 saniyelik dikey video kes (orb animasyonu + tek komut demo)
- [ ] YouTube Shorts + Twitter'a aynı anda yükle
- [ ] Başlık fikri: `"My voice assistant can't be tricked into opening a terminal 👀"`

---

### Gün 22 (Cuma) — Haftalık Değerlendirme

**Yapılacaklar:**
- [ ] GitHub Insights → Traffic sekmesine bak: hangi kaynak en çok star getirdi?
- [ ] Star sayısını not al (bir sonraki haftayla kıyaslamak için)
- [ ] Cevapsız kalan issue/yorum var mı kontrol et, hepsine yanıt ver
- [ ] Şu formatta kısa bir "hafta özeti" tweet'i at:
  ```
  Week 3 of building SAM in public: [X] stars, [Y] contributors,
  landed on r/SelfHosted and r/Privacy front pages.

  Biggest lesson: the demo video mattered more than any single post.

  [GitHub link]
  ```

---

### Gün 23-24 (Hafta Sonu) — Dinlenme + Küçük İyileştirmeler

**Yapılacaklar:**
- [ ] Gelen feedback'lerden en çok tekrarlanan 1-2 isteği küçük bir PR ile çöz
- [ ] Paylaşım yok, sadece bakım

---

## 📅 SON HAFTA — Pekiştirme

### Gün 25 (Pazartesi) — Reddit r/OpenSource

**Yapılacaklar:**
- [ ] Başlık:
  ```
  [Release] SAM - Open source voice assistant for Windows (privacy-first)
  ```
- [ ] İçerik: Hafta 2'deki r/SelfHosted metnini temel al ama "open source, katkıya açık"
  vurgusunu öne çıkar, "good first issue"lara link ver

---

### Gün 26 (Salı) — Podcast Pitch'leri Gönder

**Yapılacaklar:**
- [ ] 3 podcast'e mail at (The Changelog, Python Bytes, Self-Hosted Podcast — iletişim
  bilgilerini kendi sitelerinden bul)
- [ ] Şablon:
  ```
  Subject: Built a privacy-first voice assistant with Ollama

  Hi [Host name],

  I'm Samet, developer of SAM — a voice assistant that runs entirely
  locally (no cloud, Ollama-powered).

  Thought it might interest your audience because:
  - Privacy-first architecture (addresses the Alexa/Google concerns
    a lot of your listeners probably share)
  - Uses Ollama instead of any cloud LLM API
  - Hardened against a real failure mode: STT hallucinations that
    could otherwise trigger shell access

  Would you be interested in covering it?

  GitHub: https://github.com/sametgurtuna/SAM
  Demo: [YOUTUBE LINK]

  Best,
  Samet
  ```

---

### Gün 27 (Çarşamba) — Blog Yazısı #3: Retrospektif

**Yapılacaklar:**
- [ ] Dev.to'da:

  **Başlık:** `30 Days of Building SAM in Public — What Worked and What Didn't`

  **İskelet:**
  ```markdown
  A month ago I launched SAM on Product Hunt and Hacker News. Here's
  the honest breakdown of what actually moved the needle.

  ## The numbers
  [Gerçek rakamları yaz: star sayısı, hangi platform ne kadar getirdi]

  ## What worked
  [En çok trafiği getiren platform/post — muhtemelen HN veya PH]

  ## What didn't
  [Beklediğin ama tutmayan bir kanal — dürüst ol]

  ## What's next
  [ROADMAP.md'den 2-3 madde]

  If you're building something local-first, happy to compare notes.
  ```

---

### Gün 28 (Perşembe) — Aylık Changelog + Duyuru

**Yapılacaklar:**
- [ ] `CHANGELOG.md`'yi güncelle, bu ay eklenen her şeyi listele
- [ ] Katkı sağlayan olduysa isimlerini an (shoutout)
- [ ] Reddit + Twitter'da kısa duyuru:
  ```
  Monthly SAM update: [en önemli 2-3 değişiklik].
  Thanks to everyone who starred, opened issues, or sent feedback this
  month 🙏

  [GitHub link]
  ```

---

### Gün 29 (Cuma) — Product Hunt "Launch Update"

**Yapılacaklar:**
- [ ] Product Hunt sayfana bir "update" postu ekle (yeni özellik, yeni sayı — hatırlatma
  amaçlı, yeni trafik çeker)

---

### Gün 30 (Cumartesi) — Ay Sonu Değerlendirme

**Yapılacaklar:**
- [ ] Final metrikleri kaydet: star, fork, download, video görüntülenme
- [ ] Hangi 3 aksiyon en çok işe yaradı, hangi 3'ü işe yaramadı — bunu bir sonraki
  30 günlük döngü için not al
- [ ] Kendine bir teşekkür et — 30 gün boyunca tutarlı paylaşım yapmak zor iştir 🎉

---

## 🎯 30 Gün Sonunda Beklenen Sonuç

| Metrik | Gerçekçi Hedef |
|---|---|
| GitHub Stars | 150-300 |
| Contributors | 3-8 |
| YouTube video görüntülenme | 500-2000 |
| Product Hunt upvote | 100-300 |

Bu rakamlar viral bir patlama değil, **istikrarlı ve sürdürülebilir büyüme** hedefliyor —
sahte upvote/star almadan, gerçek kullanıcı tabanı kurarak.

---

## 🚨 Genel Kurallar (Her Gün Geçerli)

1. **Aynı gün 2'den fazla platforma post atma** — hepsi spam gibi görünür.
2. **Her post'tan sonra ilk 2 saati yorumlara ayır** — motorun en önemli parçası bu.
3. **"Star my repo" deme, değer ver** — her post bir şey öğretsin veya bir problemi
   anlatsın, sonunda link dursun.
4. **Bir gün atlarsan panik yapma** — bir sonraki güne geç, sıralamayı bozmadan devam et.
5. **Gerçek olmayan hiçbir metrik satın alma** (star, upvote, follower) — hem platformlar
   tespit eder hem de gerçek büyümeyi baltalar.

---

## 📌 Hızlı Referans — Bu Ay Hangi Gün Nerede Paylaşım Var?

| Gün | Platform | Konu |
|---|---|---|
| 8 | Product Hunt | Launch |
| 9 | Dev.to + Twitter | Streaming TTS yazısı |
| 10 | Hacker News | Show HN |
| 11 | Reddit r/SelfHosted | Genel tanıtım |
| 12 | Twitter | Mimari thread |
| 13 | Reddit r/LocalLLaMA | Ollama entegrasyonu |
| 14 | YouTube + Twitter | Kurulum videosu |
| 15 | Reddit r/Python | Kod mimarisi |
| 16 | GitHub (PR) | Awesome list'ler |
| 17 | Dev.to + Twitter | Güvenlik yazısı |
| 19 | Reddit r/Privacy | Privacy vurgusu |
| 20 | GitHub Pages + Twitter | Landing page |
| 21 | YouTube Shorts + Twitter | Kısa video |
| 22 | Twitter | Haftalık özet |
| 25 | Reddit r/OpenSource | Katkıya açık vurgu |
| 26 | E-posta | Podcast pitch |
| 27 | Dev.to | Retrospektif |
| 28 | Reddit + Twitter | Aylık changelog |
| 29 | Product Hunt | Update postu |

---

*Son güncelleme: 2026-08-12*
