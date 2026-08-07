# Tutorial: Injeção de Coordenadas GPS em Tempo Real usando NRPPa (UERANSIM + OAI 5G Core)

## Visão Geral

Este tutorial descreve a solução completa para transmissão de coordenadas GPS reais (e dinâmicas) a partir do UERANSIM (gNB) diretamente para o **LMF (Location Management Function)** do núcleo OAI 5G. A grande vantagem desta solução é que ela **não exige nenhuma modificação nas NFs do Core 5G da OAI**; toda a lógica do protocolo de localização foi embutida nativamente dentro da imagem customizada do UERANSIM.

### Princípio de funcionamento

1. O script Python (`COORDENADAS_GPS.py`) capta ou gera coordenadas e salva no arquivo local `/tmp/ueransim_gps.json`.
2. O `docker-compose.yaml` (ou similar) injeta esse arquivo para dentro do container do UERANSIM via *bind mount*.
3. O `nr-gnb` (UERANSIM), agora munido de um interceptador NRPPa via NGAP, lê as coordenadas deste arquivo dinamicamente (`GpsInjector`).
4. Quando o LMF envia uma requisição de posicionamento (`PositioningInformationRequest` ou `MeasurementRequest`) envelopada via NGAP `DownlinkUEAssociatedNRPPaTransport`, o UERANSIM decodifica a ASN.1, lê as coordenadas do GPS e responde imediatamente envelopando um `UplinkUEAssociatedNRPPaTransport` de volta para o AMF/LMF.

> [!TIP]
> **Por que NRPPa?** O protocolo NRPPa (3GPP TS 38.455) é o padrão oficial para troca de dados de assistência e localização entre a estação base (gNB) e o LMF. Utilizá-lo permite que qualquer core 5G compatível processe os dados de forma padronizada.

---

## 1. Obtenção da Imagem UERANSIM (NRPPa-enabled)

Para utilizar esta solução em qualquer núcleo 5G, você precisará da imagem Docker do UERANSIM já modificada com o suporte NRPPa. Você tem duas opções: utilizar uma imagem pré-compilada (Recomendado) ou compilar o código do zero.

### Opção 1: Download da Imagem Pré-compilada (Recomendado)

Se você já possuir a imagem hospedada em um *registry* (ex: Docker Hub), não é necessário compilar nada. Basta baixar a imagem diretamente no servidor de destino:

```bash
# TODO: Atualize a URL abaixo com o repositório onde a imagem será hospedada
docker pull seu_usuario/ueransim:gps-nrppa
```

> **Nota:** Certifique-se de que a tag no seu `docker-compose.yaml` (Passo 3) corresponda ao nome da imagem baixada.

### Opção 2: Compilação do zero (Avançado)

Caso você queira recriar o ambiente a partir de um repositório limpo do UERANSIM, o processo exige injetar o protocolo NRPPa diretamente no código C++ do simulador, uma vez que ele não é suportado nativamente.

**Processo de modificação (Resumo):**
1. **Extração do Protocolo (ASN.1):** Copie todos os arquivos `.c` e `.h` referentes ao protocolo NRPPa (3GPP TS 38.455) do repositório OpenAirInterface LMF (`oai-cn5g-lmf/src/nrppa/`) para dentro do UERANSIM (ex: `UERANSIM/src/asn/nrppa/`).
2. **Sistema de Build (CMake):** Crie um `CMakeLists.txt` na nova pasta para gerar uma biblioteca estática (`asn-nrppa`) e faça o *link* desta biblioteca no `CMakeLists.txt` principal do UERANSIM.
3. **Módulo de Leitura do GPS (`gps_injector.hpp`):** Implemente uma classe Thread-Safe em C++ para ler de forma contínua o arquivo JSON injetado `/ueransim/gps_position.json`.
4. **Interceptação NGAP:** No arquivo `src/gnb/ngap/transport.cpp`, adicione o tratamento (switch case) para despachar mensagens do tipo `DownlinkUEAssociatedNRPPaTransport` recebidas do AMF.
5. **Decodificação e Resposta (`nrppa.cpp`):** Crie o decodificador que converte o *payload* do NGAP para pacotes NRPPa (`ngap_encode::Decode<NRPPA_PDU_t>`). Ao receber um `PositioningInformationRequest`, popule a estrutura de resposta com a `lat` e `lon` lidas do `GpsInjector` e envie um `UplinkUEAssociatedNRPPaTransport` de volta.

Após realizar essas modificações no código-fonte, construa a imagem executando no diretório base do UERANSIM:

```bash
docker build -t ueransim:gps-nrppa .
```

---

## 2. Preparação do Script de Coordenadas (Python)

O script `COORDENADAS_GPS.py` já está preparado para exportar continuamente os valores para `/tmp/ueransim_gps.json`. 
Não é necessário alterá-lo. Para iniciar a emissão das coordenadas na máquina host:

```bash
python3 COORDENADAS_GPS.py
```

O arquivo JSON atualizado conterá:
```json
{ "lat": -15.7942, "lon": -47.8822, "alt": 1172.0 }
```

---

## 3. Modificação do arquivo `docker-compose`

A única etapa necessária no momento do deploy da infraestrutura é assegurar que o seu container UERANSIM utilize a imagem customizada e tenha acesso de leitura ao JSON gerado pelo Python. 

No arquivo de compose do seu simulador (por exemplo, `docker-compose-ueransim.yaml` ou `docker-compose.yaml` no diretório do fed/LMF), faça as seguintes alterações exclusivas no serviço **`ueransim`**:

```yaml
  ueransim:
    # 1. Modifique a imagem original para a imagem que acabamos de construir
    image: ueransim:gps-nrppa
    container_name: ueransim
    volumes:
      # 2. Adicione este bind mount para expor as coordenadas em tempo real ao gNB
      - ueransim_gps.json:/ueransim/gps_position.json:ro
      - ./config:/ueransim/config
    environment:
      # (Opcional, se sua config solicitar) Diga ao gNB onde ler o GPS
      - GPS_POSITION_FILE=/ueransim/gps_position.json
    networks:
      - oai-public-access
    # Demais configurações (command, sysctls, cap_add) seguem inalteradas...
```

> [!IMPORTANT]
> **Modificações Restritas:** Note que nenhuma modificação em AMF, SMF, UPF ou LMF é feita neste compose. Eles utilizam as imagens e tags *upstream* da OpenAirInterface inalteradas.

---

## 4. Testando a Implementação

Com a rede iniciada e o script Python rodando no host:

1. Suba a rede core 5G com LMF (`docker-compose up -d ...`).
2. Conecte o UE.
3. Observe os logs do container do UERANSIM:
   ```bash
   docker logs -f ueransim
   ```
4. Durante a fase de registro (ou sempre que o LMF disparar sondagens do UE), você verá mensagens no UERANSIM afirmando:
   * `"Received DownlinkUEAssociatedNRPPaTransport from AMF"`
   * `"Received NRPPa PositioningInformationRequest"`
   * Em seguida, o UERANSIM decodifica o arquivo do GPS e injeta a lat/lon real enviada via NRPPa Uplink.

Isso garante que toda a topologia de Localização 5G enxergará as coordenadas controladas pelo seu script `COORDENADAS_GPS.py` instantaneamente!
