"""
UMAY 9 — Kariyer.net İş Arama Workflow Demo
============================================

Bu script, UMAY'ın Browser Agent gücünü gösterir:
1. kariyer.net'e gider
2. Arama yapar (Python Developer)
3. Sonuçları analiz eder
4. İş ilanlarını listeler
5. Rapor oluşturur

Kullanım:
    python scripts/kariyer_net_workflow.py
    veya UMAY chat'ten: "kariyer.net'te Python Developer ara"

Gereksinimler: Playwright + Chromium (Docker içinde kurulu)
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Path setup
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "agents"))

from utils.logger import log


def search_jobs(keyword: str = "Python Developer", city: str = ""):
    """Kariyer.net'te iş ara."""
    from browser_agent import BrowserAgent

    log(f"[KARIYER] İş araması başlatılıyor: {keyword} {city}")

    agent = BrowserAgent(gorunur=False, yavas_mod=False)
    if not agent.baslat():
        log("[KARIYER] Browser başlatılamadı!")
        return {"error": "Browser başlatılamadı"}

    results = {
        "search_keyword": keyword,
        "city": city,
        "timestamp": datetime.now().isoformat(),
        "jobs": [],
        "total_found": 0,
        "screenshots": [],
    }

    try:
        # 1. Kariyer.net'e git
        log("[KARIYER] kariyer.net açılıyor...")
        agent.git("https://www.kariyer.net")
        time.sleep(2)
        screenshot1 = agent.ekran_al()
        results["screenshots"].append(screenshot1)
        log(f"[KARIYER] Sayfa başlığı: {agent.sayfa_baslik()}")

        # 2. Arama kutusunu bul ve doldur
        log(f"[KARIYER] '{keyword}' aranıyor...")

        # Kariyer.net arama kutusu için farklı selector'lar dene
        search_selectors = [
            'input[data-testid="search-input"]',
            'input[placeholder*="Ara"]',
            'input[placeholder*="anahtar"]',
            'input[name="keyword"]',
            '#search-input',
            '.search-input input',
            'input[type="search"]',
            'input.form-control',
        ]

        found = False
        for selector in search_selectors:
            try:
                eleman = agent.sayfa.locator(selector).first
                if eleman.is_visible(timeout=2000):
                    eleman.fill(keyword)
                    found = True
                    log(f"[KARIYER] Arama kutusu bulundu: {selector}")
                    break
            except:
                continue

        if not found:
            # Sayfa içeriğini analiz et
            content = agent.sayfa_metni()[:2000]
            log(f"[KARIYER] Arama kutusu bulunamadı. Sayfa içeriği: {content[:500]}")
            results["error"] = "Arama kutusu bulunamadı"
            results["page_content"] = content[:1000]
            return results

        time.sleep(0.5)

        # 3. Enter tuşuna bas veya ara butonuna tıkla
        try:
            agent.sayfa.keyboard.press("Enter")
            log("[KARIYER] Enter tuşuna basıldı")
        except:
            # Ara butonunu tıkla
            try:
                agent.sayfa.locator('button[type="submit"], .search-button, button:has-text("Ara")').first.click()
                log("[KARIYER] Ara butonuna tıklandı")
            except:
                log("[KARIYER] Enter/ar但失败")

        time.sleep(3)
        screenshot2 = agent.ekran_al()
        results["screenshots"].append(screenshot2)

        # 4. Sonuç sayfasını analiz et
        log("[KARIYER] Sonuçlar analiz ediliyor...")
        page_text = agent.sayfa_metni()
        results["page_title"] = agent.sayfa_baslik()
        results["page_url"] = agent.sayfa.url

        # 5. İş ilanlarını çıkarmaya çalış
        job_selectors = [
            '[data-testid="job-card"]',
            '.job-card',
            '.job-item',
            '.job-listing',
            'article',
            '.position',
            '.ilan',
            'a[href*="/is-ilani/"]',
            'a[href*="/job/"]',
        ]

        jobs_found = []
        for selector in job_selectors:
            try:
                elements = agent.sayfa.locator(selector).all()
                if elements:
                    log(f"[KARIYER] {len(elements)} iş ilanı bulundu ({selector})")
                    for i, el in enumerate(elements[:20]):  # Max 20 ilan
                        try:
                            title = el.inner_text()[:200]
                            link = ""
                            try:
                                link = el.get_attribute("href") or ""
                                if not link:
                                    link_el = el.locator("a").first
                                    link = link_el.get_attribute("href") or ""
                            except:
                                pass

                            jobs_found.append({
                                "index": i + 1,
                                "title": title.strip(),
                                "link": link,
                            })
                        except:
                            continue
                    if jobs_found:
                        break
            except:
                continue

        # 6. Sayfadaki tüm linkleri topla
        if not jobs_found:
            log("[KARIYER] Structured job cards bulunamadı, linkler analiz ediliyor...")
            try:
                all_links = agent.sayfa.locator("a").all()
                for link in all_links[:100]:
                    try:
                        href = link.get_attribute("href") or ""
                        text = link.inner_text().strip()[:200]
                        if text and ("iş" in text.lower() or "job" in text.lower() or
                                     "pozisyon" in text.lower() or "developer" in text.lower() or
                                     "mühendis" in text.lower() or "uzman" in text.lower()):
                            jobs_found.append({
                                "index": len(jobs_found) + 1,
                                "title": text,
                                "link": href,
                            })
                    except:
                        continue
            except:
                pass

        results["jobs"] = jobs_found[:20]
        results["total_found"] = len(jobs_found)

        # 7. Sayfadaki önemli metni kaydet
        results["page_analysis"] = page_text[:3000]

        log(f"[KARIYER] Toplam {len(jobs_found)} iş ilanı bulundu")

    except Exception as e:
        log(f"[KARIYER] Hata: {e}")
        results["error"] = str(e)
    finally:
        try:
            agent.kapat()
        except:
            pass

    return results


def analyze_job(url: str):
    """Belirli bir iş ilanını analiz et."""
    from browser_agent import BrowserAgent

    log(f"[KARIYER] İlan analiz ediliyor: {url}")

    agent = BrowserAgent(gorunur=False, yavas_mod=False)
    if not agent.baslat():
        return {"error": "Browser başlatılamadı"}

    result = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "title": "",
        "company": "",
        "location": "",
        "requirements": [],
        "description": "",
        "screenshot": "",
    }

    try:
        agent.git(url)
        time.sleep(2)

        result["title"] = agent.sayfa_baslik()
        result["screenshot"] = agent.ekran_al()
        content = agent.sayfa_metni()
        result["description"] = content[:5000]

        # Basit analiz
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "şirket" in line.lower() or "company" in line.lower():
                result["company"] = line[:100]
            if "konum" in line.lower() or "location" in line.lower() or "yer" in line.lower():
                result["location"] = line[:100]

        log(f"[KARIYER] İlan analiz edildi: {result['title']}")

    except Exception as e:
        log(f"[KARIYER] Analiz hatası: {e}")
        result["error"] = str(e)
    finally:
        try:
            agent.kapat()
        except:
            pass

    return result


def generate_report(search_results: dict) -> str:
"""Arama sonuçlarından rapor oluştur."""
    report_lines = [
        "=" * 60,
        "KARIYER.NET İŞ ARAMA RAPORU",
        "=" * 60,
        f"Arama: {search_results.get('search_keyword', '?')}",
        f"Şehir: {search_results.get('city', 'Tümü')}",
        f"Tarih: {search_results.get('timestamp', '?')}",
        f"Toplam Sonuç: {search_results.get('total_found', 0)}",
        "",
        "-" * 60,
        "BULUNAN İŞ İLANLARI",
        "-" * 60,
    ]

    jobs = search_results.get("jobs", [])
    if not jobs:
        report_lines.append("Henüz iş ilanı bulunamadı.")
        report_lines.append("(Tarayıcı arama sonucunu tam olarak parse edememiş olabilir)")
    else:
        for job in jobs:
            report_lines.append(f"")
            report_lines.append(f"  #{job.get('index', '?')}. {job.get('title', 'Başlık yok')}")
            if job.get('link'):
                report_lines.append(f"     Link: {job['link']}")

    if search_results.get("error"):
        report_lines.extend([
            "",
            "-" * 60,
            "HATA",
            "-" * 60,
            search_results["error"],
        ])

    report_lines.extend([
        "",
        "=" * 60,
        f"Ekran görüntüleri: {len(search_results.get('screenshots', []))} adet",
        f"Sayfa URL: {search_results.get('page_url', 'N/A')}",
        "=" * 60,
    ])

    return "\n".join(report_lines)


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    keyword = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Python Developer"

    print(f"\n🔍 UMAY 9 — Kariyer.net İş Arama")
    print(f"   Arama kelimesi: {keyword}")
    print(f"   Başlatılıyor...\n")

    results = search_jobs(keyword)
    report = generate_report(results)
    print(report)

    # Raporu kaydet
    report_path = ROOT / "logs" / f"kariyer_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\n📄 Rapor kaydedildi: {report_path}")
