#!/bin/bash

set -e 

echo " Iniciando processo de enriquecimento da ontologia..."

python3 pipeline.py

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="ontologia.owl.bak_${TIMESTAMP}"
cp ontologia.owl "$BACKUP_FILE"
echo " Backup da ontologia original criado em: $BACKUP_FILE"

DATASET_LIST=$(ls -1 datasets/ | tr '\n' ',' | sed 's/,$//')
echo "Found datasets: $DATASET_LIST"

TEMP_FILE="ontologia.tmp.owl"

echo " Invocando a IA para gerar a nova ontologia (isso pode levar um momento)..."

PROMPT="Você é um assistente especialista em ontologias médicas. Sua tarefa é enriquecer a ontologia em anexo para reduzir a heterogeneidade semântica.
Analise a seguinte lista de nomes de arquivos de datasets: ${DATASET_LIST}.
Gere e retorne APENAS o conteúdo completo e atualizado do arquivo 'ontologia.owl' com as novas classes e relações baseadas nesses datasets.
Ignore datasets que não pareçam ser da área médica.
Sua saída deve ser estritamente o código RDF/XML da ontologia, sem nenhuma frase, explicação ou comentário adicional."

if gemini -p "$PROMPT" > "$TEMP_FILE"; then

    mv "$TEMP_FILE" ontologia.owl
    echo "✔️  Ontologia atualizada com sucesso!"
else

    echo " ERRO: O comando gemini falhou. A ontologia original não foi modificada."
    rm -f "$TEMP_FILE" 
    exit 1 
fi


rm -rf datasets/

echo " Processo finalizado."