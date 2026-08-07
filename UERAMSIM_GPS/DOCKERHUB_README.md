# UERANSIM com Suporte a NRPPa (NR Positioning Protocol A)

Esta imagem é um *fork* customizado do [UERANSIM](https://github.com/aligungr/UERANSIM) que integra o **NRPPa (3GPP TS 38.455)** diretamente no gNB. Ela foi projetada especificamente para injetar coordenadas GPS reais e dinâmicas em uma Rede Core 5G (como o OpenAirInterface - OAI) através da LMF (Location Management Function).

## Principais Funcionalidades

*   **Suporte Nativo a NRPPa:** O gNB está equipado com mais de 350 definições ASN.1 do protocolo NRPPa.
*   **Sem Modificações no Core:** Integração perfeita com Redes Core 5G não modificadas (AMF/SMF/UPF/LMF) usando as requisições de posicionamento padrão do 3GPP.
*   **Injeção de GPS em Tempo Real:** Lê continuamente as coordenadas a partir de um arquivo JSON. Não é necessário reiniciar o gNB para atualizar sua localização.
*   **Interceptação NGAP:** Decodifica automaticamente mensagens `DownlinkUEAssociatedNRPPaTransport` vindas da AMF e responde com `UplinkUEAssociatedNRPPaTransport` contendo uma `PositioningInformationResponse`.

## Como usar esta imagem

Esta imagem deve ser utilizada como substituta direta para a imagem padrão do UERANSIM no seu arquivo `docker-compose.yaml`.

### 1. O Arquivo de Posição GPS
Crie um arquivo JSON (ex., `ueransim_gps.json`) na sua máquina host que será constantemente atualizado com as coordenadas que você deseja injetar:
```json
{ "lat": -15.7942, "lon": -47.8822, "alt": 1172.0 }
```

### 2. Configuração do Docker Compose
Atualize o seu `docker-compose.yaml` para usar esta imagem e montar o arquivo JSON como um volume:

```yaml
  ueransim:
    image: dyegofduarte/ueramsim_gps:latest
    container_name: ueransim
    volumes:
      - /caminho/no/host/ueransim_gps.json:/ueransim/gps_position.json:ro
      - ./config:/ueransim/config
    environment:
      - GPS_POSITION_FILE=/ueransim/gps_position.json
    networks:
      - oai-public-access
    # Outras configurações padrão do UERANSIM (cap_add, devices, etc.)
```

## Como funciona nos bastidores

Diferente do UERANSIM padrão, que apenas reporta as identidades de célula (CGI/TAC) via `UserLocationInformationNR` do protocolo NGAP, esta imagem customizada compreende nativamente as requisições da Location Management Function (LMF).

Quando a rede core interroga o UE/gNB sobre posicionamento:
1. O gNB recebe uma mensagem NGAP contendo um *payload* NRPPa.
2. O módulo interno `GpsInjector` faz a leitura segura da latitude e longitude atuais a partir do arquivo JSON montado no container.
3. O gNB constrói uma mensagem `PositioningInformationResponse` ou `MeasurementResponse` em conformidade com o padrão 3GPP.
4. As coordenadas são enviadas de volta ao LMF, ficando disponíveis para os Serviços de Localização (LCS) e de análise (ex: NWDAF).

---
*Construído para pesquisas e emulação avançada de posicionamento em 5G.*
