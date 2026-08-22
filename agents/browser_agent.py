"""
UMAY Browser Agent (L4)
Playwright tabanli web otomasyon ajani.
Sitelere gider, form doldurur, analiz yapar, screenshot alir.
"""

import os
import sys
import time
import base64
from pathlib import Path
from datetime import datetime

CORE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core")
sys.path.insert(0, CORE)

from utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata
from utils.logger import log

AJAN_ADI = "browser_agent"
SCREENSHOT_DIR = Path(__file__).parent.parent / "logs" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class BrowserAgent:
    def __init__(self, gorunur: bool = True, yavas_mod: bool = False):
        """
        gorunur: True = tarayici gozukur, False = arka planda
        yavas_mod: True = her adimda yavas calisir (izlemek icin)
        """
        self.gorunur = gorunur
        self.yavas_mod = yavas_mod
        self.tarayici = None
        self.context = None
        self.sayfa = None
        self.playwright = None
        self.durduruldu = False
        self.screenshot_yolu = None

    def _sayfa_kontrol(self) -> bool:
        """Sayfa nesnesinin gercekten mevcut olup olmadigini kontrol et."""
        if self.sayfa is None:
            log("[BROWSER] [HATA] Page nesnesi None — navigasyon mumkun degil")
            return False
        if self.tarayici is None:
            log("[BROWSER] [HATA] Browser nesnesi None")
            return False
        return True

    def baslat(self):
        """Tarayiciyi baslatir: playwright → browser → context → page."""
        from playwright.sync_api import sync_playwright
        aid = eylem_baslat(AJAN_ADI, "Tarayici baslatiliyor", "Chromium ac", "")
        try:
            # Docker/headless ortamda gorunur mod calismaz
            is_headless = not self.gorunur or not os.environ.get("DISPLAY")
            log(f"[BROWSER] Baslatiliyor (headless={is_headless})")

            self.playwright = sync_playwright().start()
            log("[BROWSER] Playwright baslatildi")

            self.tarayici = self.playwright.chromium.launch(
                headless=is_headless,
                slow_mo=500 if self.yavas_mod else 100,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            log("[BROWSER] Chromium baslatildi")

            self.context = self.tarayici.new_context(
                viewport={"width": 1280, "height": 800}
            )
            log("[BROWSER] Context olusturuldu")

            self.sayfa = self.context.new_page()
            log("[BROWSER] Page olusturuldu")

            eylem_tamamla(aid, "Tarayici hazir", True, 0)
            log("[BROWSER] Tarayici hazir — browser/context/page mevcut")
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            log(f"[BROWSER] [HATA] Baslatma hatasi: {type(e).__name__}: {e}")
            return False

    def kapat(self):
        """Tarayiciyi kapatir."""
        try:
            if self.sayfa:
                self.sayfa.close()
                self.sayfa = None
                log("[BROWSER] Page kapatildi")
        except Exception as e:
            log(f"[BROWSER] Page kapatma hatasi: {e}")
        try:
            if self.context:
                self.context.close()
                self.context = None
                log("[BROWSER] Context kapatildi")
        except Exception as e:
            log(f"[BROWSER] Context kapatma hatasi: {e}")
        try:
            if self.tarayici:
                self.tarayici.close()
                self.tarayici = None
                log("[BROWSER] Browser kapatildi")
        except Exception as e:
            log(f"[BROWSER] Browser kapatma hatasi: {e}")
        try:
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
                log("[BROWSER] Playwright durduruldu")
        except Exception as e:
            log(f"[BROWSER] Playwright durdurma hatasi: {e}")

    def git(self, url: str) -> bool:
        """Belirtilen URL'ye gider."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        if not self._sayfa_kontrol():
            if not self.baslat():
                return False
        aid = eylem_baslat(AJAN_ADI, f"Siteye git: {url}", f"navigate({url})", "")
        try:
            self._durdurma_kontrol()
            log(f"[NAVIGATE] Basladi: {url}")
            self.sayfa.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._bekle(1)
            log(f"[NAVIGATE] Basarili: {self.sayfa.title()}")
            eylem_tamamla(aid, f"Sayfa yuklendi: {url}", True, 1)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            log(f"[NAVIGATE] [HATA] {type(e).__name__}: {e}")
            return False

    def ekran_al(self) -> str:
        """Screenshot alir ve dosyaya kaydeder. Yolu dondurur."""
        if not self._sayfa_kontrol():
            log("[SCREENSHOT] [HATA] Page mevcut degil")
            return ""
        try:
            log("[SCREENSHOT] Aliniyor...")
            zaman = datetime.now().strftime("%H%M%S_%f")[:-3]
            dosya = SCREENSHOT_DIR / f"screen_{zaman}.png"
            self.sayfa.screenshot(path=str(dosya))
            self.screenshot_yolu = str(dosya)
            boyut = dosya.stat().st_size
            log(f"[SCREENSHOT] Basarili: {dosya.name} ({boyut} byte)")
            return str(dosya)
        except Exception as e:
            log(f"[SCREENSHOT] [HATA] {type(e).__name__}: {e}")
            return ""

    def ekran_al_base64(self) -> str:
        """Screenshot alir ve base64 olarak dondurur."""
        if not self._sayfa_kontrol():
            return ""
        try:
            log("[SCREENSHOT] Base64 aliniyor...")
            png_bytes = self.sayfa.screenshot()
            b64 = base64.b64encode(png_bytes).decode("utf-8")
            log(f"[SCREENSHOT] Base64 basarili ({len(b64)} karakter)")
            return b64
        except Exception as e:
            log(f"[SCREENSHOT] [HATA] Base64 hatasi: {type(e).__name__}: {e}")
            return ""

    def ekran_al_ve_dosyaya_kaydet(self) -> tuple[str, str]:
        """Hem dosyaya kaydet hem base64 dondur. (path, base64)"""
        if not self._sayfa_kontrol():
            return "", ""
        try:
            log("[SCREENSHOT] Aliniyor (dosya + base64)...")
            png_bytes = self.sayfa.screenshot()
            b64 = base64.b64encode(png_bytes).decode("utf-8")
            zaman = datetime.now().strftime("%H%M%S_%f")[:-3]
            dosya = SCREENSHOT_DIR / f"screen_{zaman}.png"
            with open(dosya, "wb") as f:
                f.write(png_bytes)
            self.screenshot_yolu = str(dosya)
            log(f"[SCREENSHOT] Basarili: {dosya.name} ({len(png_bytes)} byte, {len(b64)} b64)")
            return str(dosya), b64
        except Exception as e:
            log(f"[SCREENSHOT] [HATA] {type(e).__name__}: {e}")
            return "", ""

    def analiz_et(self) -> dict:
        """
        Mevcut sayfayi analiz eder.
        Baslik, URL, metin, linkler, formlar, goruntuyu dondurur.
        """
        if not self._sayfa_kontrol():
            log("[ANALYSIS] [HATA] Page mevcut degil — analiz mumkun degil")
            return {"baslik": "", "url": "", "metin": "", "linkler": [], "formlar": []}

        aid = eylem_baslat(AJAN_ADI, "Sayfa analizi", "HTML + screenshot analiz", "")
        try:
            log("[ANALYSIS] Basladi...")

            # Sayfa bilgileri
            baslik = self.sayfa_baslik()
            url = self.sayfa.url
            log(f"[ANALYSIS] Baslik: {baslik}")
            log(f"[ANALYSIS] URL: {url}")

            # Linkleri oku
            try:
                linkler = self.sayfa.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => ({text: e.innerText.trim(), href: e.href})).slice(0,20)"
                )
                log(f"[ANALYSIS] {len(linkler)} link bulundu")
            except Exception as e:
                log(f"[ANALYSIS] Link okuma hatasi: {e}")
                linkler = []

            # Formlari oku
            try:
                formlar = self.sayfa.eval_on_selector_all(
                    "input, textarea, select",
                    "els => els.map(e => ({tag: e.tagName, type: e.type, name: e.name, placeholder: e.placeholder})).slice(0,20)"
                )
                log(f"[ANALYSIS] {len(formlar)} form alani bulundu")
            except Exception as e:
                log(f"[ANALYSIS] Form okuma hatasi: {e}")
                formlar = []

            sonuc = {
                "baslik": baslik,
                "url": url,
                "metin": self.sayfa_metni()[:2000],
                "linkler": linkler[:10],
                "formlar": formlar[:10],
                "screenshot": "",
            }
            eylem_tamamla(aid, f"Analiz tamam: {baslik}", True, 1)
            log(f"[ANALYSIS] Basarili: {len(linkler)} link, {len(formlar)} form")
            return sonuc
        except Exception as e:
            eylem_hata(aid, str(e))
            log(f"[ANALYSIS] [HATA] {type(e).__name__}: {e}")
            return {"baslik": "", "url": "", "metin": "", "linkler": [], "formlar": []}

    # ─── Digér metodlar ──────────────────────────────────────────────────

    def yaz(self, secici: str, metin: str, temizle: bool = True) -> bool:
        """Bir input alanina metin yazar."""
        aid = eylem_baslat(AJAN_ADI, f"Yaz: '{metin[:30]}'", f"fill({secici})", "")
        try:
            self._durdurma_kontrol()
            eleman = self.sayfa.locator(secici).first
            if temizle:
                eleman.clear()
            eleman.fill(metin)
            self._bekle(0.3)
            self.ekran_al()
            eylem_tamamla(aid, f"Yazildi: {metin[:50]}", True, 0.3)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            return False

    def tikla(self, secici: str) -> bool:
        """Bir elemana tiklar."""
        aid = eylem_baslat(AJAN_ADI, f"Tikla: {secici[:50]}", f"click({secici})", "")
        try:
            self._durdurma_kontrol()
            self.sayfa.locator(secici).first.click()
            self._bekle(0.5)
            self.ekran_al()
            eylem_tamamla(aid, "Tiklandi", True, 0.5)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            return False

    def ara(self, arama_kutusu: str, metin: str) -> bool:
        """Arama kutusuna yazar ve Enter'a basar."""
        if not self.yaz(arama_kutusu, metin):
            return False
        try:
            self.sayfa.keyboard.press("Enter")
            self._bekle(2)
            self.ekran_al()
            return True
        except Exception as e:
            return False

    def sayfa_metni(self) -> str:
        """Sayfanin tum metnini dondurur."""
        try:
            return self.sayfa.inner_text("body")[:5000]
        except:
            return ""

    def sayfa_html(self) -> str:
        """Sayfanin HTML kodunu dondurur."""
        try:
            return self.sayfa.content()[:8000]
        except:
            return ""

    def sayfa_baslik(self) -> str:
        """Sayfa basligini dondurur."""
        try:
            return self.sayfa.title()
        except:
            return ""

    def dosya_yukle(self, secici: str, dosya_yolu: str) -> bool:
        """Dosya yukleme input'una dosya ekler."""
        aid = eylem_baslat(AJAN_ADI, f"Dosya yukle: {dosya_yolu}", f"set_input_files({secici})", "")
        try:
            self.sayfa.set_input_files(secici, dosya_yolu)
            self._bekle(1)
            self.ekran_al()
            eylem_tamamla(aid, f"Dosya yuklendi: {dosya_yolu}", True, 1)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            return False

    def bekle_eleman(self, secici: str, timeout: int = 10) -> bool:
        """Bir elemanin gorunmesini bekler."""
        try:
            self.sayfa.wait_for_selector(secici, timeout=timeout * 1000)
            return True
        except:
            return False

    def dropdown_sec(self, secici: str, deger: str) -> bool:
        """Dropdown/select menusunden deger sec."""
        aid = eylem_baslat(AJAN_ADI, f"Dropdown sec: {deger}", f"select({secici})", "")
        try:
            self._durdurma_kontrol()
            self.sayfa.select_option(secici, deger)
            self._bekle(0.3)
            self.ekran_al()
            eylem_tamamla(aid, f"Secildi: {deger}", True, 0.3)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            return False

    def form_doldur(self, alanlar: dict) -> bool:
        """Form alanlarini toplu doldur."""
        aid = eylem_baslat(AJAN_ADI, f"Form doldur: {len(alanlar)} alan", "form_fill", "")
        try:
            self._durdurma_kontrol()
            for secici, deger in alanlar.items():
                eleman = self.sayfa.locator(secici).first
                tag = eleman.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    eleman.select_option(deger)
                elif tag == "input":
                    tip = eleman.get_attribute("type") or "text"
                    if tip == "checkbox":
                        if deger.lower() in ("true", "1", "evet", "yes"):
                            eleman.check()
                        else:
                            eleman.uncheck()
                    elif tip == "radio":
                        eleman.click()
                    else:
                        eleman.fill(deger)
                elif tag == "textarea":
                    eleman.fill(deger)
                else:
                    eleman.fill(deger)
                self._bekle(0.2)
            self.ekran_al()
            eylem_tamamla(aid, f"Form dolduruldu: {len(alanlar)} alan", True, 0)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            return False

    def checkbox_isaretle(self, secici: str, isaret: bool = True) -> bool:
        """Checkbox'i isaret veya kaldir."""
        aid = eylem_baslat(AJAN_ADI, f"Checkbox: {secici}", f"check({secici})", "")
        try:
            self._durdurma_kontrol()
            eleman = self.sayfa.locator(secici).first
            if isaret:
                eleman.check()
            else:
                eleman.uncheck()
            self._bekle(0.3)
            self.ekran_al()
            eylem_tamamla(aid, f"Checkbox guncellendi: {isaret}", True, 0.3)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            return False

    def radio_sec(self, secici: str) -> bool:
        """Radio button sec."""
        aid = eylem_baslat(AJAN_ADI, f"Radio sec: {secici}", f"click({secici})", "")
        try:
            self._durdurma_kontrol()
            self.sayfa.locator(secici).first.click()
            self._bekle(0.3)
            self.ekran_al()
            eylem_tamamla(aid, "Radio secildi", True, 0.3)
            return True
        except Exception as e:
            eylem_hata(aid, str(e))
            return False

    def buton_bul(self, metin: str) -> str | None:
        """Metin ile buton bul."""
        try:
            buton = self.sayfa.get_by_role("button", name=metin)
            if buton.count() > 0:
                return metin
            buton = self.sayfa.locator(f"button:has-text('{metin}')")
            if buton.count() > 0:
                return metin
            return None
        except Exception:
            return None

    def sayfa_ozet(self) -> dict:
        """Sayfanin ozet bilgilerini dondurur."""
        try:
            return {
                "baslik": self.sayfa_baslik(),
                "url": self.sayfa.url,
                "metin_uzunlugu": len(self.sayfa_metni()),
                "link_sayisi": len(self.linkleri_oku(max_sayisi=100)),
                "form_sayisi": len(self.sayfa.locator("form").all()),
                "tablo_sayisi": len(self.sayfa.locator("table").all()),
                "goruntu_sayisi": len(self.sayfa.locator("img").all()),
            }
        except Exception:
            return {}

    def tablo_oku(self, tablo_secici: str = "table") -> list:
        """Sayfadaki tabloyu oku."""
        try:
            tablo = self.sayfa.locator(tablo_secici).first
            satirlar = tablo.locator("tr").all()
            sonuc = []
            for satir in satirlar:
                hucreler = satir.locator("th, td").all()
                satir_verisi = [h.inner_text().strip() for h in hucreler]
                sonuc.append(satir_verisi)
            return sonuc
        except Exception:
            return []

    def linkleri_oku(self, max_sayisi: int = 20) -> list:
        """Sayfadaki tum linkleri oku."""
        try:
            return self.sayfa.eval_on_selector_all(
                "a[href]",
                f"els => els.map(e => ({{text: e.innerText.trim(), href: e.href}})).slice(0,{max_sayisi})"
            )
        except Exception:
            return []

    def durdur(self):
        """Insanin mudahale etmesi icin agenti durdurur."""
        log("[BROWSER] *** INSAN MUDAHALESI - Agent durduruldu ***")
        self.durduruldu = True

    def devam_et(self):
        """Duraklatilmis agenti devam ettirir."""
        log("[BROWSER] Agent devam ediyor...")
        self.durduruldu = False

    def _durdurma_kontrol(self):
        """Durdurulmus mu kontrol eder, durdurulduysa bekler."""
        while self.durduruldu:
            time.sleep(0.5)

    def _bekle(self, saniye: float):
        """Bekleme (yavas modda daha uzun bekler)."""
        carpan = 2 if self.yavas_mod else 1
        time.sleep(saniye * carpan)


# ─────────────────────────────────────────────
# Hazir Gorev Sablonlari
# ─────────────────────────────────────────────

def google_ara(sorgu: str) -> dict:
    """Google'da arama yapar ve ilk sonuclari dondurur."""
    agent = BrowserAgent(gorunur=True, yavas_mod=True)
    if not agent.baslat():
        return {"hata": "Tarayici baslatilamadi"}

    try:
        agent.git("https://www.google.com")
        agent.ara("textarea[name='q']", sorgu)
        time.sleep(2)
        analiz = agent.analiz_et()
        return analiz
    finally:
        agent.kapat()


def site_analiz_et(url: str) -> dict:
    """Bir siteye gidip tam analiz yapar."""
    agent = BrowserAgent(gorunur=True, yavas_mod=True)
    if not agent.baslat():
        return {"hata": "Tarayici baslatilamadi"}

    try:
        agent.git(url)
        time.sleep(2)
        return agent.analiz_et()
    finally:
        agent.kapat()


if __name__ == "__main__":
    print("=== UMAY Browser Agent Test ===\n")
    print("Google'da 'UMAY AI OS' araniyor...\n")
    sonuc = google_ara("UMAY AI OS Python")
    print(f"Sayfa Baslik : {sonuc.get('baslik', 'N/A')}")
    print(f"URL          : {sonuc.get('url', 'N/A')}")
    print(f"Screenshot   : {sonuc.get('screenshot', 'N/A')}")
    print(f"Link Sayisi  : {len(sonuc.get('linkler', []))}")
