# Importando as bibliotecas necessárias
import os
import subprocess
import sys
import argparse
from pathlib import Path
import json
import re

# --- Bloco de Configuração ---
DEFAULT_SEARCH_QUERY = "diabetes health"
DEFAULT_OUTPUT_PATH = "datasets/raw"
DEFAULT_NUM_DATASETS = 1
# NOVO: Nome do arquivo de log
LOG_FILE = "download_log.txt"

# --- NOVAS FUNÇÕES DE LOG ---

def read_log():
    """Lê o arquivo de log e retorna um conjunto com os nomes dos datasets já baixados."""
    log_path = Path(LOG_FILE)
    if not log_path.exists():
        return set() # Retorna um conjunto vazio se o log não existe
    
    with open(log_path, 'r', encoding='utf-8') as f:
        # Usamos set() para ter uma busca mais rápida (O(1))
        return set(line.strip() for line in f if line.strip())

def write_to_log(dataset_name):
    """Adiciona o nome de um dataset ao arquivo de log."""
    log_path = Path(LOG_FILE)
    print(f"✍️  Registrando '{dataset_name}' no log...")
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"{dataset_name}\n")

# --- Funções Auxiliares (sem grandes mudanças) ---

def check_kaggle_credentials():
    """Verifica se o arquivo de credenciais do Kaggle existe e é válido."""
    kaggle_json_path = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json_path.exists():
        print("❌ ERRO: Arquivo 'kaggle.json' não encontrado.")
        return False
    try:
        with open(kaggle_json_path, 'r') as f:
            credentials = json.load(f)
            if 'username' not in credentials or 'key' not in credentials:
                print("❌ ERRO: Credenciais inválidas.")
                return False
    except (json.JSONDecodeError, Exception) as e:
        print(f"❌ ERRO: Não foi possível ler o arquivo de credenciais: {e}")
        return False
    print("✅ Credenciais do Kaggle encontradas e válidas.")
    return True

def check_kaggle_cli():
    """Verifica se a CLI do Kaggle está instalada e acessível."""
    try:
        result = subprocess.run(["kaggle", "--version"], capture_output=True, text=True, check=True)
        print(f"✅ Kaggle CLI encontrada: {result.stdout.strip()}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"❌ ERRO ao verificar a CLI do Kaggle: {e}")
        return False

def validate_dataset_name(dataset_name):
    """Valida o formato do nome do dataset."""
    if not dataset_name or '/' not in dataset_name or len(dataset_name.split('/')) != 2:
        print(f"❌ ERRO: Nome do dataset '{dataset_name}' inválido.")
        return False
    return True

def search_datasets(query, limit=10):
    """Busca por datasets no Kaggle e retorna uma lista dos melhores resultados."""
    print(f"🔎 Buscando por datasets com o termo: '{query}'...")
    command = ["kaggle", "datasets", "list", "--search", query, "--sort-by", "votes"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) < 3: return []
        
        refs = [line.split()[0] for line in lines[2:] if '/' in line.split()[0]]
        print(f"✅ Busca encontrou {len(refs)} datasets relevantes.")
        return refs[:limit]
    except subprocess.CalledProcessError as e:
        print(f"❌ ERRO: Falha ao buscar por datasets: {e.stderr}")
        return []

def download_dataset(dataset, path):
    """Baixa um único dataset. Retorna True em sucesso, False em falha."""
    dataset_folder = Path(path) / dataset.split('/')[1]
    dataset_folder.mkdir(parents=True, exist_ok=True)
    
    command = ["kaggle", "datasets", "download", "-d", dataset, "-p", str(dataset_folder), "--unzip"]
    print(f"📥 Baixando '{dataset}' para '{dataset_folder}'...")
    
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ Download de '{dataset}' concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ERRO: Falha ao baixar o dataset '{dataset}'.")
        # Mostra o erro real do Kaggle, que é muito útil para depurar
        error_message = e.stderr.strip()
        if "404" in error_message:
            print("📝 Motivo: Dataset não encontrado (Erro 404). Verifique o nome.")
        elif "403" in error_message:
            print("📝 Motivo: Acesso negado (Erro 403). Verifique suas credenciais ou aceite as regras do dataset no site.")
        else:
            print(f"📝 Detalhes: {error_message}")
        return False

# --- BLOCO PRINCIPAL (MODIFICADO COM A LÓGICA DE LOG) ---

def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Busca e baixa datasets NOVOS do Kaggle, registrando-os em um log.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("-s", "--search", default=DEFAULT_SEARCH_QUERY, help="Termo de busca")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_PATH, help="Pasta de saída base")
    parser.add_argument("-n", "--number", type=int, default=DEFAULT_NUM_DATASETS, help="Número máximo de NOVOS datasets a baixar")
    # Removido o --force, pois a lógica de log é mais explícita.
    # Para re-baixar, o usuário pode apagar a linha do log.
    
    args = parser.parse_args()
    
    print("🚀 --- INÍCIO DO SCRIPT DE DOWNLOAD INTELIGENTE ---")
    print(f"🔍 Termo de Busca: {args.search}")
    print(f"🔢 Máximo de datasets novos a baixar: {args.number}")
    print(f"📁 Pasta de saída base: {args.output}")
    print("-" * 50)
    
    if not check_kaggle_credentials() or not check_kaggle_cli():
        sys.exit(1)
        
    # 1. Ler o log de datasets já baixados
    already_downloaded = read_log()
    print(f"ℹ️  Encontrados {len(already_downloaded)} datasets no log de registros.")
    
    # 2. Buscar por datasets no Kaggle (buscamos um pouco mais para ter margem)
    # Se queremos 5 novos e os 10 primeiros já foram baixados, precisamos buscar mais.
    found_datasets = search_datasets(args.search, limit=len(already_downloaded) + args.number + 10)
    
    if not found_datasets:
        print("❌ --- SCRIPT FINALIZADO: NENHUM DATASET ENCONTRADO NA BUSCA ---")
        sys.exit(0)
    
    # 3. Filtrar a lista para pegar apenas os que são NOVOS
    new_datasets_to_download = []
    for ds in found_datasets:
        if ds not in already_downloaded:
            new_datasets_to_download.append(ds)
        # Para quando atingirmos o número desejado de novos datasets
        if len(new_datasets_to_download) >= args.number:
            break
            
    if not new_datasets_to_download:
        print("✅ --- SCRIPT FINALIZADO: Nenhum dataset novo encontrado para esta busca. Tudo atualizado! ---")
        sys.exit(0)
        
    print("-" * 50)
    print(f"⏬ Encontrados {len(new_datasets_to_download)} datasets novos. Iniciando downloads...")
    
    success_count = 0
    # 4. Loop para baixar cada dataset NOVO
    for i, dataset_name in enumerate(new_datasets_to_download):
        print(f"\n--- Processando novo dataset {i+1}/{len(new_datasets_to_download)}: {dataset_name} ---")
        
        if validate_dataset_name(dataset_name):
            # Tenta baixar o dataset
            if download_dataset(dataset_name, args.output):
                # Se o download for um sucesso, REGISTRA no log
                write_to_log(dataset_name)
                success_count += 1
    
    print("-" * 50)
    if success_count > 0:
        print(f"🎉 --- {success_count} NOVO(S) DATASET(S) BAIXADO(S) E REGISTRADO(S) ---")
    else:
        print("⚠️  --- NENHUM NOVO DATASET FOI BAIXADO COM SUCESSO ---")

if __name__ == "__main__":
    main()