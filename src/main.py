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
  # Como o controle de tempo no while True garante a execução a cada 50ms,
  # o efeito de debounce indireto é mantido.
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

# Variáveis para gerenciar o delay não-bloqueante de normalização do sistema
aguardandoNormalizacao = False
tsInicioNormalizacao = 0
DELAY_NORMALIZACAO_MS = 700

# Imprime o status atual do sistema
def printStatus():
  global alarmePortaAberta, alarmeTermico, estadoAnterior
  global alarmePortaAnterior, alarmeTermicoAnterior
  global aguardandoNormalizacao, tsInicioNormalizacao

  if alarmePortaAberta and not alarmePortaAnterior:
    print("ALERTA: Porta aberta por muito tempo!")
  if alarmeTermico and not alarmeTermicoAnterior:
    print("ALERTA: Degradacao termica detectada!")

  # Verifica se o sistema acabou de normalizar
  if not (alarmePortaAberta or alarmeTermico) and estadoAnterior:
    aguardandoNormalizacao = True
    tsInicioNormalizacao = time.ticks_ms()

  # Se uma nova anomalia surgir durante os 700ms de espera, cancelamos a flag de normalização
  if alarmePortaAberta or alarmeTermico:
    aguardandoNormalizacao = False

  # Processa o envio da mensagem de normalização após os 700ms sem travar o código
  if aguardandoNormalizacao:
    if time.ticks_diff(time.ticks_ms(), tsInicioNormalizacao) >= DELAY_NORMALIZACAO_MS:
      print("Status: Sistema Normalizado.")
      aguardandoNormalizacao = False # Reseta a flag após imprimir

  # Atualiza os estados anteriores para a próxima iteração
  alarmePortaAnterior = alarmePortaAberta
  alarmeTermicoAnterior = alarmeTermico
  estadoAnterior = alarmePortaAberta or alarmeTermico

print("Sistema de Monitoramento Inicializado")

# Variáveis de controle de tempo para o loop principal
tsUltimoLoop = time.ticks_ms()
INTERVALO_LOOP_MS = 50

# Por fim, o loop executa todas as funções criadas anteriormente
while True:
  tempoAtual = time.ticks_ms()

  # Garante que as checagens só ocorram a cada 50ms, liberando a CPU entre os ciclos
  if time.ticks_diff(tempoAtual, tsUltimoLoop) >= INTERVALO_LOOP_MS:
    tsUltimoLoop = tempoAtual # Atualiza a marcação de tempo

  checkBotao()
  checkAlarmePortaAberta()
  getImuTemp()
  printStatus()