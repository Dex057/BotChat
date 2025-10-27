import time
import os
import threading
import webbrowser
from flask import Flask, render_template, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, WebDriverException

# --- Configuração ---
PATH_DRIVER = r"C:\drivers\chromedriver.exe"
URL_BASE = "https://chat.sonax.net.br/"
URL_CHAT = "https://chat.sonax.net.br/app/chat"

# --- Credenciais ---
LOGIN_EMAIL = "atendente02@amazoninf.com.br"
LOGIN_SENHA = "Amazon@2025"

# --- XPaths Login ---
XPATH_CAMPO_EMAIL = "/html/body/app-root/app-login/div/div[1]/div/div[1]/input"
XPATH_CAMPO_SENHA = "/html/body/app-root/app-login/div/div[1]/div/div[2]/input"
XPATH_BOTAO_ENTRAR = "/html/body/app-root/app-login/div/div[1]/div/button"

# --- XPaths Chat (Confirmados) ---
XPATH_CONTADOR_BOT = "/html/body/app-root/app-layout/ng-sidebar-container/div/div/app-chat/app-content/main/div/div/div[1]/app-portlet/div/div/div/div[2]/div[1]/span[1]/div/span"
XPATH_CONTADOR_FILA = "/html/body/app-root/app-layout/ng-sidebar-container/div/div/app-chat/app-content/main/div/div/div[1]/app-portlet/div/div/div/div[2]/div[1]/span[2]/div/span"
XPATH_ABA_FILA = "/html/body/app-root/app-layout/ng-sidebar-container/div/div/app-chat/app-content/main/div/div/div[1]/app-portlet/div/div/div/div[2]/div[1]/span[2]"
XPATH_LISTA_CONTAINER = r"/html/body/app-root/app-layout/ng-sidebar-container/div/div/app-chat/app-content/main/div/div/div/app-portlet/div/div/div/div[2]/div[3]/app-protocols-list-card"
XPATH_PRIMEIRO_CHAT_FILA = r"/html/body/app-root/app-layout/ng-sidebar-container/div/div/app-chat/app-content/main/div/div/div/app-portlet/div/div/div/div[2]/div[3]/app-protocols-list-card/div"
XPATH_BOTAO_ASSUMIR = "//button[contains(., 'Assumir Atendimento')]"
XPATH_BOTAO_CONFIRMA_SIM = "(//button[contains(., 'SIM')])[last()]"

# --- Aplicação Flask e Estado Global ---
app = Flask(__name__)
driver = None
wait = None
bot_ativo = False
status_message = "A iniciar..."
bot_thread = None 

def toggle_bot_status():
    global bot_ativo, status_message
    bot_ativo = not bot_ativo
    status_message = "A monitorizar..." if bot_ativo else "PAUSADO!"

def setup_driver_and_login():
    global driver, wait, status_message
    try:
        options = webdriver.ChromeOptions()
        service = webdriver.ChromeService(executable_path=PATH_DRIVER)
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10) 
        
        status_message = "A aceder à página de login..."
        driver.get(URL_BASE + "login") 

        status_message = "A preencher credenciais..."
        wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_CAMPO_EMAIL))).send_keys(LOGIN_EMAIL)
        wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_CAMPO_SENHA))).send_keys(LOGIN_SENHA)
        
        status_message = "A clicar em 'Entrar'..."
        wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_BOTAO_ENTRAR))).click()
        
        status_message = "Login efetuado. A aguardar chat..."
        wait.until(EC.url_contains(URL_CHAT)) 
        wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_CONTADOR_FILA))) 

        status_message = "Chat carregado. Bot pronto."
        return True

    except Exception as e:
        status_message = f"ERRO CRITICO AO INICIAR/LOGAR: {e}"
        return False

def bot_loop():
    global status_message, bot_ativo, driver, wait
    time.sleep(2)
    status_message = "A monitorizar..."

    while True:
        current_step = "" # Para saber onde falhou
        try:
            if not bot_ativo:
                time.sleep(1)
                continue

            try:
                current_step = "ler contadores"
                contador_bot_texto = driver.find_element(By.XPATH, XPATH_CONTADOR_BOT).text
                contador_fila_texto = driver.find_element(By.XPATH, XPATH_CONTADOR_FILA).text
                bot_count = int(contador_bot_texto) if contador_bot_texto.isdigit() else 0
                fila_count = int(contador_fila_texto) if contador_fila_texto.isdigit() else 0
            except (NoSuchElementException, StaleElementReferenceException):
                # Se der erro a ler, espera 1s e tenta de novo
                bot_count, fila_count = 0, 0
                time.sleep(1) 
                continue 

            # --- LÓGICA DE DECISÃO ---
            if fila_count > 0:
                original_status = status_message # Guarda o status caso precise restaurar
                try:
                    current_step = "iniciar sequencia"
                    status_message = f"Chat na Fila! ({fila_count}). A iniciar sequencia..."

                    # Passo 1: Clicar na Aba Fila
                    current_step = "clicar Aba Fila"
                    wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_ABA_FILA))).click()
                    time.sleep(0.3)
                    
                    # Passo 1.5: Esperar que a lista de chats apareça
                    current_step = "esperar Lista"
                    wait.until(EC.visibility_of_element_located((By.XPATH, XPATH_LISTA_CONTAINER)))
                    
                    # Passo 2: Clicar no Primeiro Contacto da Lista
                    current_step = "clicar Contacto"
                    wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_PRIMEIRO_CHAT_FILA))).click()
                    time.sleep(2) 
                    
                    # Passo 3: Clicar em "Assumir Atendimento"
                    current_step = "clicar Assumir"
                    wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_BOTAO_ASSUMIR))).click()
                    
                    # Passo 4: Clicar em "Sim" na confirmação
                    current_step = "clicar SIM"
                    wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_BOTAO_CONFIRMA_SIM))).click()
                    
                    current_step = "finalizar"
                    status_message = "Confirmado! A monitorizar..."
                    time.sleep(2) # Pausa para mostrar sucesso

                except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
                    # Se QUALQUER passo da sequencia falhar, assume que foi roubado
                    status_message = f"Falha ao {current_step}. Chat provavelmente assumido. A verificar..."
                    print(f"INFO: Falha na sequencia ({current_step}). Chat roubado?") 
                    time.sleep(1) # Pausa antes de re-verificar
                    continue # Volta imediatamente para o início do while para re-ler contadores

                except WebDriverException as e: # Trata crash do navegador separadamente
                     raise e # Re-levanta a exceção para ser apanhada pelo bloco exterior
                except Exception as e: # Apanha qualquer outro erro inesperado DENTRO da sequencia
                     print(f"Erro inesperado DENTRO da sequencia ({current_step}): {e}")
                     status_message = f"Erro inesperado ({current_step}): {e}. A tentar..."
                     time.sleep(1)
                     continue # Volta ao início do loop principal
            
            elif bot_count > 0 and fila_count == 0:
                current_step = "atualizar Fila (Bot > 0)"
                status_message = f"Chat no Bot ({bot_count}). A atualizar Fila..."
                try:
                    wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_ABA_FILA))).click()
                except (TimeoutException, StaleElementReferenceException):
                    status_message = "Erro ao clicar Fila. A tentar..."
                time.sleep(0.7) 
            
            else:
                current_step = "monitorizar"
                status_message = f"A monitorizar... (Bot: {bot_count}, Fila: {fila_count})"
                time.sleep(1) # Pausa normal de 1 segundo

        except WebDriverException:
            current_step = "crash handler"
            status_message = "Navegador fechado! Reinicie."
            bot_ativo = False
            break 
            
        except Exception as e:
            status_message = f"Erro inesperado ({current_step}): {e}"
            print(f"Erro inesperado ({current_step}): {e}") 
            time.sleep(2)

# --- Rotas Flask ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def get_status():
    return jsonify({"status": status_message, "ativo": bot_ativo})

@app.route('/toggle', methods=['POST'])
def toggle_bot():
    global status_message
    if driver is None or not bot_thread.is_alive():
        status_message = "CRASH! Navegador fechado. Reinicie."
        return jsonify({"status": status_message, "ativo": False})
    toggle_bot_status()
    return jsonify({"status": status_message, "ativo": bot_ativo})

# --- Início ---
if __name__ == "__main__":
    print("Iniciando navegador e login...")
    if not setup_driver_and_login():
        print("Falha. Fechando.")
        input("Pressione Enter.")
    else:
        bot_ativo = True 
        print("Login OK. Iniciando bot...")
        bot_thread = threading.Thread(target=bot_loop, daemon=True)
        bot_thread.start()
        print("Abrindo painel web...")
        threading.Timer(2.0, lambda: webbrowser.open('http://127.0.0.1:5000')).start() 
        print("Servidor iniciado.")
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

