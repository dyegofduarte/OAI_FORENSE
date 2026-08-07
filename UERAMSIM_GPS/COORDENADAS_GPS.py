#!/usr/bin/env python3
"""
COORDENADAS_GPS.py — Injeta coordenadas GPS em tempo real no UERANSIM gNB.

O arquivo JSON gerado é lido pelo nr-gnb a cada mensagem NGAP enviada ao AMF,
sem necessidade de reiniciar nenhum container ou NF do core 5G.
"""

import json
import os
import subprocess
import sys

# ── Configurações padrão ────────────────────────────────────────────────────
# Salva o JSON no mesmo diretório onde este script está localizado
_SCRIPT_DIR            = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT         = os.path.join(_SCRIPT_DIR, "ueransim_gps.json")
DEFAULT_CONTAINER      = "ueransim"
DEFAULT_CONTAINER_PATH = "/ueransim/gps_position.json"


# ── Utilidades de entrada ────────────────────────────────────────────────────
def ler(prompt: str, exemplo: str = "", obrigatorio: bool = True) -> str:
    """Exibe prompt com exemplo e lê entrada do usuário."""
    dica = f"  (ex: {exemplo})" if exemplo else ""
    while True:
        try:
            valor = input(f"  {prompt}{dica}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nOperação cancelada.")
            sys.exit(0)
        if valor:
            return valor
        if not obrigatorio:
            return ""
        print("  ⚠  Campo obrigatório. Por favor, informe um valor.")


def ler_float(prompt: str, exemplo: str, minimo: float, maximo: float,
              obrigatorio: bool = True) -> float | None:
    """Lê um número decimal com validação de intervalo."""
    while True:
        raw = ler(prompt, exemplo, obrigatorio)
        if not raw and not obrigatorio:
            return None
        try:
            valor = float(raw)
        except ValueError:
            print(f"  ⚠  Valor inválido '{raw}'. Digite um número decimal.")
            continue
        if not (minimo <= valor <= maximo):
            print(f"  ⚠  Fora do intervalo permitido [{minimo} .. {maximo}].")
            continue
        return valor


def ler_sim_nao(prompt: str, padrao: bool = False) -> bool:
    """Lê resposta S/N com valor padrão."""
    opcoes = "S/n" if padrao else "s/N"
    while True:
        try:
            raw = input(f"  {prompt} [{opcoes}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\nOperação cancelada.")
            sys.exit(0)
        if not raw:
            return padrao
        if raw in ("s", "sim", "y", "yes"):
            return True
        if raw in ("n", "nao", "não", "no"):
            return False
        print("  ⚠  Digite S para sim ou N para não.")


def separador(titulo: str = "") -> None:
    linha = "─" * 57
    if titulo:
        print(f"\n  ┌{linha}┐")
        print(f"  │  {titulo:<55}│")
        print(f"  └{linha}┘")
    else:
        print(f"  {linha}")


# ── Lógica principal ─────────────────────────────────────────────────────────
def coletar_dados() -> dict:
    """Solicita interativamente todas as coordenadas ao usuário."""

    print()
    print("  ╔═════════════════════════════════════════════════════════╗")
    print("  ║           INJEÇÃO DE COORDENADAS GPS — UERANSIM         ║")
    print("  ║         Pressione Ctrl+C a qualquer momento p/ sair     ║")
    print("  ╚═════════════════════════════════════════════════════════╝")

    # ── Latitude ──────────────────────────────────────────────────────────────
    separador("1 · LATITUDE  (obrigatório)")
    print("    Valores válidos: -90.0 (Polo Sul) até +90.0 (Polo Norte)")
    print("    Use sinal negativo para o hemisfério Sul.")
    lat = ler_float("Latitude", "-15.7942", -90.0, 90.0)

    # ── Longitude ─────────────────────────────────────────────────────────────
    separador("2 · LONGITUDE  (obrigatório)")
    print("    Valores válidos: -180.0 (Oeste) até +180.0 (Leste)")
    print("    Use sinal negativo para o hemisfério Oeste.")
    lon = ler_float("Longitude", "-47.8822", -180.0, 180.0)

    # ── Altitude ──────────────────────────────────────────────────────────────
    separador("3 · ALTITUDE  (opcional — Enter para ignorar)")
    print("    Metros acima do elipsoide WGS84.")
    print("    Deixe em branco se não souber ou não for necessário.")
    alt = ler_float("Altitude (m)", "1172.0", -500.0, 99999.0, obrigatorio=False)

    # ── Campos extras ─────────────────────────────────────────────────────────
    separador("4 · CAMPOS EXTRAS  (opcional)")
    print("    Adicione campos adicionais ao JSON (velocidade, rumo, etc.).")
    print("    Formato: nome=valor  (ex: speed=72.5  |  heading=180.0  |  hdop=1.2)")
    print("    Digite um campo por vez. Deixe em branco para encerrar.")

    extras: dict = {}
    while True:
        raw = ler("Campo extra", "speed=72.5", obrigatorio=False)
        if not raw:
            break
        if "=" not in raw:
            print("  ⚠  Use o formato  NOME=VALOR  (ex: speed=72.5)")
            continue
        chave, val = raw.split("=", 1)
        chave = chave.strip()
        val   = val.strip()
        if not chave:
            print("  ⚠  O nome do campo não pode ser vazio.")
            continue
        if chave in ("lat", "lon", "alt"):
            print(f"  ⚠  '{chave}' já foi informado acima. Ignorado.")
            continue
        try:
            val_conv: float | int | str = float(val) if "." in val else int(val)
        except ValueError:
            val_conv = val  # manter como string
        extras[chave] = val_conv
        print(f"  ✓  {chave} = {val_conv}")

    separador()

    # Montar dicionário final
    dados: dict = {"lat": round(lat, 6), "lon": round(lon, 6)}
    if alt is not None:
        dados["alt"] = round(alt, 2)
    dados.update(extras)

    return dados


# ── Escrita do arquivo ────────────────────────────────────────────────────────
def escrever_posicao(dados: dict, caminho: str) -> None:
    """Grava o JSON de forma atômica (rename) para evitar leitura parcial."""
    tmp = caminho + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(caminho)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, caminho)


# ── Verificação do volume ─────────────────────────────────────────────────────
def verificar_sincronizacao() -> bool:
    """Confirma que o arquivo existe no container via bind mount (sem docker cp)."""
    try:
        resultado = subprocess.run(
            ["docker", "exec", DEFAULT_CONTAINER,
             "cat", DEFAULT_CONTAINER_PATH],
            capture_output=True, text=True,
        )
        return resultado.returncode == 0
    except FileNotFoundError:
        return False


# ── Exibição do resultado ─────────────────────────────────────────────────────
def exibir_resultado(dados: dict, sincronizado: bool) -> None:
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │          COORDENADAS GPS INJETADAS COM SUCESSO          │")
    print("  └─────────────────────────────────────────────────────────┘")
    print(f"  Latitude   : {dados['lat']:+.6f}°")
    print(f"  Longitude  : {dados['lon']:+.6f}°")
    if "alt" in dados:
        print(f"  Altitude   : {dados['alt']:.1f} m")
    for chave, valor in dados.items():
        if chave not in ("lat", "lon", "alt"):
            print(f"  {chave:<11}: {valor}")
    print()
    print(f"  Arquivo    : {DEFAULT_OUTPUT}")
    status = "✓ visível no container (volume mount)" if sincronizado else "⚠ container não encontrado"
    print(f"  Container  : {DEFAULT_CONTAINER}:{DEFAULT_CONTAINER_PATH}  [{status}]")
    print()
    print("  O gNB lerá a nova posição na próxima mensagem NGAP.")
    print("  Verificar  : docker logs ueransim 2>&1 | grep GPS-INJECT")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    dados = coletar_dados()

    # Grava atomicamente no host; o bind mount propaga imediatamente ao container
    escrever_posicao(dados, DEFAULT_OUTPUT)

    # Verifica que o container enxerga o arquivo pelo volume
    sincronizado = verificar_sincronizacao()

    exibir_resultado(dados, sincronizado)


if __name__ == "__main__":
    main()
