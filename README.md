# Agente de Vagas (Gupy + Telegram)

Agente leve que busca vagas no portal público da Gupy, filtra pelo título e envia alertas no Telegram.

Não fica rodando o tempo todo: sobe, busca, envia e desliga. O agendamento é feito pelo cron do sistema.

Útil para quem quer ser um dos primeiros a se candidatar em vagas novas.

## Aviso

Não exige login. A busca é feita na página pública da Gupy.

Mesmo assim, evite intervalos muito curtos para reduzir o risco de bloqueio temporário de IP.  
Recomendado: **5 horas** ou mais. Você também pode configurar uma execução ao ligar a máquina.

Novas vagas costumam ser publicadas principalmente nestes horários:
- Manhã: entre 8h e 11h
- Início da tarde: entre 13h e 16h

O autor não se responsabiliza por bloqueios ou violações dos Termos de Uso do site.

## Requisitos

- Linux (testado em Debian)
- Docker e Docker Compose
- Bot do Telegram (grátis, via @BotFather)

## Instalação rápida

```bash
git clone https://github.com/lfleites/Vagas-Agent.git
cd vagas-agent
chmod +x install.sh
./install.sh
```

O script pergunta token, chat ID, termo de busca e filtros, cria o `.env`, constrói a imagem e (opcionalmente) configura o cron.

## Configuração manual

```bash
cp .env.example .env
# Edite o .env
mkdir -p data
docker compose build
docker compose run --rm vagas-agent
```

### Variáveis do `.env`

| Variável           | Descrição                                                         |
|--------------------|-------------------------------------------------------------------|
| `TELEGRAM_TOKEN`   | Token do bot (BotFather)                                          |
| `TELEGRAM_CHAT_ID` | Seu chat ID                                                       |
| `SEARCH_TERM`      | Termo de busca na Gupy (ex.: `Suporte`)                           |
| `WORKPLACE`        | `remote`, `hybrid` ou `on-site`                                   |
| `REQUIRED_TERMS`   | Termos que o título **deve** conter (vírgula). Vazio = não filtra |
| `EXCLUDED_TERMS`   | Termos que **descartam** a vaga (vírgula). Vazio = não descarta   |
| `MAX_ALERTS`       | Máximo de alertas por execução (padrão: 10)                       |

## Como pegar o Chat ID

1. Crie o bot com o @BotFather (`/newbot`).
2. Envie qualquer mensagem para o bot.
3. Acesse no navegador:  
   `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
4. Procure `"chat":{"id":123456789}` e use esse número.

## Agendamento (cron)

A cada 5 horas + na inicialização da máquina:

```cron
0 */5 * * * cd /caminho/para/vagas-agent && /usr/bin/docker compose run --rm vagas-agent >> /caminho/para/vagas-agent/data/cron.log 2>&1
@reboot sleep 90 && cd /caminho/para/vagas-agent && /usr/bin/docker compose run --rm vagas-agent >> /caminho/para/vagas-agent/data/cron.log 2>&1
```

O `install.sh` pode configurar isso automaticamente.

## Como funciona o controle de “já enviado”

- Cada link enviado é gravado em `data/sent_jobs.json`.
- Na próxima execução, links já presentes no arquivo são ignorados.
- Apagar a mensagem no Telegram **não** remove do arquivo.
- Se a empresa republicar a vaga com um job ID novo, o link muda e o alerta é enviado de novo.

## Sugestão de filtros (área de Suporte / Service Desk)

Para quem atua em suporte técnico, Service Desk, N1/N2 (Windows, ServiceNow, Active Directory, remoto):

```env
SEARCH_TERM=Suporte
WORKPLACE=remote
REQUIRED_TERMS=suporte,service desk,helpdesk,help desk,atendimento técnico,atendimento tecnico,técnico de suporte,tecnico de suporte,analista de suporte,analista suporte,n1,n2,sustentação,sustentacao
EXCLUDED_TERMS=dados,data,bi ,bi,,mis,power bi,powerbi,kpi,dashboard,etl,sql,oracle,analista de dados,analise de dados,análise de dados,especialista suporte atendimento,rpa,middleware,desenvolvedor,developer,dev ,qa,design,estágio,estagio,estagiário,pj,product owner,scrum master
```

Ajuste conforme sua área. Os filtros olham apenas o **título** da vaga.

## Comandos úteis

```bash
docker compose run --rm vagas-agent   # executar agora
crontab -l                            # ver agendamento
tail -f data/cron.log                 # logs das execuções automáticas
```

## Segurança

- Nunca commite o arquivo `.env` (já está no `.gitignore`).
- Se o token vazar, revogue no @BotFather (`/revoke` ou gere um novo).

## Licença

MIT
