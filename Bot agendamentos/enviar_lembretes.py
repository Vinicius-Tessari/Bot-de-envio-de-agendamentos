import mysql.connector
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import logging
import requests

data_atual = datetime.now().strftime("%d-%m-%Y")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"log_{data_atual}.txt"),
        logging.StreamHandler()
    ]
)

def formatar_telefone(telefone):
    telefone = ''.join(filter(str.isdigit, telefone))
    if telefone.startswith("55") and len(telefone) == 12:
        return f"+{telefone}"
    elif telefone.startswith("55") and len(telefone) == 11:
        return f"+{telefone}"
    elif len(telefone) == 10:
        return f"+55{telefone}"
    elif len(telefone) == 11:
        return f"+55{telefone}"
    else:
        raise ValueError(f"Número de telefone inválido: {telefone}")

def iniciar_driver():
    try:
        chrome_options = Options()
        user_data_dir = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data'
        chrome_options.add_argument(f'user-data-dir={user_data_dir}')
        chrome_options.add_argument('--profile-directory=Bot')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-browser-side-navigation')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        service = Service(ChromeDriverManager().install())
        os.system("taskkill /f /im chrome.exe")
        time.sleep(2)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        logging.error(f"Erro ao iniciar o driver: {str(e)}")
        return None

def esperar_elemento(driver, xpath, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
    except Exception:
        return None

def limpar_pesquisa(driver):
    try:
        for _ in range(3):
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.5)
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                search_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="3"]')
                if search_box:
                    search_box.clear()
                    search_box.send_keys(Keys.CONTROL + "a")
                    search_box.send_keys(Keys.DELETE)
                    time.sleep(0.5)
                    if not search_box.text:
                        return True
            except StaleElementReferenceException:
                if tentativa < max_tentativas - 1:
                    time.sleep(1)
                    continue
        return False
    except Exception as e:
        logging.error(f"Erro ao limpar pesquisa: {str(e)}")
        return False

def verificar_contato_existe(driver, telefone):
    try:
        search_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="3"]')
        if not search_box:
            return False, telefone
        search_box.clear()
        search_box.send_keys(telefone)
        time.sleep(0.5)
        search_box.send_keys(Keys.ENTER)
        time.sleep(0.5)
        message_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="10"]', timeout=3)
        if message_box:
            return True, telefone
        if not limpar_pesquisa(driver):
            return False, telefone
        if telefone.startswith("+55") and len(telefone) == 14:
            telefone_sem_9 = telefone[:5] + telefone[6:]
            search_box.clear()
            search_box.send_keys(telefone_sem_9)
            time.sleep(0.5)
            search_box.send_keys(Keys.ENTER)
            time.sleep(0.5)
            message_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="10"]', timeout=3)
            if message_box:
                return True, telefone_sem_9
        return iniciar_nova_conversa(driver, telefone)
    except Exception as e:
        logging.error(f"Erro ao verificar contato: {str(e)}")
        return False, telefone

def iniciar_nova_conversa(driver, telefone):
    try:
        numero_limpo = telefone.replace("+", "")
        url = f"https://web.whatsapp.com/send/?phone={numero_limpo}"
        driver.get(url)
        time.sleep(7)
        erro_elementos = driver.find_elements(By.XPATH, '//*[contains(text(), "O número de telefone compartilhado através de url é inválido.")]')
        if erro_elementos:
            if telefone.startswith("+55") and len(telefone) == 14:
                telefone_sem_9 = telefone[:5] + telefone[6:]
                numero_limpo = telefone_sem_9.replace("+", "")
                url = f"https://web.whatsapp.com/send/?phone={numero_limpo}"
                driver.get(url)
                time.sleep(7)
                erro_elementos = driver.find_elements(By.XPATH, '//*[contains(text(), "O número de telefone compartilhado através de url é inválido.")]')
                if erro_elementos:
                    return False, telefone_sem_9
                message_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="10"]', timeout=10)
                if message_box:
                    return True, telefone_sem_9
            return False, telefone
        message_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="10"]', timeout=7)
        return (True, telefone) if message_box else (False, telefone)
    except Exception as e:
        logging.error(f"Erro ao iniciar nova conversa: {str(e)}")
        return False, telefone

def minimizar_conversa(driver):
    try:
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.XPATH, '//div[@aria-label="Iniciando conversa"]'))
            )
        except Exception:
            pass
        try:
            notificacao = esperar_elemento(driver, '//div[@aria-label="Fechar"]')
            if notificacao:
                notificacao.click()
        except Exception:
            pass 
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.5)
        search_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="3"]')
        if search_box:
            search_box.click()
            return True
        return False
    except Exception as e:
        logging.error(f"Erro ao minimizar conversa: {str(e)}")
        return False

def enviar_mensagem_whatsapp(driver, telefone, mensagem, max_tentativas=3):
    for tentativa in range(max_tentativas):
        try:
            minimizar_conversa(driver)
            time.sleep(1)
            contato_existe, numero_valido = verificar_contato_existe(driver, telefone)
            if not contato_existe:
                logging.error(f"Contato não encontrado em nenhum formato: {telefone}")
                return False
            if numero_valido != telefone:
                logging.info(f"Usando formato alternativo do número: {numero_valido}")
            message_box = esperar_elemento(driver, '//div[@contenteditable="true"][@data-tab="10"]')
            if not message_box:
                logging.error(f"Campo de mensagem não encontrado (tentativa {tentativa + 1})")
                continue
            message_box.clear()
            for parte in [mensagem[i:i+50] for i in range(0, len(mensagem), 50)]:
                message_box.send_keys(parte)
                time.sleep(0.1)
            time.sleep(0.5)
            message_box.send_keys(Keys.ENTER)
            time.sleep(1.5)
            minimizar_conversa(driver)
            time.sleep(1)
            return True
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem (tentativa {tentativa + 1}): {str(e)}")
            if tentativa < max_tentativas - 1:
                time.sleep(2)
                continue
            return False

def processar_agendamentos(db_config):
    driver = None
    db = None
    cursor = None
    try:
        driver = iniciar_driver()
        if not driver:
            logging.error("Não foi possível iniciar o navegador.")
            return
        driver.get("https://web.whatsapp.com")
        logging.info("Aguardando carregamento do WhatsApp Web...")
        time.sleep(10)
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        query = """
            Você deve adicionar a query de busca dos agendamentos dentro do seu banco de dados
        """
        cursor.execute(query, (amanha,))
        agendas = cursor.fetchall()
        if not agendas:
            logging.info("Não há agendamentos para amanhã.")
            return
        total_agendas = len(agendas)
        logging.info(f"Encontrados {total_agendas} agendamentos para amanhã.")
        sucessos = 0
        falhas = 0

        horario_base_manha = datetime.strptime("07:00", "%H:%M")
        horario_base_tarde = datetime.strptime("13:00", "%H:%M")

        contador_manha = 0
        contador_tarde = 0

        for i, agenda in enumerate(agendas, 1):
            fone_provisorio, inicio, paciente = agenda
            telefone_formatado = formatar_telefone(fone_provisorio)
            logging.info(f"Processando {i}/{total_agendas}: {paciente}")
            minimizar_conversa(driver)
            time.sleep(1)

            if inicio.hour < 13:
                horario_comparecimento = horario_base_manha + timedelta(minutes=1 * contador_manha)
                contador_manha += 1
            else:
                horario_comparecimento = horario_base_tarde + timedelta(minutes=1 * contador_tarde)
                contador_tarde += 1

            horario_comparecimento_formatado = horario_comparecimento.strftime("%H:%M")

            mensagem = (
                f"*LEMBRETE*\n\n"
                f"Olá {paciente}, sou o assistente do *nome do estabelecimento*. Gostaria de lembrá-lo(a) de que você tem um agendamento.\n\n"
                f"*Data:* Amanhã\n"
                f"*Horário:* *{horario_comparecimento_formatado}*\n"
                f"Pedimos, por gentileza, que compareça com *10 minutos* de antecedência.\n\n"
                "Qualquer dúvida, estamos à disposição.\n\n"
                "*Obrigado!*"
            )
            sucesso = enviar_mensagem_whatsapp(driver, telefone_formatado, mensagem)
            if sucesso:
                logging.info(f"✓ Mensagem enviada para {paciente} ({telefone_formatado})")
                sucessos += 1
            else:
                logging.error(f"✗ Falha ao enviar mensagem para {paciente} ({telefone_formatado})")
                falhas += 1
            if i < total_agendas:
                tempo_espera = 3 if i % 10 != 0 else 5
                time.sleep(tempo_espera)
        logging.info(f"\nResumo do processamento:")
        logging.info(f"Total de agendamentos: {total_agendas}")
        logging.info(f"Mensagens enviadas com sucesso: {sucessos}")
        logging.info(f"Falhas no envio: {falhas}")
    except mysql.connector.Error as err:
        logging.error(f"Erro ao conectar ao MariaDB: {err}")
    except Exception as e:
        logging.error(f"Erro durante a execução: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if db and db.is_connected():
            db.close()
        if driver:
            driver.quit()

def verificar_conexao_internet():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

def main():
    logging.info("Iniciando o processo de envio de lembretes.")
    if not verificar_conexao_internet():
        logging.error("Sem conexão com a internet. O processo não pode continuar.")
        return
    db_config = {
       "host": "localhost",
        "user": "useuario do banco",
        "password": "senha do banco",
        "database": "nome do banco",
        "port": "porta do banco",
        "charset": "utf8mb4",
        "collation": "utf8mb4_general_ci"
    }
    try:
        db = mysql.connector.connect(**db_config)
        db.close()
        logging.info("Conexão com o banco de dados estabelecida com sucesso.")
        processar_agendamentos(db_config)
    except mysql.connector.Error as err:
        logging.error(f"Erro ao conectar ao banco de dados: {err}")

if __name__ == "__main__":
    main()
