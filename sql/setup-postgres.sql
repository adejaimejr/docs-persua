-- ============================================================================
-- Setup Postgres pro docs-persua
-- ============================================================================
-- Roda esse script ANTES do primeiro deploy do Docmost.
-- Cria database `docmost` e user `docmost` isolados de outros apps que
-- compartilham a mesma instancia Postgres no Swarm (postgres_postgres).
--
-- Como rodar:
--
--   1. Pegar a senha do superuser postgres no Dokploy
--      (servico postgres_postgres, env var POSTGRES_PASSWORD)
--
--   2. Conectar via psql, opcoes:
--
--      a) Pelo proprio container postgres no servidor Swarm:
--         docker exec -it $(docker ps -q -f name=postgres_postgres) psql -U postgres
--
--      b) Pela UI do Dokploy: a maioria das versoes tem terminal/SQL no app
--         postgres_postgres. Cole o SQL la.
--
--      c) Via tunel SSH + psql local (requer porta exposta):
--         psql -h <vps-ip> -U postgres -d postgres
--
--   3. Trocar `<SENHA_FORTE_AQUI>` na linha 23 pela senha real
--      Gerar com: openssl rand -base64 24
--      Anotar pra colar no DATABASE_URL do .env do app docs-persua
--
--   4. Colar o SQL abaixo (todo) e executar
-- ============================================================================

-- Cria o user dedicado (sem privilegios de admin)
CREATE USER docmost WITH ENCRYPTED PASSWORD '<SENHA_FORTE_AQUI>';

-- Cria o database
CREATE DATABASE docmost OWNER docmost ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8' TEMPLATE template0;

-- Garante permissoes
GRANT ALL PRIVILEGES ON DATABASE docmost TO docmost;

-- Conecta no novo db pra dar permissao no schema public
\c docmost
GRANT ALL ON SCHEMA public TO docmost;
GRANT CREATE ON SCHEMA public TO docmost;

-- Validacao
SELECT current_database(), current_user;
-- Deve retornar: docmost | docmost (se conectou como docmost) ou docmost | postgres (se ainda como superuser)
