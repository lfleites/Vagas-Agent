# Agente de Vagas (Gupy + Telegram)

Agente leve que busca vagas no portal público da Gupy, filtra pelo título e envia alertas no Telegram.

Não fica rodando o tempo todo: sobe, busca, envia e desliga. No Linux o agendamento é o cron. No Windows, o Agendador de Tarefas.

A busca atual olha a primeira página de vagas remotas com o termo `Suporte`, na ordem da mais nova para a mais antiga. São cerca de 10 anúncios por execução. O `filtros.txt` decide quais desses títulos viram mensagem.

## Aviso

Não exige login. A busca é feita na página pública da Gupy.

Evite intervalos menores que 5 horas. Uma execução lê uma página de resultados e não abre o anúncio de cada vaga. Varrer muitas páginas, ou rodar de poucos em poucos minutos, aumenta o risco de bloqueio temporário de IP.

O autor não se responsabiliza por bloqueios ou por violações dos Termos de Uso do site.

## Requisitos

- Docker com Docker Compose (`docker compose`)
- Linux ou Windows 10/11 de 64 bits
- No Windows: Docker Desktop aberto, com o backend WSL2
- Bot do Telegram, criado de graça com o [@BotFather](https://t.me/BotFather)

## Instalação no Linux

```bash
git clone https://github.com/lfleites/Vagas-Agent.git
cd Vagas-Agent
chmod +x install.sh
./install.sh
```

O script pede o token e o chat ID, grava o `.env` na pasta do projeto, constrói a imagem e, se você confirmar, agenda a execução a cada 5 horas e na inicialização.

## Instalação no Windows

1. Instale o [Docker Desktop](https://www.docker.com/products/docker-desktop/) e deixe ele aberto. Na primeira abertura, confirme o uso do WSL2.
2. No Docker Desktop, ative a inicialização junto com o Windows. A tarefa agendada falha se o Docker estiver fechado.
3. Clone o repositório e entre na pasta.
4. Dê dois cliques em `install.bat`, ou rode no Prompt de Comando:

```bat
install.bat
```

O script pede o token e o chat ID, grava o `.env`, constrói a imagem e, se você confirmar, cria duas tarefas:

- `Vagas-Agent`, a cada 5 horas
- `Vagas-Agent-Logon`, cerca de 90 segundos depois do logon

A primeira construção baixa o Chromium e pode levar alguns minutos.

## Configuração manual

```bash
cp .env.example .env
mkdir -p data
docker compose build
docker compose run --rm vagas-agent
```

No Windows, a cópia do exemplo é `copy .env.example .env`. A pasta `data` pode ser criada com `mkdir data`.

O `.env` tem só o Telegram:

```env
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
```

Os filtros de título não ficam mais no `.env`. Eles ficam em `filtros.txt`.

### Como pegar o chat ID

1. Crie o bot com o @BotFather (`/newbot`).
2. Envie qualquer mensagem para o bot.
3. Abra no navegador `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`.
4. Use o número que aparece em `"chat":{"id":123456789}`.

## Filtros

`filtros.txt` é lido em toda execução. Salvar o arquivo basta. Não precisa reconstruir a imagem.

- A vaga precisa ter pelo menos um termo de `[obrigatorios]` no título.
- Se o título tiver qualquer termo de `[excluidos]`, ela é descartada.
- Acento é ignorado. A vogal final de gênero também: `estagiario` casa com estagiário e estagiária.
- Linha em branco e linha que começa com `#` são ignoradas.
- O espaço no final de `bi` e de `dev` é de propósito. Sem ele, `bi` entraria em "habitação" e `dev` em "devops".

O arquivo que vem no repositório é o perfil de suporte técnico, service desk e N1/N2, remoto. Troque os termos pela sua área. O filtro olha só o título.

A URL da busca está em `app.py`, na função `buscar_vagas_gupy`:

```text
https://portal.gupy.io/job-search/term=Suporte&workplaceTypes[]=remote
```

`filtros.txt` não muda essa URL. Para outro cargo ou outro modelo de trabalho, edite essa linha. O `docker-compose.yml` monta o `app.py` e o `filtros.txt` da pasta do projeto, então essa edição também não pede rebuild.

## Agendamento no Linux

```cron
0 */5 * * * cd /caminho/para/Vagas-Agent && docker compose run --rm vagas-agent >> /caminho/para/Vagas-Agent/data/cron.log 2>&1
@reboot sleep 90 && cd /caminho/para/Vagas-Agent && docker compose run --rm vagas-agent >> /caminho/para/Vagas-Agent/data/cron.log 2>&1
```

O `install.sh` grava essas linhas se você confirmar.

## Agendamento no Windows

O `install.bat` chama o `run.bat` pelo Agendador de Tarefas. Para criar na mão:

1. Abra o Agendador de Tarefas.
2. Crie uma tarefa que repete a cada 5 horas.
3. Programa: o caminho completo de `run.bat`.
4. Marque para executar só com o usuário logado. O Docker Desktop precisa estar aberto.
5. Crie outra tarefa com o gatilho "Ao fazer logon", atrasada em 90 segundos, chamando o mesmo `run.bat`.

## O que conta como vaga nova

- Cada link enviado fica em `data/sent_jobs.json`.
- A primeira execução cria esse arquivo. Ela avisa o que estiver na primeira página e passar no filtro, inclusive anúncio de dias anteriores.
- Nas execuções seguintes, link já gravado é ignorado.
- Apagar a mensagem no Telegram não apaga o arquivo.
- Se a empresa republicar a vaga com outro identificador, o link muda e o alerta sai de novo.

## Comandos

```bash
docker compose run --rm vagas-agent
```

No Linux, `crontab -l` mostra a agenda e `tail -f data/cron.log` acompanha o log. No Windows, o log fica em `data\cron.log`.

## O que não vai para o GitHub

O `.gitignore` deixa de fora o `.env`, a pasta `data`, a pasta `backup` e arquivos `.pdf`. Token, histórico de vagas e currículo ficam na máquina de quem usa.

Se um token vazar, revogue no @BotFather e gere outro.

## Licença

MIT
