import asyncio
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "SEU_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "SEU_TELEGRAM_CHAT_ID")
STATE_FILE = Path(os.getenv("STATE_FILE", "/app/data/sent_jobs.json"))
FILTROS_FILE = Path(os.getenv("FILTROS_FILE", "/app/filtros.txt"))

SECOES_OBRIGATORIOS = {"[obrigatorios]", "[obrigatórios]"}
SECOES_EXCLUIDOS = {"[excluidos]", "[excluídos]"}


def normalize(texto):
    decomposicao = unicodedata.normalize("NFD", texto.lower())
    return "".join(ch for ch in decomposicao if unicodedata.category(ch) != "Mn")


def compile_termo(texto):
    """Casa o termo ignorando acento e a vogal final de gênero (o/a, os/as)."""
    normalizado = normalize(texto)
    partes = []
    for parte in re.split(r"(\s+)", normalizado):
        if parte == "" or parte.isspace():
            partes.append(re.escape(parte))
            continue
        if len(parte) >= 4 and parte.endswith(("os", "as")):
            partes.append(re.escape(parte[:-2]) + r"(?:os|as)")
        elif len(parte) >= 4 and parte.endswith(("o", "a")):
            partes.append(re.escape(parte[:-1]) + r"[oa]")
        else:
            partes.append(re.escape(parte))
    return texto, re.compile("".join(partes))


def load_filtros(path):
    if not path.is_file():
        raise SystemExit(
            f"Arquivo de filtros não encontrado: {path}\n"
            "O arquivo filtros.txt precisa estar na pasta do projeto."
        )

    obrigatorios = []
    excluidos = []
    secao = None
    for numero, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        header = raw.strip().lower()
        if header in SECOES_OBRIGATORIOS:
            secao = "obrigatorios"
            continue
        if header in SECOES_EXCLUIDOS:
            secao = "excluidos"
            continue
        if secao is None:
            raise SystemExit(f"Linha {numero} de {path} está fora de uma seção: {raw}")
        termo = compile_termo(raw.lstrip(" \t"))
        if secao == "obrigatorios":
            obrigatorios.append(termo)
        else:
            excluidos.append(termo)

    if not obrigatorios:
        raise SystemExit(
            f"Nenhum termo obrigatório em {path}. A busca foi interrompida."
        )
    return obrigatorios, excluidos


def primeiro_termo(termos, titulo):
    normalizado = normalize(titulo)
    for texto, pattern in termos:
        if pattern.search(normalizado):
            return texto
    return None


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


def send_telegram(text):
    if TELEGRAM_TOKEN in ("", "SEU_TELEGRAM_BOT_TOKEN"):
        print("Telegram não configurado. Mensagem não enviada.")
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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        url = "https://portal.gupy.io/job-search/term=Suporte&workplaceTypes[]=remote"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector('a[href*="/job/"]', timeout=20000)
            await page.wait_for_timeout(2000)
            vagas = await page.eval_on_selector_all(
                'a[href*="/job/"]',
                '''elements => elements.map(e => {
                    const lines = e.innerText.trim().split("\\n").map(s => s.trim()).filter(Boolean);
                    const published = lines.find(l => l.toLowerCase().includes("published") || l.toLowerCase().includes("publicad")) || "";
                    return {
                        company: lines[0] || "",
                        title: lines[1] || lines[0] || "",
                        published: published,
                        link: e.href
                    };
                }).filter(v => v.link && v.title)'''
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
    obrigatorios, excluidos = load_filtros(FILTROS_FILE)
    print(
        f"Filtros: {len(obrigatorios)} obrigatórios, {len(excluidos)} excluídos "
        f"({FILTROS_FILE})"
    )
    print("🤖 Executando verificação do Agente...")
    vagas = await buscar_vagas_gupy()
    if not vagas:
        print("Nenhuma vaga encontrada ou erro de carregamento.")
        return

    sent = load_sent()
    novas = 0

    for vaga in vagas:
        titulo = vaga.get("title") or ""
        link = vaga.get("link") or ""

        if not link or link in sent:
            continue

        if not primeiro_termo(obrigatorios, titulo):
            continue

        termo_excluido = primeiro_termo(excluidos, titulo)
        if termo_excluido:
            print(f"Descartada ({termo_excluido.strip()}): {titulo}")
            continue

        msg = (
            f"Nova vaga\n\n"
            f"Empresa: {vaga.get('company', '-')}\n"
            f"Cargo: {titulo or '-'}\n"
            f"Publicacao: {vaga.get('published', '-')}\n"
            f"{link}"
        )
        print(f"✅ Nova: {titulo}")
        ok = send_telegram(msg)
        if ok:
            sent[link] = {
                "title": titulo,
                "company": vaga.get("company"),
                "published": vaga.get("published"),
                "sent_at": datetime.utcnow().isoformat(),
            }
            novas += 1
        if novas >= 10:
            break

    save_sent(sent)
    print(f"Enviadas {novas} vagas novas. Total já enviadas: {len(sent)}")


if __name__ == "__main__":
    asyncio.run(main())
