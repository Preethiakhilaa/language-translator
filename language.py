"""
TranslateX — a free, single-file Flask translation website.

Everything (backend, HTML, CSS, JavaScript) lives in this one file on purpose,
so the whole project can be run with a single command: `python app.py`.

Free-to-run by design:
- Translation uses `deep-translator`'s GoogleTranslator, which calls Google
  Translate's public web endpoint. It requires no API key and costs nothing,
  but it is an unofficial integration, so Google may rate-limit it under very
  heavy traffic (see the note in the deployment instructions).
- Voice output primarily uses the browser's built-in Web Speech API
  (completely free, no server cost, works instantly). An optional
  "Download MP3" button uses gTTS (also free, unofficial, same rate-limit
  caveat as above) and streams audio from memory — no files are written to
  disk, which keeps it safe under concurrent public users.
"""

import io
import logging
import os

from flask import Flask, jsonify, render_template_string, request, send_file
from deep_translator import GoogleTranslator
from deep_translator.exceptions import LanguageNotSupportedException
from gtts import gTTS

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("translatex")

MAX_TEXT_LENGTH = 5000

# Languages supported by the app: code -> display name.
LANGUAGES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh-CN": "Chinese (Simplified)",
    "ja": "Japanese",
}

# gTTS expects lowercase codes for a couple of languages that deep-translator
# writes differently.
TTS_LANG_MAP = {"zh-CN": "zh-CN", "zh-cn": "zh-CN"}


def translate_text(text, source, target):
    """Translate text using deep-translator's free Google Translate wrapper."""
    translator = GoogleTranslator(source=source, target=target)
    return translator.translate(text)


# ---------------------------------------------------------------------------
# HTML / CSS / JS — all inline, rendered with render_template_string.
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TranslateX — Free Instant Translation for Everyone</title>
<meta name="description" content="Translate text between 11 languages instantly. Free, no sign-up, works on any device.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>
:root{
  --font-display:'Lexend','Inter',sans-serif;
  --font-body:'Inter',sans-serif;
  --font-mono:'IBM Plex Mono',monospace;

  --bg:#F6F7FC;
  --bg-alt:#EDEFFB;
  --surface:#FFFFFF;
  --surface-soft:#F1F2FA;
  --border:#E2E4F1;
  --ink:#14162B;
  --ink-muted:#5B5F79;

  --primary:#3B5BFC;
  --primary-strong:#2A44D6;
  --primary-soft:#E7ECFF;
  --jade:#12A585;
  --jade-soft:#DCF7F0;
  --amber:#F5A623;
  --danger:#E23E3E;
  --danger-soft:#FBE7E6;

  --shadow-sm:0 1px 2px rgba(20,22,43,.06);
  --shadow-md:0 10px 30px rgba(20,22,43,.08);
  --shadow-lg:0 24px 60px rgba(20,22,43,.16);
  --radius-sm:10px;
  --radius-md:16px;
  --radius-lg:26px;
  --ease:cubic-bezier(.4,0,.2,1);
}
html[data-theme="dark"]{
  --bg:#0A0D1F;
  --bg-alt:#0E1226;
  --surface:#121631;
  --surface-soft:#181D3C;
  --border:#262C52;
  --ink:#EDEFFC;
  --ink-muted:#9AA0C4;
  --primary:#6E86FF;
  --primary-strong:#8A9EFF;
  --primary-soft:#1D2450;
  --jade:#2BD9B4;
  --jade-soft:#0F332C;
  --amber:#F5BA52;
  --danger:#FF6B63;
  --danger-soft:#391A1A;
  --shadow-sm:0 1px 2px rgba(0,0,0,.4);
  --shadow-md:0 10px 30px rgba(0,0,0,.45);
  --shadow-lg:0 24px 60px rgba(0,0,0,.6);
}
*{box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{
  margin:0;font-family:var(--font-body);background:var(--bg);color:var(--ink);
  transition:background .25s var(--ease),color .25s var(--ease);
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3{font-family:var(--font-display);margin:0;letter-spacing:-0.01em;}
p{line-height:1.6;}
a{color:inherit;}
button{font-family:inherit;}
::selection{background:var(--primary-soft);color:var(--primary-strong);}
:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;}
.container{max-width:1120px;margin:0 auto;padding:0 24px;}
.eyebrow{
  display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:600;
  color:var(--primary-strong);background:var(--primary-soft);padding:6px 14px;border-radius:999px;
}
.reveal{opacity:0;transform:translateY(16px);transition:opacity .6s var(--ease),transform .6s var(--ease);}
.reveal.is-visible{opacity:1;transform:translateY(0);}

/* ---------- Header / Nav ---------- */
.site-header{
  position:sticky;top:0;z-index:40;
  background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:blur(12px);
  border-bottom:1px solid var(--border);
}
.nav-inner{display:flex;align-items:center;justify-content:space-between;padding:14px 0;}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;}
.brand-mark{
  width:38px;height:38px;border-radius:11px;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,var(--primary),var(--jade));color:#fff;font-size:16px;
  box-shadow:var(--shadow-sm);
}
.brand-name{font-family:var(--font-display);font-weight:700;font-size:19px;color:var(--ink);}
.nav-links{display:flex;align-items:center;gap:4px;}
.nav-link{
  padding:9px 14px;border-radius:999px;font-size:14px;font-weight:600;color:var(--ink-muted);
  text-decoration:none;transition:background .2s var(--ease),color .2s var(--ease);
}
.nav-link:hover{background:var(--surface-soft);color:var(--ink);}
.nav-cta{
  padding:10px 18px;border-radius:999px;background:var(--primary);color:#fff;font-weight:700;font-size:14px;
  text-decoration:none;box-shadow:0 8px 20px rgba(59,91,252,.28);transition:transform .15s var(--ease);
}
.nav-cta:hover{transform:translateY(-1px);}
.theme-toggle{
  width:38px;height:38px;border-radius:999px;border:1px solid var(--border);background:var(--surface);
  color:var(--ink);cursor:pointer;display:flex;align-items:center;justify-content:center;margin-left:6px;
  transition:transform .2s var(--ease);
}
.theme-toggle:hover{transform:rotate(15deg);}
.nav-toggle{display:none;width:38px;height:38px;border-radius:10px;border:1px solid var(--border);background:var(--surface);color:var(--ink);cursor:pointer;}
.mobile-nav{display:none;flex-direction:column;gap:4px;padding:12px 0 16px;border-top:1px solid var(--border);}
.mobile-nav.open{display:flex;}

/* ---------- Hero ---------- */
.hero{position:relative;padding:64px 0 40px;overflow:hidden;}
.hero-glow{
  position:absolute;inset:-160px 0 auto 0;height:520px;pointer-events:none;z-index:0;
  background:
    radial-gradient(480px 280px at 18% 30%,rgba(59,91,252,.20),transparent 65%),
    radial-gradient(420px 260px at 82% 20%,rgba(18,165,133,.18),transparent 65%);
  filter:blur(6px);
}
.hero-inner{position:relative;z-index:1;text-align:center;max-width:720px;margin:0 auto;}
.hero h1{font-size:clamp(32px,5vw,52px);font-weight:800;margin:18px 0 14px;line-height:1.1;}
.hero h1 .accent{color:var(--primary);}
.hero p.lede{color:var(--ink-muted);font-size:17px;max-width:560px;margin:0 auto;}

/* ---------- Translator tool ---------- */
.tool-wrap{max-width:920px;margin:40px auto 0;position:relative;z-index:1;}
.lang-bar{display:flex;align-items:center;justify-content:center;gap:14px;margin-bottom:16px;flex-wrap:wrap;}
.lang-select{
  flex:1;min-width:170px;max-width:320px;padding:12px 16px;border-radius:var(--radius-sm);
  border:1px solid var(--border);background:var(--surface);color:var(--ink);font-size:14.5px;font-weight:600;
  cursor:pointer;box-shadow:var(--shadow-sm);appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%235B5F79'%3E%3Cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center;background-size:16px;padding-right:36px;
}
.swap-btn{
  flex:0 0 auto;width:46px;height:46px;border-radius:999px;border:1px solid var(--border);
  background:var(--surface);color:var(--primary);cursor:pointer;display:flex;align-items:center;justify-content:center;
  box-shadow:var(--shadow-sm);transition:transform .3s var(--ease),background .2s var(--ease);
}
.swap-btn:hover{background:var(--primary-soft);}
.swap-btn.spin{transform:rotate(180deg);}

.panels{display:grid;grid-template-columns:1fr 1fr;gap:18px;position:relative;}
.flow-line{
  position:absolute;left:50%;top:50%;width:2px;height:0;background:transparent;pointer-events:none;
}
.panel{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);
  box-shadow:var(--shadow-md);display:flex;flex-direction:column;min-height:230px;overflow:hidden;
  transition:box-shadow .25s var(--ease);
}
.panel.is-translating{box-shadow:0 0 0 2px var(--primary-soft),var(--shadow-md);}
.panel-body{flex:1;padding:20px;position:relative;}
textarea,.output-box{
  width:100%;height:100%;min-height:160px;border:none;resize:none;background:transparent;color:var(--ink);
  font-size:16px;line-height:1.65;font-family:var(--font-body);
}
textarea:focus{outline:none;}
textarea::placeholder{color:var(--ink-muted);}
.output-box{white-space:pre-wrap;word-break:break-word;}
.placeholder-text{color:var(--ink-muted);}
.panel-footer{
  display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 16px;
  border-top:1px solid var(--border);background:var(--surface-soft);
}
.panel-actions{display:flex;gap:4px;}
.icon-btn{
  width:38px;height:38px;border-radius:var(--radius-sm);border:1px solid transparent;background:transparent;
  color:var(--ink-muted);cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:background .18s var(--ease),color .18s var(--ease),transform .12s var(--ease);position:relative;
}
.icon-btn:hover:not(:disabled){background:var(--surface);color:var(--primary);border-color:var(--border);}
.icon-btn:active:not(:disabled){transform:scale(.9);}
.icon-btn:disabled{opacity:.35;cursor:not-allowed;}
.char-counter{font-size:12px;color:var(--ink-muted);font-family:var(--font-mono);white-space:nowrap;}

.loader{position:absolute;inset:0;display:none;align-items:center;justify-content:center;gap:9px;background:var(--surface);color:var(--ink-muted);font-size:14px;}
.loader .dot{width:8px;height:8px;border-radius:50%;background:var(--primary);animation:bounce 1s infinite ease-in-out;}
.loader .dot:nth-child(2){animation-delay:.15s;}
.loader .dot:nth-child(3){animation-delay:.3s;}
@keyframes bounce{0%,80%,100%{transform:scale(.6);opacity:.5;}40%{transform:scale(1);opacity:1;}}

.translate-row{display:flex;justify-content:center;margin-top:22px;}
.translate-btn{
  position:relative;overflow:hidden;padding:15px 36px;border-radius:999px;border:none;
  background:linear-gradient(135deg,var(--primary),var(--primary-strong));color:#fff;font-size:16px;font-weight:700;
  cursor:pointer;display:flex;align-items:center;gap:10px;box-shadow:0 12px 26px rgba(59,91,252,.32);
  transition:transform .15s var(--ease),box-shadow .25s var(--ease);
}
.translate-btn:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 16px 32px rgba(59,91,252,.4);}
.translate-btn:disabled{opacity:.72;cursor:progress;}
.translate-btn kbd{background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.3);border-radius:6px;padding:2px 6px;font-size:11px;}
.ripple{position:absolute;border-radius:50%;background:rgba(255,255,255,.5);transform:scale(0);animation:rippleAnim .5s ease-out;pointer-events:none;}
@keyframes rippleAnim{to{transform:scale(3);opacity:0;}}

/* Recent translations */
.recent-wrap{max-width:920px;margin:22px auto 0;}
.recent-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-muted);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;}
.recent-clear{background:none;border:none;color:var(--primary);font-size:12px;font-weight:600;cursor:pointer;}
.recent-list{display:flex;flex-wrap:wrap;gap:8px;}
.recent-chip{
  padding:8px 14px;border-radius:999px;border:1px solid var(--border);background:var(--surface);
  font-size:13px;cursor:pointer;color:var(--ink-muted);transition:background .18s var(--ease),color .18s var(--ease);
  max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.recent-chip:hover{background:var(--primary-soft);color:var(--primary-strong);}

/* ---------- Sections ---------- */
.section{padding:76px 0;}
.section-alt{background:var(--bg-alt);}
.section-head{text-align:center;max-width:560px;margin:0 auto 44px;}
.section-head h2{font-size:clamp(24px,3.4vw,34px);margin:12px 0 10px;}
.section-head p{color:var(--ink-muted);}

.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;}
.step-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:28px;box-shadow:var(--shadow-sm);}
.step-num{font-family:var(--font-mono);font-size:13px;color:var(--primary);font-weight:600;margin-bottom:14px;}
.step-card h3{font-size:18px;margin-bottom:8px;}
.step-card p{color:var(--ink-muted);font-size:14.5px;margin:0;}

.feature-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;}
.feature-card{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:26px;
  box-shadow:var(--shadow-sm);transition:transform .25s var(--ease),box-shadow .25s var(--ease);
}
.feature-card:hover{transform:translateY(-4px);box-shadow:var(--shadow-md);}
.feature-icon{
  width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;
  background:var(--primary-soft);color:var(--primary-strong);font-size:18px;margin-bottom:16px;
}
.feature-card h3{font-size:16px;margin-bottom:6px;}
.feature-card p{color:var(--ink-muted);font-size:14px;margin:0;}

.lang-cloud{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;}
.lang-pill{
  padding:9px 16px;border-radius:999px;border:1px solid var(--border);background:var(--surface);
  font-size:13.5px;font-weight:600;color:var(--ink-muted);display:flex;align-items:center;gap:7px;
}
.lang-pill .code{font-family:var(--font-mono);font-size:11px;color:var(--jade);}

.faq-list{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:12px;}
.faq-item{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);padding:6px 20px;box-shadow:var(--shadow-sm);}
.faq-item summary{cursor:pointer;padding:16px 0;font-weight:600;font-size:15px;list-style:none;display:flex;justify-content:space-between;align-items:center;}
.faq-item summary::-webkit-details-marker{display:none;}
.faq-item summary::after{content:'+';font-size:20px;color:var(--primary);transition:transform .2s var(--ease);}
.faq-item[open] summary::after{transform:rotate(45deg);}
.faq-item p{color:var(--ink-muted);margin:0 0 16px;font-size:14.5px;}

/* ---------- Footer ---------- */
.site-footer{border-top:1px solid var(--border);background:var(--surface);padding:44px 0 24px;}
.footer-grid{display:grid;grid-template-columns:2fr 1fr;gap:24px;margin-bottom:24px;}
.footer-brand p{color:var(--ink-muted);font-size:14px;margin:10px 0 0;max-width:320px;}
.footer-langs h4{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-muted);margin-bottom:10px;}
.footer-langs p{color:var(--ink-muted);font-size:13.5px;line-height:1.8;margin:0;}
.footer-bottom{border-top:1px solid var(--border);padding-top:18px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;color:var(--ink-muted);font-size:13px;}

/* ---------- Toasts ---------- */
.toast-stack{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;gap:10px;z-index:100;width:min(90vw,380px);}
.toast{display:flex;align-items:center;gap:10px;padding:13px 16px;border-radius:var(--radius-sm);background:var(--surface);border:1px solid var(--border);box-shadow:var(--shadow-lg);font-size:14px;animation:toastIn .22s var(--ease);}
.toast.success i{color:var(--jade);}
.toast.error i{color:var(--danger);}
@keyframes toastIn{from{opacity:0;transform:translateY(12px);}to{opacity:1;transform:translateY(0);}}

/* ---------- Responsive ---------- */
@media (max-width:900px){
  .feature-grid{grid-template-columns:repeat(2,1fr);}
  .steps{grid-template-columns:1fr;}
}
@media (max-width:760px){
  .nav-links{display:none;}
  .nav-toggle{display:flex;align-items:center;justify-content:center;}
  .panels{grid-template-columns:1fr;}
  .lang-select{max-width:none;}
  .feature-grid{grid-template-columns:1fr;}
  .footer-grid{grid-template-columns:1fr;}
}
@media (prefers-reduced-motion:reduce){
  *{animation-duration:.01ms !important;animation-iteration-count:1 !important;transition-duration:.01ms !important;}
  html{scroll-behavior:auto;}
}
</style>
</head>
<body>

<header class="site-header">
  <div class="container nav-inner">
    <a href="#top" class="brand">
      <span class="brand-mark"><i class="fa-solid fa-language"></i></span>
      <span class="brand-name">TranslateX</span>
    </a>
    <nav class="nav-links" aria-label="Primary">
      <a class="nav-link" href="#top">Translate</a>
      <a class="nav-link" href="#how-it-works">How it works</a>
      <a class="nav-link" href="#features">Features</a>
      <a class="nav-link" href="#faq">FAQ</a>
      <a class="nav-cta" href="#top">Try it free</a>
      <button class="theme-toggle" id="themeToggle" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">
        <i class="fa-solid fa-moon"></i>
      </button>
    </nav>
    <div style="display:flex;align-items:center;gap:8px;">
      <button class="theme-toggle" id="themeToggleMobile" type="button" aria-label="Toggle dark mode" title="Toggle dark mode" style="display:none;">
        <i class="fa-solid fa-moon"></i>
      </button>
      <button class="nav-toggle" id="navToggle" type="button" aria-label="Open menu" aria-expanded="false">
        <i class="fa-solid fa-bars"></i>
      </button>
    </div>
  </div>
  <div class="container mobile-nav" id="mobileNav">
    <a class="nav-link" href="#top">Translate</a>
    <a class="nav-link" href="#how-it-works">How it works</a>
    <a class="nav-link" href="#features">Features</a>
    <a class="nav-link" href="#faq">FAQ</a>
  </div>
</header>

<main id="top">

  <!-- ================= HERO + TOOL ================= -->
  <section class="hero">
    <div class="hero-glow" aria-hidden="true"></div>
    <div class="container hero-inner">
      <span class="eyebrow"><i class="fa-solid fa-sparkles"></i> Free forever &middot; No sign-up required</span>
      <h1>Speak any language,<br><span class="accent">instantly.</span></h1>
      <p class="lede">Translate text between 11 languages right in your browser. Type, listen, and share — no account, no cost, no limits.</p>
    </div>

    <div class="container">
      <div class="tool-wrap">
        <div class="lang-bar">
          <select id="sourceLang" class="lang-select" aria-label="Source language">
            {% for code, name in languages.items() %}
              <option value="{{ code }}" {% if code == 'en' %}selected{% endif %}>{{ name }}</option>
            {% endfor %}
          </select>

          <button class="swap-btn" id="swapBtn" type="button" title="Swap languages" aria-label="Swap languages">
            <i class="fa-solid fa-right-left"></i>
          </button>

          <select id="targetLang" class="lang-select" aria-label="Target language">
            {% for code, name in languages.items() %}
              <option value="{{ code }}" {% if code == 'ta' %}selected{% endif %}>{{ name }}</option>
            {% endfor %}
          </select>
        </div>

        <div class="panels">
          <div class="panel" id="sourcePanel">
            <div class="panel-body">
              <textarea id="sourceText" placeholder="Type or paste text to translate..." maxlength="5000" aria-label="Text to translate"></textarea>
            </div>
            <div class="panel-footer">
              <div class="panel-actions">
                <button class="icon-btn" id="clearBtn" type="button" title="Clear text" aria-label="Clear text"><i class="fa-solid fa-eraser"></i></button>
                <button class="icon-btn" id="copySourceBtn" type="button" title="Copy source text" aria-label="Copy source text"><i class="fa-regular fa-copy"></i></button>
              </div>
              <span class="char-counter"><span id="charCount">0</span>/5000</span>
            </div>
          </div>

          <div class="panel" id="targetPanel">
            <div class="panel-body">
              <div class="output-box" id="outputText"><span class="placeholder-text">Your translation will appear here.</span></div>
              <div class="loader" id="loader">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                <span>Translating…</span>
              </div>
            </div>
            <div class="panel-footer">
              <div class="panel-actions">
                <button class="icon-btn" id="speakBtn" type="button" title="Listen" aria-label="Listen to translation" disabled><i class="fa-solid fa-volume-high"></i></button>
                <button class="icon-btn" id="downloadBtn" type="button" title="Download MP3" aria-label="Download audio" disabled><i class="fa-solid fa-download"></i></button>
                <button class="icon-btn" id="copyTargetBtn" type="button" title="Copy translation" aria-label="Copy translation" disabled><i class="fa-regular fa-copy"></i></button>
              </div>
            </div>
          </div>
        </div>

        <div class="translate-row">
          <button class="translate-btn" id="translateBtn" type="button">
            <span>Translate</span><kbd>Ctrl + Enter</kbd>
          </button>
        </div>
      </div>

      <div class="recent-wrap" id="recentWrap" style="display:none;">
        <div class="recent-title">
          <span>Recent</span>
          <button class="recent-clear" id="recentClearBtn" type="button">Clear</button>
        </div>
        <div class="recent-list" id="recentList"></div>
      </div>
    </div>
  </section>

  <!-- ================= HOW IT WORKS ================= -->
  <section class="section" id="how-it-works">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">How it works</span>
        <h2>Three steps. Zero friction.</h2>
        <p>No installs, no accounts — just open the page and start translating.</p>
      </div>
      <div class="steps">
        <div class="step-card reveal">
          <div class="step-num">01</div>
          <h3>Type or paste your text</h3>
          <p>Enter up to 5,000 characters in the source panel — any of the 11 supported languages.</p>
        </div>
        <div class="step-card reveal">
          <div class="step-num">02</div>
          <h3>Pick your languages</h3>
          <p>Choose a source and target language, or swap them instantly with one click.</p>
        </div>
        <div class="step-card reveal">
          <div class="step-num">03</div>
          <h3>Read, listen, or share</h3>
          <p>Get your translation instantly, then copy it, hear it spoken aloud, or download the audio.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ================= FEATURES ================= -->
  <section class="section section-alt" id="features">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">Why TranslateX</span>
        <h2>Built to be simple, fast, and free</h2>
        <p>No hidden costs, no premium tier — every feature is available to everyone.</p>
      </div>
      <div class="feature-grid">
        <div class="feature-card reveal">
          <div class="feature-icon"><i class="fa-solid fa-gift"></i></div>
          <h3>100% free</h3>
          <p>No subscriptions, no paywalls, no usage limits that require payment.</p>
        </div>
        <div class="feature-card reveal">
          <div class="feature-icon"><i class="fa-solid fa-microphone"></i></div>
          <h3>Voice in and out</h3>
          <p>Listen to any translation out loud, or download it as an MP3 file.</p>
        </div>
        <div class="feature-card reveal">
          <div class="feature-icon"><i class="fa-solid fa-lock"></i></div>
          <h3>No account needed</h3>
          <p>Nothing is stored on our servers. Your recent translations stay only in your browser.</p>
        </div>
        <div class="feature-card reveal">
          <div class="feature-icon"><i class="fa-solid fa-mobile-screen"></i></div>
          <h3>Works everywhere</h3>
          <p>A responsive layout that feels right at home on phones, tablets, and desktops.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ================= LANGUAGES ================= -->
  <section class="section" id="languages">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">Supported languages</span>
        <h2>Translate between 11 languages</h2>
      </div>
      <div class="lang-cloud reveal">
        {% for code, name in languages.items() %}
          <span class="lang-pill">{{ name }} <span class="code">{{ code }}</span></span>
        {% endfor %}
      </div>
    </div>
  </section>

  <!-- ================= FAQ ================= -->
  <section class="section section-alt" id="faq">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">FAQ</span>
        <h2>Good to know</h2>
      </div>
      <div class="faq-list reveal">
        <details class="faq-item">
          <summary>Is TranslateX really free to use?</summary>
          <p>Yes. Every feature — translation, voice playback, and audio download — is free for everyone, with no account or payment required.</p>
        </details>
        <details class="faq-item">
          <summary>Do I need to create an account?</summary>
          <p>No. Just open the page and start translating. Your recent translations are saved only in your own browser, not on a server.</p>
        </details>
        <details class="faq-item">
          <summary>Is my text stored anywhere?</summary>
          <p>No. Text is sent to the translation service only to produce your result and is not saved by this application.</p>
        </details>
      </div>
    </div>
  </section>

</main>

<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <span class="brand-name">TranslateX</span>
        <p>Fast, simple, and free translation for everyone — no sign-up, no cost, no catch.</p>
      </div>
      <div class="footer-langs">
        <h4>Supported languages</h4>
        <p>{{ languages.values() | join(', ') }}</p>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; <span id="footerYear"></span> TranslateX. All rights reserved.</span>
      <span>Made for everyone, everywhere.</span>
    </div>
  </div>
</footer>

<div class="toast-stack" id="toastStack"></div>
<audio id="audioPlayer" style="display:none;"></audio>

<script>
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const RECENT_KEY = "translatex_recent";
  const THEME_KEY = "translatex_theme";

  /* ---------------- Theme ---------------- */
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const icon = theme === "dark" ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
    $("themeToggle").innerHTML = icon;
    $("themeToggleMobile").innerHTML = icon;
    localStorage.setItem(THEME_KEY, theme);
  }
  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    const preferred = saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    applyTheme(preferred);
  }
  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "dark" ? "light" : "dark");
  }
  $("themeToggle").addEventListener("click", toggleTheme);
  $("themeToggleMobile").addEventListener("click", toggleTheme);

  /* ---------------- Mobile nav ---------------- */
  const navToggle = $("navToggle");
  const mobileNav = $("mobileNav");
  const themeToggleMobile = $("themeToggleMobile");
  function syncMobileControls() {
    const isMobile = window.innerWidth <= 760;
    themeToggleMobile.style.display = isMobile ? "flex" : "none";
  }
  navToggle.addEventListener("click", () => {
    const open = mobileNav.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(open));
    navToggle.innerHTML = open ? '<i class="fa-solid fa-xmark"></i>' : '<i class="fa-solid fa-bars"></i>';
  });
  mobileNav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => {
    mobileNav.classList.remove("open");
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.innerHTML = '<i class="fa-solid fa-bars"></i>';
  }));
  window.addEventListener("resize", syncMobileControls);
  syncMobileControls();

  /* ---------------- Scroll reveal ---------------- */
  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    revealEls.forEach((el) => observer.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-visible"));
  }

  /* ---------------- Toasts ---------------- */
  const toastStack = $("toastStack");
  function showToast(message, type) {
    const icons = { success: "fa-circle-check", error: "fa-circle-exclamation" };
    const toast = document.createElement("div");
    toast.className = "toast " + (type || "success");
    toast.innerHTML = '<i class="fa-solid ' + (icons[type] || icons.success) + '"></i><span></span>';
    toast.querySelector("span").textContent = message;
    toastStack.appendChild(toast);
    setTimeout(() => toast.remove(), 3200);
  }

  /* ---------------- Translator tool ---------------- */
  const sourceLang = $("sourceLang");
  const targetLang = $("targetLang");
  const swapBtn = $("swapBtn");
  const sourceText = $("sourceText");
  const outputText = $("outputText");
  const charCount = $("charCount");
  const clearBtn = $("clearBtn");
  const copySourceBtn = $("copySourceBtn");
  const copyTargetBtn = $("copyTargetBtn");
  const speakBtn = $("speakBtn");
  const downloadBtn = $("downloadBtn");
  const translateBtn = $("translateBtn");
  const loader = $("loader");
  const audioPlayer = $("audioPlayer");
  const sourcePanel = $("sourcePanel");
  const targetPanel = $("targetPanel");

  let lastTranslatedText = "";

  function ripple(e, btn) {
    const rect = btn.getBoundingClientRect();
    const circle = document.createElement("span");
    const size = Math.max(rect.width, rect.height);
    circle.className = "ripple";
    circle.style.width = circle.style.height = size + "px";
    circle.style.left = (e.clientX - rect.left - size / 2) + "px";
    circle.style.top = (e.clientY - rect.top - size / 2) + "px";
    btn.appendChild(circle);
    setTimeout(() => circle.remove(), 500);
  }

  sourceText.addEventListener("input", () => {
    charCount.textContent = sourceText.value.length;
  });

  clearBtn.addEventListener("click", () => {
    sourceText.value = "";
    charCount.textContent = "0";
    sourceText.focus();
  });

  copySourceBtn.addEventListener("click", async () => {
    if (!sourceText.value) { showToast("Nothing to copy.", "error"); return; }
    await navigator.clipboard.writeText(sourceText.value);
    showToast("Source text copied.", "success");
  });

  copyTargetBtn.addEventListener("click", async () => {
    if (!lastTranslatedText) { showToast("Nothing to copy.", "error"); return; }
    await navigator.clipboard.writeText(lastTranslatedText);
    showToast("Translation copied.", "success");
  });

  swapBtn.addEventListener("click", () => {
    const tmp = sourceLang.value;
    sourceLang.value = targetLang.value;
    targetLang.value = tmp;

    const carryOver = lastTranslatedText;
    sourceText.value = carryOver || "";
    charCount.textContent = sourceText.value.length;

    outputText.innerHTML = '<span class="placeholder-text">Your translation will appear here.</span>';
    lastTranslatedText = "";
    copyTargetBtn.disabled = true;
    speakBtn.disabled = true;
    downloadBtn.disabled = true;

    swapBtn.classList.add("spin");
    setTimeout(() => swapBtn.classList.remove("spin"), 300);
  });

  function resetOutputButtons() {
    copyTargetBtn.disabled = true;
    speakBtn.disabled = true;
    downloadBtn.disabled = true;
  }

  async function translate() {
    const text = sourceText.value.trim();
    if (!text) {
      showToast("Please enter some text to translate.", "error");
      sourceText.focus();
      return;
    }

    translateBtn.disabled = true;
    loader.style.display = "flex";
    outputText.innerHTML = "";
    sourcePanel.classList.add("is-translating");
    targetPanel.classList.add("is-translating");
    resetOutputButtons();

    try {
      const response = await fetch("/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          source_language: sourceLang.value,
          target_language: targetLang.value
        })
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || "Translation failed.");
      }

      lastTranslatedText = data.translated_text;
      outputText.textContent = lastTranslatedText;
      copyTargetBtn.disabled = false;
      speakBtn.disabled = false;
      downloadBtn.disabled = false;

      saveRecent({
        sourceText: text,
        translatedText: lastTranslatedText,
        sourceLang: sourceLang.value,
        targetLang: targetLang.value
      });
    } catch (err) {
      outputText.innerHTML = '<span class="placeholder-text">Your translation will appear here.</span>';
      showToast(err.message || "Network error. Please try again.", "error");
    } finally {
      translateBtn.disabled = false;
      loader.style.display = "none";
      sourcePanel.classList.remove("is-translating");
      targetPanel.classList.remove("is-translating");
    }
  }

  translateBtn.addEventListener("click", (e) => { ripple(e, translateBtn); translate(); });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      translate();
    }
  });

  speakBtn.addEventListener("click", () => {
    if (!lastTranslatedText || !window.speechSynthesis) {
      if (!window.speechSynthesis) showToast("Voice playback isn't supported in this browser.", "error");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(lastTranslatedText);
    utterance.lang = targetLang.value;
    const voices = window.speechSynthesis.getVoices();
    const match = voices.find((v) => v.lang === targetLang.value) || voices.find((v) => v.lang.startsWith(targetLang.value.split("-")[0]));
    if (match) utterance.voice = match;
    window.speechSynthesis.speak(utterance);
  });

  downloadBtn.addEventListener("click", async () => {
    if (!lastTranslatedText) return;
    downloadBtn.disabled = true;
    try {
      const response = await fetch("/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: lastTranslatedText, language: targetLang.value })
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Could not generate audio.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "translatex-audio.mp3";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast("Audio downloaded.", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      downloadBtn.disabled = false;
    }
  });

  /* ---------------- Recent translations (localStorage only) ---------------- */
  const recentWrap = $("recentWrap");
  const recentList = $("recentList");
  const recentClearBtn = $("recentClearBtn");

  function readRecent() {
    try {
      return JSON.parse(localStorage.getItem(RECENT_KEY)) || [];
    } catch { return []; }
  }
  function writeRecent(list) {
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch {}
  }
  function saveRecent(entry) {
    const list = readRecent().filter((e) => e.sourceText !== entry.sourceText || e.targetLang !== entry.targetLang);
    list.unshift(entry);
    writeRecent(list.slice(0, 5));
    renderRecent();
  }
  function renderRecent() {
    const list = readRecent();
    recentWrap.style.display = list.length ? "block" : "none";
    recentList.innerHTML = "";
    list.forEach((entry) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "recent-chip";
      chip.title = entry.sourceText;
      chip.textContent = entry.sourceText.length > 40 ? entry.sourceText.slice(0, 40) + "…" : entry.sourceText;
      chip.addEventListener("click", () => {
        sourceLang.value = entry.sourceLang;
        targetLang.value = entry.targetLang;
        sourceText.value = entry.sourceText;
        charCount.textContent = sourceText.value.length;
        document.getElementById("top").scrollIntoView({ behavior: "smooth" });
        translate();
      });
      recentList.appendChild(chip);
    });
  }
  recentClearBtn.addEventListener("click", () => {
    writeRecent([]);
    renderRecent();
  });

  /* ---------------- Init ---------------- */
  $("footerYear").textContent = new Date().getFullYear();
  initTheme();
  renderRecent();
})();
</script>
</body>
</html>
"""


@app.route("/")
def home():
    """Render the landing page with the embedded translation tool."""
    return render_template_string(HTML_TEMPLATE, languages=LANGUAGES)


@app.route("/translate", methods=["POST"])
def translate():
    """
    Translate text.
    Request JSON:  { "text": str, "source_language": str, "target_language": str }
    Response JSON: { "success": true, "translated_text": str }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing request data."}), 400

    text = (data.get("text") or "").strip()
    source_language = (data.get("source_language") or "en").strip()
    target_language = (data.get("target_language") or "").strip()

    if not text:
        return jsonify({"success": False, "error": "Please enter some text to translate."}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({"success": False, "error": f"Text is too long. Limit is {MAX_TEXT_LENGTH} characters."}), 400
    if target_language not in LANGUAGES:
        return jsonify({"success": False, "error": "Unsupported target language."}), 400
    if source_language not in LANGUAGES:
        return jsonify({"success": False, "error": "Unsupported source language."}), 400
    if source_language == target_language:
        return jsonify({"success": True, "translated_text": text})

    try:
        translated = translate_text(text, source_language, target_language)
        if not translated:
            raise ValueError("Empty translation result")
        return jsonify({"success": True, "translated_text": translated})
    except LanguageNotSupportedException:
        return jsonify({"success": False, "error": "One of the selected languages is not supported."}), 400
    except Exception:
        logger.exception("Translation failed")
        return jsonify({
            "success": False,
            "error": "Translation service is temporarily unavailable. Please try again in a moment."
        }), 502


@app.route("/speak", methods=["POST"])
def speak():
    """Generate a downloadable MP3 for the given text/language using gTTS, entirely in memory."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing request data."}), 400

    text = (data.get("text") or "").strip()
    language = (data.get("language") or "en").strip()

    if not text:
        return jsonify({"success": False, "error": "There is no text to convert to speech."}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({"success": False, "error": f"Text is too long. Limit is {MAX_TEXT_LENGTH} characters."}), 400

    tts_lang = TTS_LANG_MAP.get(language, language)

    try:
        audio_buffer = io.BytesIO()
        tts = gTTS(text=text, lang=tts_lang)
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return send_file(audio_buffer, mimetype="audio/mpeg", as_attachment=True, download_name="translatex-audio.mp3")
    except Exception:
        logger.exception("Text-to-speech failed")
        return jsonify({
            "success": False,
            "error": "Could not generate audio for this language right now."
        }), 502


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"success": False, "error": "Not found."}), 404


@app.errorhandler(500)
def server_error(_e):
    logger.exception("Unhandled server error")
    return jsonify({"success": False, "error": "Something went wrong on our end."}), 500


if __name__ == "__main__":
    # PORT is provided automatically by most hosting platforms (Render, Railway, etc.).
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
