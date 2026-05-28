"""
setup.py
────────
Script de configuração inicial do FACITEC-MoodleSync.
Automatiza a criação do ambiente virtual, instalação de dependências
e geração do arquivo .env com as credenciais do usuário.

Uso:
    python setup.py
"""

import os
import sys
import subprocess
import shutil
import platform


# ── Cores para terminal ───────────────────────────────────────────────────────

IS_WINDOWS = platform.system() == "Windows"

def c(color, text):
    codes = {"green": "\033[92m", "blue": "\033[94m",
             "yellow": "\033[93m", "red": "\033[91m", "bold": "\033[1m", "reset": "\033[0m"}
    if IS_WINDOWS:
        return text
    return f"{codes.get(color,'')}{text}{codes['reset']}"


# ── Utilitários ───────────────────────────────────────────────────────────────

def header(text):
    print(f"\n{c('bold', '─' * 50)}")
    print(c('bold', f"  {text}"))
    print(c('bold', '─' * 50))

def ok(text):   print(f"  {c('green',  '✓')} {text}")
def info(text): print(f"  {c('blue',   '→')} {text}")
def warn(text): print(f"  {c('yellow', '!')} {text}")
def err(text):  print(f"  {c('red',    '✗')} {text}")

def ask(prompt, default=""):
    try:
        val = input(f"  {c('blue', '?')} {prompt} ").strip()
        return val if val else default
    except KeyboardInterrupt:
        print("\n\nSetup cancelado pelo usuário.")
        sys.exit(0)

def ask_secret(prompt):
    import getpass
    try:
        val = getpass.getpass(f"  {c('blue', '?')} {prompt} ").strip()
        return val
    except KeyboardInterrupt:
        print("\n\nSetup cancelado pelo usuário.")
        sys.exit(0)


# ── Verificações de pré-requisitos ────────────────────────────────────────────

def check_python():
    header("1/5  Verificando Python")
    version = sys.version_info
    if version < (3, 11):
        err(f"Python 3.11+ é necessário. Você tem {version.major}.{version.minor}.")
        err("Baixe em: https://python.org/downloads")
        sys.exit(1)
    ok(f"Python {version.major}.{version.minor}.{version.micro} detectado")


def check_chrome():
    header("2/5  Verificando Google Chrome (navegador)")
    paths = {
        "Windows": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        ],
        "Darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ],
        "Linux": [
            "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/brave-browser",
        ],
    }
    system = platform.system()
    for path in paths.get(system, []):
        if os.path.exists(path):
            ok(f"Chrome encontrado em: {path}")
            info("O ChromeDriver (arquivo de automacao) sera baixado automaticamente")
            info("na primeira execucao — apenas ~10 MB, nao e o Chrome em si.")
            return
    for name in ("google-chrome", "google-chrome-stable", "chromium",
                  "chromium-browser", "brave-browser", "chrome"):
        found = shutil.which(name)
        if found:
            ok(f"Chrome encontrado no PATH: {found}")
            info("O ChromeDriver sera baixado automaticamente na primeira execucao (~10 MB).")
            return
    warn("Chrome nao encontrado automaticamente.")
    warn("O projeto precisa do Google Chrome JA instalado no seu computador.")
    warn("O setup NAO baixa o Chrome — so o ChromeDriver (driver de automacao).")
    warn("Instale o Chrome em: https://www.google.com/chrome e rode o setup novamente.")


# ── Ambiente virtual ──────────────────────────────────────────────────────────

def create_venv():
    header("3/5  Criando ambiente virtual")
    venv_path = os.path.join(os.path.dirname(__file__), "venv")

    if os.path.exists(venv_path):
        warn("Ambiente virtual já existe — pulando criação.")
        return venv_path

    info("Criando venv...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True, capture_output=True)
        ok("Ambiente virtual criado em ./venv")
    except subprocess.CalledProcessError as e:
        err(f"Falha ao criar venv: {e.stderr.decode()}")
        sys.exit(1)

    return venv_path


def install_dependencies():
    header("4/5  Instalando dependências")

    # Resolve o executável pip dentro do venv
    if IS_WINDOWS:
        pip = os.path.join("venv", "Scripts", "pip.exe")
    else:
        pip = os.path.join("venv", "bin", "pip")

    if not os.path.exists(pip):
        err("pip não encontrado no venv. Tente apagar a pasta venv/ e rodar novamente.")
        sys.exit(1)

    info("Instalando pacotes de requirements.txt...")
    try:
        subprocess.run(
            [pip, "install", "-r", "requirements.txt", "--quiet"],
            check=True
        )
        ok("selenium instalado")
        ok("requests instalado")
        ok("python-dotenv instalado")
    except subprocess.CalledProcessError as e:
        err(f"Falha na instalação: {e}")
        sys.exit(1)


# ── Geração do .env ───────────────────────────────────────────────────────────

def create_env():
    header("5/5  Configurando credenciais (.env)")

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    if os.path.exists(env_path):
        resposta = ask(".env já existe. Deseja reconfigurar? (s/N):", "N").lower()
        if resposta != "s":
            ok(".env mantido sem alterações.")
            return

    print()
    print(f"  {c('bold', 'Credenciais do Moodle (campus virtual FACITEC)')}")
    moodle_user = ask("Usuário (matrícula ou e-mail):")
    moodle_pass = ask_secret("Senha:")

    print()
    print(f"  {c('bold', 'Credenciais do Notion')}")
    info("Token de integração: notion.so/my-integrations → sua integração → copie o token")
    notion_token = ask("NOTION_TOKEN (começa com ntn_ ou secret_):")

    info("ID do banco: pegue da URL da página do Notion (parte entre / e ?)")
    notion_db = ask("NOTION_DB_ID:")

    print()
    print(f"  {c('bold', 'Configurações opcionais')}")
    headless = ask("Executar Chrome em modo invisível? (S/n):", "S").upper()
    headless_val = "false" if headless == "N" else "true"
    debug = ask("Ativar logs detalhados (DEBUG)? (s/N):", "N").upper()
    debug_val = "true" if debug == "S" else "false"

    env_content = f"""# FACITEC-MoodleSync — gerado pelo setup.py
# NÃO faça commit deste arquivo!

# ── Moodle ────────────────────────────────────────────────────────────────────
MOODLE_BASE_URL=https://campusvirtual.facitec.edu.py
MOODLE_USER={moodle_user}
MOODLE_PASS={moodle_pass}

# ── Notion ────────────────────────────────────────────────────────────────────
NOTION_TOKEN={notion_token}
NOTION_DB_ID={notion_db}

# ── WebDriver ─────────────────────────────────────────────────────────────────
HEADLESS={headless_val}
WAIT_TIMEOUT=20
PAGE_LOAD_TIMEOUT=30

# ── App ───────────────────────────────────────────────────────────────────────
DEBUG={debug_val}
LOOP_INTERVAL=3600
LOG_FILE=logs/moodle_sync.log
"""
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    ok(".env criado com sucesso!")


# ── Instruções finais ─────────────────────────────────────────────────────────

def print_final():
    print(f"\n{c('bold', '=' * 50)}")
    print(c('green', c('bold', '  ✓  Setup concluído! Projeto pronto para uso.')))
    print(c('bold', '=' * 50))

    if IS_WINDOWS:
        activate = r"venv\Scripts\activate"
    else:
        activate = "source venv/bin/activate"

    print(f"""
  Como executar:

    {c('bold', '1.')} Ative o ambiente virtual:
       {c('blue', activate)}

    {c('bold', '2.')} Sincronização única:
       {c('blue', 'python main.py')}

    {c('bold', '3.')} Modo loop (a cada hora):
       {c('blue', 'python main.py --loop')}

    {c('bold', '4.')} Diagnóstico (sem sincronizar):
       {c('blue', 'python main.py --diag')}

  Logs em: {c('blue', 'logs/moodle_sync.log')}
""")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print(c('bold', "\n  🎓 FACITEC-MoodleSync — Setup"))
    print(c('blue', "  Configuração inicial do projeto\n"))

    check_python()
    check_chrome()
    create_venv()
    install_dependencies()
    create_env()
    print_final()


if __name__ == "__main__":
    main()
