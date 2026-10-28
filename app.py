import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STATE_FILE = Path(os.getenv("STATE_FILE", "/app/data/sent_jobs.json"))

# Busca na Gupy
SEARCH_TERM = os.getenv("SEARCH_TERM", "Suporte")
WORKPLACE = os.getenv("WORKPLACE", "remote")  # remote | hybrid | on-site

# Filtros (separados por vírgula no .env)
def _split_terms(raw: str) -> list[str]:
    return [t.strip().lower() for t in raw.split(",") if t.strip()]

TERMOS_OBRIGATORIOS = _split_terms(os.getenv("REQUIRED_TERMS", ""))
TERMOS_EXCLUIDOS = _split_terms(os.getenv("EXCLUDED_TERMS", ""))

MAX_ALERTS = int(os.getenv("MAX_ALERTS", "10"))


def load_sent():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_sent(sent):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(sent, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_telegram(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram não configurado (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if not r.ok:
            print(f"Telegram recusou: {r.status_code} {r.text}")
            return False
        return True
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")
        return False


async def buscar_vagas_gupy():
    print("🔍 Varrendo portal Gupy...")
    url = (
        f"https://portal.gupy.io/job-search/term={SEARCH_TERM}"
        f"&workplaceTypes[]={WORKPLACE}"
    )
    print(f"URL: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector('a[href*="/job/"]', timeout=20000)
            await page.wait_for_timeout(2000)
            vagas = await page.eval_on_selector_all(
                'a[href*="/job/"]',
                """elements => elements.map(e => {
                    const lines = e.innerText.trim().split("\\n").map(s => s.trim()).filter(Boolean);
                    const published = lines.find(l =>
                        l.toLowerCase().includes("published") ||
                        l.toLowerCase().includes("publicad")
                    ) || "";
                    return {
                        company: lines[0] || "",
                        title: lines[1] || lines[0] || "",
                        published: published,
                        link: e.href
                    };
                }).filter(v => v.link && v.title)""",
            )
            seen = set()
            unicas = []
            for v in vagas:
                if v["link"] not in seen:
                    seen.add(v["link"])
                    unicas.append(v)
            await browser.close()
            print(f"Encontradas {len(unicas)} vagas brutas")
            return unicas
        except Exception as e:
            print(f"Erro no carregamento da Gupy: {e}")
            await browser.close()
            return []


async def main():
    print("🤖 Executando verificação do Agente...")
    vagas = await buscar_vagas_gupy()
    if not vagas:
        print("Nenhuma vaga encontrada ou erro de carregamento.")
        return

    sent = load_sent()
    novas = 0

    for vaga in vagas:
        titulo = (vaga.get("title") or "").lower()
        link = vaga.get("link") or ""

        if not link or link in sent:
            continue

        if TERMOS_OBRIGATORIOS and not any(t in titulo for t in TERMOS_OBRIGATORIOS):
            continue

        if TERMOS_EXCLUIDOS and any(t in titulo for t in TERMOS_EXCLUIDOS):
            print(f"Descartada: {vaga.get('title')}")
            continue

        msg = (
            f"Nova vaga\n\n"
            f"Empresa: {vaga.get('company', '-')}\n"
            f"Cargo: {vaga.get('title', '-')}\n"
            f"Publicacao: {vaga.get('published', '-')}\n"
            f"{link}"
        )
        print(f"✅ Nova: {vaga.get('title')}")
        if send_telegram(msg):
            sent[link] = {
                "title": vaga.get("title"),
                "company": vaga.get("company"),
                "published": vaga.get("published"),
                "sent_at": datetime.utcnow().isoformat(),
            }
            novas += 1
        if novas >= MAX_ALERTS:
            break

    save_sent(sent)
    print(f"Enviadas {novas} vagas novas. Total já enviadas: {len(sent)}")


if __name__ == "__main__":
    asyncio.run(main())
