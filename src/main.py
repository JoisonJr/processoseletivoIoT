from machine import Pin, I2C
from mpu6050 import MPU6050
import time

# Inicia a conexão I2C de ID=0 nos pinos 21 (SDA) e 22 (SCL)
i2c = I2C(0, scl = Pin(22), sda = Pin(21))

# Inicializa uma instância do MPU6050 denominada 'imu1', passando o endereço do I2C 
imu1 = MPU6050(i2c)

# Também é inicializada uma
btn1 = Pin(14, Pin.IN, Pin.PULL_DOWN)

# Definição das constantes de limite de tempo e de temperatura
LIMITE_TEMPO_PORTA_MS = 5000
LIMITE_VARIACAO_TEMP = 3.0

# Variáveis para monitorar os status dos erros 
alarmePortaAberta = False
alarmeTermico = False
estadoAnterior = False

# Flag para indicar se a porta está aberta ou não, e variável que registra o tempo de abertura para
# verificar se a porta foi aberta por mais tempo do que o limite
portaAberta = False
tsAbertura = 0

def checkBotao():
    global portaAberta, tsAbertura
    # Vale destacar que, agora com essa função dentro do while true:, que tem um sleep dentro, não é 
    # mais necessário implementar o debounce dentro da função para checar o botão
    portaAtual = (btn1.value() == 0)
    # Verifica se a porta foi aberta no instante atual para guardar o tempo de abertura e verificar
    # o momemto em que o alarme deverá ser ativado
    if portaAtual and not portaAberta:
        tsAbertura = time.ticks_ms()
    portaAberta = portaAtual


def checkAlarmePortaAberta():
  global alarmePortaAberta
  # O alarme da porta aberta é ativo se o tempo atual - tempo de abertura foi maior ou
  # igual ao limite estabelecido
  if portaAberta == True:
    alarmePortaAberta = time.ticks_diff(time.ticks_ms(), tsAbertura) >= LIMITE_TEMPO_PORTA_MS
  else:
    alarmePortaAberta = False

# Número máximo de leituras para serem colocadas na lista
MAX_LEITURAS = 100
# Temperatura de referência, que é a média das últimas MAX_LEITURAS leituras
tempRef = 0
# Soma de todas as leituras para a obtenção de tempRef
somaLeituras = 0
# Lista das 10 últimas leituras
listaLeituras = []

def getImuTemp():
  global somaLeituras, tempRef, alarmeTermico
  try:
    # Obtém o valor atual de temperatura do MPU6050
    tempAtual = imu1.read_temperature()

    # Caso exista alguma leitura anterior já existente, é feita a verificação. Como a verificação 
    # serve apenas para o sobreaquecimento dos componentes, como estava na descrição do README,
    # não é necessário usar abs()
    if len(listaLeituras) > 0:
        alarmeTermico = (tempAtual - tempRef) >= LIMITE_VARIACAO_TEMP

    # Coleta a temperatura de referência apenas quando a porta estiver fechada
    if not portaAberta and not alarmeTermico:
        # Anexa a leitura atual à lista e, caso a lista esteja cheia, descarta a leitura mais antiga
        listaLeituras.append(tempAtual)
        somaLeituras = somaLeituras + tempAtual
        # Caso a lista de leituras fique cheia, subtrai o valor da leitura mais antiga e o retira da
        # lista de leituras
        if len(listaLeituras) > MAX_LEITURAS:
            somaLeituras = somaLeituras - listaLeituras.pop(0)
        
        # Atualiza a temperatura de referência
        tempRef = somaLeituras / len(listaLeituras)
  except Exception as e:
    print("Erro ao ler o MPU6050: ", e)

# Salva o estado dos alarmes anteriores para evitar que as mensagens de erro sejam continuamente
# impressas enquanto o erro existir
alarmePortaAnterior = False
alarmeTermicoAnterior = False

# Imprime o status atual do sistema
def printStatus():
  global alarmePortaAberta, alarmeTermico, estadoAnterior
  global alarmePortaAnterior, alarmeTermicoAnterior
  # Toda essa "lógica" de um tipo de alarme e seu anterior é para evitar uma "contínua impressão"
  # do alarme enquanto o sistema está neste estado, e a variável estadoAnterior é utilizada para
  # imprimir a mensagem de sistema normalizado depois do término de um alerta
  if alarmePortaAberta and not alarmePortaAnterior:
    print("ALERTA: Porta aberta por muito tempo!")
  if alarmeTermico and not alarmeTermicoAnterior:
    print("ALERTA: Degradacao termica detectada!")
  if not (alarmePortaAberta or alarmeTermico) and estadoAnterior:
    # Delay para imprimir a mensagem, pois estava dando erro no teste 3 do github actions
    time.sleep_ms(700)
    print("Status: Sistema Normalizado.")

  # Por fim, os alarmes anteriores são atualizados com os estados atuais para a próxima iteração, 
  # bem como o estadoAnterior
  alarmePortaAnterior = alarmePortaAberta
  alarmeTermicoAnterior = alarmeTermico
  estadoAnterior = alarmePortaAberta or alarmeTermico
  
print("Sistema de Monitoramento Inicializado")

# Por fim, o loop executa todas as funções criadas anteriormente
while True:
    checkBotao()
    checkAlarmePortaAberta()
    getImuTemp()
    printStatus()
    time.sleep_ms(50)